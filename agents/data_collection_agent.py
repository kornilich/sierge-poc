import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import PromptTemplate
import agents.prompts as prmt


class DataCollectionAgent:
    def __init__(self, vector_store, tools, settings):
        self.data_collection_prompt = settings["data_collection_prompt"]
        self.gpt_model = settings["model"]

        self.vector_store = vector_store

        self.llm = ChatOpenAI(
            model=self.gpt_model,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
        )

        self.tools = tools
        self.llm_agent = self.llm.bind_tools(self.tools)
        
        # Unfinite duplicate tool calls detection
        self.tool_calls_history = {}

    def get_system_prompt(self, prompt, config, web_search_count=0):
        def _format_prompt(prompt, **kwargs):
            # Count number of placeholders in the prompt
            prompt_before = prompt

            template = PromptTemplate.from_template(prompt)
            result = template.format(**kwargs)

            if prompt_before != result:
                result = _format_prompt(result, **kwargs)

            return result
        
        # Direct access to config if not graph invoked, otherwise use graph config via configurable
        cfg = config.get('configurable', config) 
        
        location = cfg.get('location', '')
        search_limit = cfg.get('search_limit', 0)
        number_of_results = cfg.get('number_of_results', 0)

        limit = search_limit - web_search_count
        limit = 0 if limit < 0 else limit
        
        system_prompt = _format_prompt(prompt, location=location, search_limit=limit, number_of_results=number_of_results)

        return system_prompt

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
            prmt.data_collection_prompt, config, web_search_count)
        
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

        # TODO: Rework ToolNode to regular node for smart exception and error handling
        # This is a workaround to handle errors in ToolNode and it's not a good practice
        # TODO: Maybe move search limit here
        for message in state["messages"]:
            if isinstance(message, ToolMessage) and message.status == "error":
                raise Exception(message.content)

        if "tool_calls" in last_message.additional_kwargs:
            for call in last_message.additional_kwargs["tool_calls"]:
                fn_name = call["function"]["name"]
                fn_args = call["function"]["arguments"]
                                                                
                if fn_name not in self.tool_calls_history:
                    self.tool_calls_history[fn_name] = {fn_args: 1}
                elif fn_args not in self.tool_calls_history[fn_name]:
                    self.tool_calls_history[fn_name][fn_args] = 1
                else:
                    self.tool_calls_history[fn_name][fn_args] += 1
                         
                # Infinite tool calls control    
                limit = 3
                if self.tool_calls_history[fn_name][fn_args] >= limit:
                    raise Exception(f"Tool call limit reached ({limit}): {fn_name} with args: {fn_args}")

            return "Search"
        else:
            return "Results"

    def setup(self):
        COLLECT_DATA_NODE = "Data collection"
        DATA_SOURCE_NODE = "Data sources"

        graph = StateGraph(state_schema=MessagesState)

        graph.add_edge(START, COLLECT_DATA_NODE)

        graph.add_node(COLLECT_DATA_NODE, self.agent_node)
        graph.add_node(DATA_SOURCE_NODE, ToolNode(self.tools))
        graph.set_entry_point(COLLECT_DATA_NODE)

        graph.add_conditional_edges(
            COLLECT_DATA_NODE,
            self.should_continue,
            {
                "Search": DATA_SOURCE_NODE,
                "Results": END,
            },
        )

        graph.add_edge(DATA_SOURCE_NODE, COLLECT_DATA_NODE)

        self.runnable = graph.compile(store=self.vector_store)
