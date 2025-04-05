import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState
from langchain_core.runnables import RunnableConfig

import agents.tools as mytools
import agents.prompts as prmt

class SimpleAgent:
    def __init__(self, settings):
        self.agent_description = settings["agent_description"]
        self.tools_instructions = settings["tools_instructions"]
        self.summarize_instructions = settings["summarize_instructions"]
        self.search_limit = settings["search_limit"]
        self.gpt_model = settings["model"]
        
        self.llm_agent = ChatOpenAI(
            model=self.gpt_model,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
            streaming=True
        )
        
        self.llm_summarize = ChatOpenAI(
            model=self.gpt_model,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
            streaming=True
        )
        
        self.tools = [
            mytools.web_search,
        ]
        
        self.tools_node = ToolNode(self.tools)
        
        self.llm_agent = self.llm_agent.bind_tools(
            self.tools, tool_choice="any")

    def agent_node(self, state: MessagesState):
        """LLM decides whether to call a tool or not"""
        
        web_search_count = 0
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                for call in msg.additional_kwargs["tool_calls"]:
                    if call["function"]["name"] == "web_search":
                        web_search_count += 1
        
        if web_search_count >= self.search_limit:
            return {"messages": state["messages"] +
                    [AIMessage(content=f"Maximum Web Search calls reached ({self.search_limit}). Stopping.")]}

        return {
            "messages": [
                self.llm_agent.invoke(
                    [
                        SystemMessage(
                            content=self.agent_description + "\n" + 
                                    self.tools_instructions + "\n" +
                                    f"You can call the web_search tool up to {self.search_limit-web_search_count} times.")
                    ]
                    + state["messages"]
                )
            ]
        }
        
    def summarize(self, state: MessagesState):
        search_results = []
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                search_results.append({"call_id": msg.tool_call_id, "content": msg.content})
                
        new_messages = []
        human_message = None
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                human_message = msg.content
            else:
                new_messages.append(msg)

        new_messages.append(HumanMessage(
            content=human_message + "\n" + self.summarize_instructions))
        # new_messages.append(AIMessage(content=json.dumps(search_results)))
       
        return {
            "messages": [
                self.llm_summarize.invoke(
                    [
                        SystemMessage(
                            content=self.agent_description
                        )
                    ]
                    + new_messages
                )
            ]
        }

    def should_continue(self, state: MessagesState):
        """Determine whether to continue to tools or end"""
        last_message = state["messages"][-1]
                
        if "tool_calls" in last_message.additional_kwargs:
            return "Search"
        else:        
            return "Results"


    def setup(self): 
        graph = StateGraph(state_schema=MessagesState)

        graph.add_edge(START, "Agent")
        
        graph.add_node("Agent", self.agent_node)
        graph.add_node("Web", self.tools_node)
        graph.add_node("Summarize", self.summarize)
        graph.set_entry_point("Agent")

        graph.add_conditional_edges(
            "Agent",
            self.should_continue,
            {
                "Search": "Web",
                "Results": "Summarize",
            },
        )
        
        graph.add_edge("Web", "Agent")
        graph.add_edge("Summarize", END)
        
        self.graph = graph
        self.runnable = graph.compile()

    