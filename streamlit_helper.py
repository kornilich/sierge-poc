from dotenv import load_dotenv
import pandas as pd
import streamlit as st
import inspect
import os
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
from streamlit.external.langchain import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from typing import TypeVar, Callable
import agents.prompts as prmt
import json

COLLECTION_MODE = "Collection"
DISCOVERY_MODE = "Discovery"
ITINERARY_MODE = "Itinerary"


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


def streamlit_settings(chat_mode_list, current_chat_mode=None):
    st.set_page_config(page_title='Sierge PoC', layout='wide')

    user_preferences = ""
    data_collection_prompt = ""
    itinerary_instructions = ""
    search_limit = 1
    number_of_results = 5

    with st.sidebar:
        chat_mode = st.segmented_control(
            "Data mode", chat_mode_list, default=current_chat_mode, selection_mode="single"
        )

        if chat_mode == COLLECTION_MODE:
            with st.expander("Preferences"):
                user_preferences = st.text_area(
                    ":orange[**Fixed, Contextual, Situational**]", value=prmt.user_preferences, height=72*6)

            with st.expander("Instructions"):
                data_collection_prompt = st.text_area(
                    ":orange[**Data collection**]",
                    value=prmt.data_collection_prompt, height=72*6)

            # itinerary_instructions = st.text_area(
            #     ":orange[**Itinerary**]",
            #     value=prmt.system_agent_itinerary, height=72*3)

        with st.expander("Agent settings", expanded=True):
            location = st.selectbox(
                "Location", ("Dallas, Texas, United States", "Los Angeles, California, United States"))
            if chat_mode == COLLECTION_MODE:
                search_limit = st.slider(
                    "Search limit", min_value=0, max_value=20, value=1)
                number_of_results = st.slider(
                    "Number of results", min_value=5, max_value=20, value=5)
            model = st.selectbox("Model", ("gpt-4o-mini"))
            if chat_mode == COLLECTION_MODE:
                st.selectbox("Web search", ("serpapi"))

    return {
        "user_preferences": user_preferences,
        "data_collection_prompt": data_collection_prompt,
        "itinerary_instructions": itinerary_instructions,
        "model": model,
        "location": location,
        "search_limit": search_limit,
        "number_of_results": number_of_results,
        "chat_mode": chat_mode
    }


def streamlit_show_collection_home(agent):
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://media.lordicon.com/icons/wired/flat/2007-dallas-city.svg",
                 use_container_width=True)
    with col2:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.header(":blue[Data collection mode]")
        with c2:
            st.header(":gray[Sierge PoC]")
        st.markdown("Instructions usage: **Common** - used for all AI LLM calls. Addtionally to that **Data collection** - used for data collection, **Summarize** - used for summarization")

    col1, col2 = st.columns([2, 2])
    img = agent.runnable.get_graph().draw_png()
    with col1:
        st.image(img, width=400, caption="Congitive model")
    with col2:
        st.subheader(":gray[Data sources]")
        st.write("Tool name and instructions for the agent on when and how using it")
        for tool in agent.tools:
            st.markdown(f"**{tool.name}**: {tool.description}")

    return


def streamlit_show_itinerary_home(agent):
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://media.lordicon.com/icons/wired/flat/2007-dallas-city.svg",
                 use_container_width=True)
    with col2:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.header(":blue[Itinerary mode]")
        with c2:
            st.header(":gray[Sierge PoC]")
        # st.write(settings["summarize_instructions"])

    col1, col2 = st.columns([2, 2])
    img = agent.runnable.get_graph().draw_png()
    with col1:
        st.image(img, width=200, caption="Congitive model")
    with col2:
        st.subheader(":gray[Data sources]")
        st.write("Tool name and instructions for the agent on when and how using it")
        for tool in agent.tools:
            st.markdown(f"**{tool.name}**: {tool.description}")

    return


def streamlit_show_generic_home(agent, tools, title, image_name, description):
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(f"assets/{image_name}",
                 use_container_width=True)
    with col2:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.header(f":blue[{title}]")
        with c2:
            st.header(":gray[Sierge PoC]")
        st.write(description)
        st.divider()

    col1, col2 = st.columns([1, 2])
    img = agent.get_graph().draw_mermaid_png()

    with col1:
        st.image(img, width=300, caption="Congitive model")
    with col2:
        st.subheader(":gray[Tools]")
        st.write("Tool name and instructions for the agent on when and how using it")
        for tool in tools:
            st.markdown(f"**{tool.name}**: {tool.description}")

    return


def streamlit_prepare_execution(settings, config, agent, chat_input):
    query = f"{settings['user_preferences']} \n\n {chat_input}"

    with st.chat_message("ai"):
        with st.expander("Data collection prompt", expanded=False):
            st.write(agent.get_system_prompt(prmt.data_collection_prompt, config))

    with st.chat_message("human"):
        with st.expander("Human prompt", expanded=False):
            st.write(query)
            st.markdown(
                f":gray-badge[Model: {settings['model']}] :gray-badge[Location: {settings['location']}]" +
                f":gray-badge[Search limit: {settings['search_limit']}] :gray-badge[Number of results: {settings['number_of_results']}]"
            )

    return query


def streamlit_report_execution(result, tools):
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
                                if query_text:
                                    query_text = f" > {query_text}"

                                st.markdown(
                                    f"Decided to use **{fn['name']}** {query_text}")
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
                                f"**{msg.name} results**: <a href='{results.get('search_url', '')}' target='_blank'>{results.get('search_query', '')}</a>", unsafe_allow_html=True)
                            with st.expander(f"Search results: {search_type} ({len(results.get('search_results', []))})"):
                                st.json(results.get(
                                    "search_results", {}), expanded=True)
                    else:
                        st.markdown(
                            f"**Results from {json_content.get('data_source')} saved:** {json_content.get('records_affected')} records")
            else:
                st.write(msg)
        elif isinstance(msg, SystemMessage):
            with st.chat_message("ai"):
                with st.expander("System message", expanded=False):
                    st.write(msg)
        else:
            st.write(msg)


def streamlit_display_storage(storage, data_ids, group_by="data_source", namespace=""):
    # Display stored search results
    st.subheader(":gray[Collected data]")

    if not data_ids:
        st.write("No data collected")
        return

    activities = storage.get_by_ids(data_ids, namespace)

    # Convert activities to DataFrame
    df = pd.DataFrame([activity.model_dump() for activity in activities])

    # Move id column to the end if it exists
    cols = [col for col in df.columns if col != 'id'] + ['id']

    if len(cols) < 2:
        st.error("Not enough columns to display data")
        return

    df = df[cols]

    # Convert timestamp fields to datetime
    df['created'] = pd.to_datetime(df['created_at'], unit='s')
    df['updated'] = pd.to_datetime(df['updated_at'], unit='s')

    # Add 'new' column based on created_at and updated_at comparison
    df['new'] = (df['created_at'] == df['updated_at']
                 ).map({True: 'yes', False: 'no'})
    # Move 'new' column to first position
    cols = ['new'] + [col for col in df.columns if col != 'new']
    df = df[cols]

    # Remove timestamp columns
    df = df.drop(['created_at', 'updated_at'], axis=1)

    # Group by source and display in expandable sections
    if len(df) > 0 and group_by in df.columns:
        for source in df[group_by].unique():
            source_df = df[df[group_by] == source]
            with st.expander(f"Results from {source}"):
                st.dataframe(source_df.drop('data_source', axis=1),
                             use_container_width=True)
    else:
        st.error("Structure issue: no 'data_source' column found")
        st.dataframe(df, use_container_width=True)


def load_environment():
    load_dotenv()

    # Set environment variables from streamlit secrets
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    os.environ["SERPAPI_KEY"] = st.secrets["SERPAPI_KEY"]
    os.environ["LANGSMITH_TRACING"] = st.secrets["LANGSMITH_TRACING"]
    os.environ["LANGSMITH_ENDPOINT"] = st.secrets["LANGSMITH_ENDPOINT"]
    os.environ["LANGSMITH_API_KEY"] = st.secrets["LANGSMITH_API_KEY"]
    os.environ["LANGSMITH_PROJECT"] = st.secrets["LANGSMITH_PROJECT"]
    os.environ["PINECONE_API_KEY"] = st.secrets["PINECONE_API_KEY"]
    os.environ["PINECONE_INDEX"] = st.secrets["PINECONE_INDEX"]

    return
