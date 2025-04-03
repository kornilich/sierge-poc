import os
import logging
import json

from langchain_core.agents import AgentAction
from langchain_openai import ChatOpenAI
from langchain_core.agents import AgentAction
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState

import agents.tools as mytools
import agents.prompts as myprompts

class TestAgent:
    def __init__(self):
        self.runnable = None
        self.graph = None
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
            streaming=True
        )
        
        self.llm_summarize = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
            streaming=True
        )

        
        self.tools = [
            mytools.web_search,
        ]
        
        self.tools_node = ToolNode(self.tools)
        
        self.agent_node = self.llm.bind_tools(self.tools, tool_choice="any")
        
        return


    def agent_call(self, state: MessagesState):
        """LLM decides whether to call a tool or not"""
        
        web_search_count = 0
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                for call in msg.additional_kwargs["tool_calls"]:
                    if call["function"]["name"] == "web_search":
                        web_search_count += 1
        
        if web_search_count > 1:
            return {"messages": state["messages"] +
                    [AIMessage(content="Maximum Web Search calls reached. Stopping.")]}

        return {
            "messages": [
                self.agent_node.invoke(
                    [
                        SystemMessage(
                            content=myprompts.system_agent_description + "\n" + myprompts.system_agent_web_search
                        )
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
            content=human_message + "\n" + myprompts.system_agent_summarize))
        # new_messages.append(AIMessage(content=json.dumps(search_results)))
       
        return {
            "messages": [
                self.llm_summarize.invoke(
                    [
                        SystemMessage(
                            content=myprompts.system_agent_description
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
        
        graph.add_node("Agent", self.agent_call)
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

    