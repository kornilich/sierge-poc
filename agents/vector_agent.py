import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import PromptTemplate
import agents.prompts as prmt

from langchain_openai import OpenAIEmbeddings


class VectorStorageAgent:
    def __init__(self, vector_store, tools, settings):
        self.gpt_model = settings["model"]
        self.vector_store = vector_store

        self.llm = ChatOpenAI(
            model=self.gpt_model,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
        )

        self.tools = tools
        self.llm_agent = self.llm.bind_tools(self.tools)

    def agent_node(self, state: MessagesState, config: RunnableConfig):
        """LLM decides whether to call a tool or not"""
        cfg = config.get('configurable', {})
        search_limit = cfg.get('search_limit', 0)

        web_search_count = 0
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                for call in msg.additional_kwargs["tool_calls"]:
                    if call["function"]["name"] in [t.name for t in self.tools if t.name != "save_results"]:
                        web_search_count += 1

        system_prompt = self.get_system_prompt(
            prmt.system_data_collection_prompt_template, config, web_search_count)
        
        if web_search_count >= search_limit:
            system_prompt = system_prompt + \
                "\n\nMaximum search rounds reached. Stop using search tools, save results and summarize."

        msg_history = [
            SystemMessage(content=system_prompt)
        ] + state["messages"]


        result = self.llm_agent.invoke(msg_history)

        return {
            "messages": [result]
        }


    def should_continue(self, state: MessagesState):
        """Determine whether to continue to tools or end"""
        last_message = state["messages"][-1]

        for message in state["messages"]:
            if isinstance(message, ToolMessage) and message.status == "error":
                raise Exception(message.content)

        if "tool_calls" in last_message.additional_kwargs:
            return "Tools"
        else:
            return "Results"
        
    def setup(self):
        DATA_DISCOVERY = "Data discovery"
        STORAGE_TOOLS = "Vector storage"

        graph = StateGraph(state_schema=MessagesState)

        graph.add_edge(START, DATA_DISCOVERY)

        graph.add_node(DATA_DISCOVERY, self.agent_node)
        graph.add_node(STORAGE_TOOLS, ToolNode(self.tools))

        graph.set_entry_point(DATA_DISCOVERY)

        graph.add_conditional_edges(
            DATA_DISCOVERY,
            self.should_continue,
            {
                "Tools": STORAGE_TOOLS,
                "Results": END,
            },
        )

        graph.add_edge(STORAGE_TOOLS, DATA_DISCOVERY)

        self.graph = graph
        self.runnable = graph.compile(store=self.vector_store)

