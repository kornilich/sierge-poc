import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState
from langchain_core.runnables import RunnableConfig

import agents.tools as tools_set
from agents.tools import ActivitiesList

class SimpleAgent:
    def __init__(self, tools, settings):
        self.agent_description = settings["agent_description"]
        self.tools_instructions = settings["tools_instructions"]
        self.summarize_instructions = settings["summarize_instructions"]
        self.search_limit = settings["search_limit"]
        self.gpt_model = settings["model"]
        
        self.llm = ChatOpenAI(
            model=self.gpt_model,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
        )
                
        self.tools = tools
        
        self.tools_node = ToolNode(self.tools)        
        self.llm_agent = self.llm.bind_tools(self.tools, tool_choice="any")
        
        # self.llm_summarize = self.llm.with_structured_output(
        #     ActivitiesList, method="json_mode")
        
        self.llm_summarize = self.llm


    def agent_node(self, state: MessagesState, config: RunnableConfig):
        """LLM decides whether to call a tool or not"""
        
        web_search_count = 0
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                for call in msg.additional_kwargs["tool_calls"]:
                    if call["function"]["name"] in ["web_search", "events_search", "local_search"]:
                        web_search_count += 1
        
        if web_search_count >= self.search_limit:
            return {"messages": state["messages"] +
                    [AIMessage(content=f"Maximum search rounds reached ({self.search_limit}). Stopping.")]}
                    
        msg_history = [
            SystemMessage(
                content=f"{self.agent_description.format(location=config.get('configurable', {}).get('location', ''))}\n\n" +
                f"{self.tools_instructions.format(activity_details=tools_set.ActivityDetails.model_json_schema())}\n\n" +
                f"You can call the web_search tool up to {self.search_limit-web_search_count} times.")
        ] + state["messages"]
        
        result = self.llm_agent.invoke(msg_history)
        
        return {
            "messages": [result]
        }
        
    def summarize(self, state: MessagesState):
        new_messages = []
        human_message = None
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                human_message = msg.content
            else:
                new_messages.append(msg)
        
        new_messages.append(HumanMessage(
            content=human_message + "\n\n" + self.summarize_instructions))
        
        result = self.llm_summarize.invoke(new_messages)

        # return {
        #     "messages": [
        #         AIMessage(content=result.model_dump_json(),
        #                     additional_kwargs={"structured_output": result, "title":"Summary"})
        #     ]
        # }
        
        return {
            "messages": [result]
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
        graph.add_node("Search tools", self.tools_node)
        graph.add_node("Summarize", self.summarize)
        graph.set_entry_point("Agent")

        graph.add_conditional_edges(
            "Agent",
            self.should_continue,
            {
                "Search": "Search tools",
                "Results": "Summarize",
            },
        )
        
        graph.add_edge("Search tools", "Agent")
        graph.add_edge("Summarize", END)
        
        self.graph = graph
        self.runnable = graph.compile()

    