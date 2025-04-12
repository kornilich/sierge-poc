from dotenv import load_dotenv
import pandas as pd
import streamlit as st
import inspect
import os
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
from agents.simpleagent import SimpleAgent
# from langchain.callbacks.streamlit import StreamlitCallbackHandler
from streamlit.external.langchain import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from typing import TypeVar, Callable
import agents.prompts as prmt
import json

from agents.tools import ActivitiesList
import agents.tools as tools_set

class slCallbackHandler(StreamlitCallbackHandler):
    def on_chat_model_start(self, serialized, messages, **kwargs):
        return self.on_llm_start(serialized=serialized, prompts=messages, **kwargs)
        

# Progress callback wrapper
def get_streamlit_cb(parent_container: DeltaGenerator) -> BaseCallbackHandler:
    fn_return_type = TypeVar('fn_return_type')

    def add_streamlit_context(fn: Callable[..., fn_return_type]) -> Callable[..., fn_return_type]:
        ctx = get_script_run_ctx()

        def wrapper(*args, **kwargs) -> fn_return_type:
            try:    
                add_script_run_ctx(ctx=ctx)
                r = fn(*args, **kwargs)
                return r
            except Exception as e:
                # st.info(f"Error: {e}")
                return None

        return wrapper

    st_cb = slCallbackHandler(parent_container)

    for method_name, method_func in inspect.getmembers(st_cb, predicate=inspect.ismethod):
        if method_name.startswith('on_'):
            setattr(st_cb, method_name, add_streamlit_context(method_func))
    return st_cb


def load_environment():
    load_dotenv()

    # Set environment variables from streamlit secrets
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    os.environ["SERPAPI_KEY"] = st.secrets["SERPAPI_KEY"]
    os.environ["LANGSMITH_TRACING"] = st.secrets["LANGSMITH_TRACING"]
    os.environ["LANGSMITH_ENDPOINT"] = st.secrets["LANGSMITH_ENDPOINT"]
    os.environ["LANGSMITH_API_KEY"] = st.secrets["LANGSMITH_API_KEY"]
    os.environ["LANGSMITH_PROJECT"] = st.secrets["LANGSMITH_PROJECT"]


def streamlit_config():
    st.set_page_config(page_title='Sierge PoC', layout='wide')

    with st.sidebar:
        with st.expander("Preferences"):
            contextual_preferences = st.text_area(
                ":orange[**Contextual Preferences**]",
                value=prmt.contextual_preferences_default, height=72*3)
            fixed_preferences = st.text_area(
                ":orange[**Fixed Preferences**]",
                value=prmt.fixed_preferences_default, height=72*3)

        with st.expander("Instructions"):
            agent_description = st.text_area(
                ":orange[**Agent description**]",
                value=prmt.system_agent_description, height=72*3)
            tools_instructions = st.text_area(
                ":orange[**Tools instructions**]",
                value=prmt.system_tools_instructions, height=72*3)
            summarize_instructions = st.text_area(
                ":orange[**Summarize instructions**]",
                value=prmt.system_agent_summarize, height=72*3)

        with st.expander("Agent settings"):
            model = st.selectbox("Model", ("gpt-4o-mini"))
            st.selectbox("Web search", ("serpapi"))
            location = st.selectbox(
                "Location", ("Dallas, Texas, United States", "Los Angeles, California, United States"))
            search_limit = st.slider(
                "Search limit", min_value=0, max_value=20, value=1)
            number_of_results = st.slider(
                "Number of results", min_value=5, max_value=20, value=5)

    return {
        "contextual_preferences": contextual_preferences,
        "fixed_preferences": fixed_preferences,
        "agent_description": agent_description,
        "tools_instructions": tools_instructions,
        "summarize_instructions": summarize_instructions,
        "model": model,
        "location": location,
        "search_limit": search_limit,
        "number_of_results": number_of_results
    }


settings = streamlit_config()

load_environment()

tools = [
    tools_set.web_search,
    tools_set.events_search,
    tools_set.local_search,
    tools_set.yelp_search
]

agent = SimpleAgent(tools, settings)
agent.setup()

chat_input = st.chat_input("Describe your situational preferences here...")

if chat_input:
    query = f"{settings['fixed_preferences']} \n\n {settings['contextual_preferences']} \n\n {chat_input}"

    with st.chat_message("ai"):
        with st.expander("System prompt (agent)", expanded=False):
            st.write(prmt.agent_system_prompt.format(
                agent_description=settings["agent_description"].format(
                    location=settings["location"]),
                tools_instructions=settings["tools_instructions"],
                search_limit=settings["search_limit"]))

    with st.chat_message("human"):
        with st.expander("Human prompt", expanded=True):
            st.write(query)
            st.markdown(
                f":gray-badge[Model: {settings['model']}] :gray-badge[Location: {settings['location']}]" +
                f":gray-badge[Search limit: {settings['search_limit']}] :gray-badge[Number of results: {settings['number_of_results']}]"
            )
            
    with st.chat_message("ai"):
        with st.expander("System prompt (summarization)", expanded=False):
            st.write(settings["agent_description"].format(
                location=settings["location"]) + "\n\n" + settings["summarize_instructions"])

    with st.spinner("Running agent...", show_time=True):
        messages = [HumanMessage(content=query)]
        result = agent.runnable.invoke(
            input={"messages": messages},
            config=RunnableConfig({
                "location": settings["location"],
                "search_limit": settings["search_limit"],
                "number_of_results": settings["number_of_results"],
                "callbacks": [get_streamlit_cb(st.empty())],
            })
        )

    for msg in result["messages"]:
        if isinstance(msg, HumanMessage):
            pass
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                if hasattr(msg, 'additional_kwargs'):
                    if 'tool_calls' in msg.additional_kwargs:
                        for tool_call in msg.additional_kwargs['tool_calls']:
                            fn = tool_call["function"]
                            if fn["name"] in [tool.name for tool in tools]:
                                query = json.loads(fn["arguments"])
                                query_text = query.get("query", "")

                                st.markdown(f"Decided to use **{fn['name']}** ({query_text})")
                            else:
                                st.write("Tool:", fn["name"], msg.content)
                    elif 'structured_output' in msg.additional_kwargs:
                        with st.expander(msg.additional_kwargs['title']):
                            frame = pd.DataFrame([activity.model_dump(
                            ) for activity in msg.additional_kwargs['structured_output'].activities])
                            st.dataframe(frame)
                            st.write(
                                "Reason:", msg.additional_kwargs['structured_output'].reason)
                    else:
                        st.write("AIMessage:", msg.content)
        elif isinstance(msg, ToolMessage):
            if msg.name in [tool.name for tool in tools]:
                with st.chat_message("Search resutls role", avatar=":material/manage_search:"):
                    json_content = json.loads(msg.content)
                    for search_type, results in json_content.items():                        
                        st.markdown(
                            f"**{msg.name} results** (<a href='{results.get('search_url', '')}' target='_blank'>{results.get('search_query', '')}</a>)", unsafe_allow_html=True)
                        with st.expander(f"Search results: {search_type} ({len(results.get('search_results', []))})"):
                            st.json(results.get("search_results", {}), expanded=True)
            else:
                st.write(msg)
        else:
            st.write(msg)

    # start_time = datetime.now() - timedelta(days=1)
    # smithClient = LangsmithClient()
    # runs = list(
    #     smithClient.list_runs(
    #         project_name=os.environ["LANGSMITH_PROJECT"],
    #         # start_time=start_time,
    #         # trace_id="3f1be5e6-b61c-4845-8297-ebb883b3a8d8",
    #         is_root=True,
    #     )
    # )
else:  # Default page view
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://media.lordicon.com/icons/wired/flat/2007-dallas-city.svg",
                 use_container_width=True)
    with col2:
        st.header(":blue[Sierge PoC]")
        st.write(settings["agent_description"].format(location=settings["location"]))

    col1, col2 = st.columns([2, 2])
    img = agent.runnable.get_graph().draw_png()
    with col1:
        st.image(img, width=400, caption="Agent architecture")
    with col2:
        st.subheader(":gray[Available tools]")
        st.write("Tool name and instructions for the agent on when and how to use it")
        for tool in agent.tools:
            st.markdown(f"**{tool.name}**: {tool.description}")

        # st.subheader(":gray[Tools usage instructions]")
        # st.write(settings["tools_instructions"])
        # st.write(settings["summarize_instructions"])
        