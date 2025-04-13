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
from agents.tools import ActivitiesList, ActivityDetails

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

        with st.expander("Prompts"):
            system_common_prompt = st.text_area(
                ":orange[**Common**]",
                value=prmt.system_common_prompt, height=72*3)
            data_sources_prompt = st.text_area(
                ":orange[**Data collection**]",
                value=prmt.data_sources_prompt, height=72*3)
            summarize_instructions = st.text_area(
                ":orange[**Summarize**]",
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
        "system_common_prompt": system_common_prompt,
        "data_sources_prompt": data_sources_prompt,
        "summarize_instructions": summarize_instructions,
        "model": model,
        "location": location,
        "search_limit": search_limit,
        "number_of_results": number_of_results
    }


######## Start here ########

load_environment()
settings = streamlit_config()
config = RunnableConfig({
    "location": settings["location"],
    "search_limit": settings["search_limit"],
    "number_of_results": settings["number_of_results"],
    "callbacks": [get_streamlit_cb(st.empty())],
})

# tools = [
#     tools_set.events_search,
#     tools_set.local_search,
#     tools_set.yelp_search
# ]

tools = [tools_set.google_organic_search, tools_set.save_results]

agent = SimpleAgent(tools, settings)
agent.setup()

chat_input = st.chat_input("Describe your situational preferences here...")

if chat_input:
    query = f"{settings['fixed_preferences']} \n\n {settings['contextual_preferences']} \n\n {chat_input}"

    with st.chat_message("ai"):
        with st.expander("Data collection prompt", expanded=False):
            st.write(agent.get_system_prompt(
                prmt.system_data_collection_prompt_template,config, settings["search_limit"]))

    with st.chat_message("human"):
        with st.expander("Human prompt", expanded=False):
            st.write(query)
            st.markdown(
                f":gray-badge[Model: {settings['model']}] :gray-badge[Location: {settings['location']}]" +
                f":gray-badge[Search limit: {settings['search_limit']}] :gray-badge[Number of results: {settings['number_of_results']}]"
            )
            
    with st.chat_message("ai"):
        with st.expander("Summarize prompt", expanded=False):
            st.write(agent.get_system_prompt(settings["system_common_prompt"] + "\n\n" + settings["summarize_instructions"], config, 0))

    with st.spinner("Running agent...", show_time=True):
        messages = [HumanMessage(content=query)]
        result = agent.runnable.invoke(
            input={"messages": messages},
            config=config
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
                with st.chat_message("Search results role", avatar=":material/manage_search:"):
                    json_content = json.loads(msg.content)
                    if msg.name != "save_results":
                        for search_type, results in json_content.items():                        
                            st.markdown(
                                f"**{msg.name} results** (<a href='{results.get('search_url', '')}' target='_blank'>{results.get('search_query', '')}</a>)", unsafe_allow_html=True)
                            with st.expander(f"Search results: {search_type} ({len(results.get('search_results', []))})"):
                                st.json(results.get("search_results", {}), expanded=True)
                    else:
                        st.markdown(f"**Results from {json_content.get('source')} saved:** {json_content.get('records')} records")
            else:
                st.write(msg)
        else:
            st.write(msg)

    # Display stored search results
    st.subheader(":gray[Search History]")
        
    records = []
    
    agent.vector_store.dump("vector_store.json")
    agent.vector_store.load("vector_store.json")

    for index, (id, doc) in enumerate(agent.vector_store.store.items()):
        # docs have keys 'id', 'vector', 'text', 'metadata'
        # Convert string representation of dict to actual dict first
        activity_data = eval(doc['text'])  # text contains string repr of dict
        activity = ActivityDetails(**activity_data)
        activity_dict = activity.model_dump()
        records.append(activity_dict)                
            
    df = pd.DataFrame(records)
    
    # Group by source and display in expandable sections
    for source in df['source'].unique():
        source_df = df[df['source'] == source]
        with st.expander(f"Results from {source}"):
            st.dataframe(source_df.drop('source', axis=1), use_container_width=True)
else:  # Default page view
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://media.lordicon.com/icons/wired/flat/2007-dallas-city.svg",
                 use_container_width=True)
    with col2:
        st.header(":blue[Sierge PoC]")
        st.markdown("Instructions usage: **Common** - used for all AI LLM calls. Addtionally to that **Data collection** - used for data collection, **Summarize** - used for summarization")

    col1, col2 = st.columns([2, 2])
    img = agent.runnable.get_graph().draw_png()
    with col1:
        st.image(img, width=400, caption="Congitive model")
    with col2:
        st.subheader(":gray[Data sources]")
        st.write("Tool name and instructions for the agent on when and how to use it")
        for tool in agent.tools:
            st.markdown(f"**{tool.name}**: {tool.description}")
        