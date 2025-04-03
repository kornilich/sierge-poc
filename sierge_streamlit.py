import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import streamlit as st
import inspect
import os
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
from agents.simpleagent import SimpleAgent
from agents.testagent import TestAgent
from PIL import Image
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langsmith import Client as LangsmithClient

from typing import TypeVar, Callable
import agents.prompts as myprompts
import json

# Initialize the agent

def streamlit_config():
    st.set_page_config(page_title='Sierge PoC', layout='wide')
    
    with st.sidebar:
        with st.form("preferences"):
            contextual_preferences = st.text_area(
                ":orange[**Contextual Preferences**]",
                value="""I'm going with my family. 
Looking for a place with:
Atmosphere: Casual, child-friendly, well-lit
Alcohol: Limited or non-alcoholic options
Meals: Family-style sharing platters
Noise level: Moderate, tolerant of children's sounds"""
                , height=72*3)
            fixed_preferences = st.text_area(
                ":orange[**Fixed Preferences**]",
                value="""I'm from Dallas city, 21 years old, single woman.
I love dancing, and prefer vegan food.
Love meeting people but not noisy places.
I'm a new resident in Dallas."""
                , height=72*3)
            submitted = st.form_submit_button(
                "Submit", type="primary", use_container_width=True)

        with st.expander("Agent settings"):
            model = st.selectbox('Model', ('gpt-4o-mini'))
            web_search = st.selectbox('Web search', ('serpapi'))
            
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://media.lordicon.com/icons/wired/flat/2007-dallas-city.svg",
                 use_container_width=True)
    with col2:
        st.header(":blue[Sierge PoC]")
        st.write("Tailor recommendations in real time based on logistics, constraints, and external conditions like time availability, budget, location, and weather. They ensure that experiences are practical, feasible, and aligned with current circumstances without altering core user preferences.")
        
    return contextual_preferences, fixed_preferences


def get_streamlit_cb(parent_container: DeltaGenerator) -> BaseCallbackHandler:
    fn_return_type = TypeVar('fn_return_type')

    def add_streamlit_context(fn: Callable[..., fn_return_type]) -> Callable[..., fn_return_type]:
        ctx = get_script_run_ctx()

        def wrapper(*args, **kwargs) -> fn_return_type:
            add_script_run_ctx(ctx=ctx)
            return fn(*args, **kwargs)

        return wrapper

    st_cb = StreamlitCallbackHandler(parent_container)

    for method_name, method_func in inspect.getmembers(st_cb, predicate=inspect.ismethod):
        if method_name.startswith('on_'):
            setattr(st_cb, method_name, add_streamlit_context(method_func))
    return st_cb

contextual_preferences, fixed_preferences = streamlit_config()

load_dotenv()

# Set environment variables from streamlit secrets
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["SERPAPI_KEY"] = st.secrets["SERPAPI_KEY"]
os.environ["LANGSMITH_TRACING"] = st.secrets["LANGSMITH_TRACING"]
os.environ["LANGSMITH_ENDPOINT"] = st.secrets["LANGSMITH_ENDPOINT"] 
os.environ["LANGSMITH_API_KEY"] = st.secrets["LANGSMITH_API_KEY"]
os.environ["LANGSMITH_PROJECT"] = st.secrets["LANGSMITH_PROJECT"]


agent = TestAgent()
agent.setup()


# I want to stat in the morning, take a look at some sight-seen and then get to restaurant 
chat_input = st.chat_input("Describe your situational preferences here...")

if chat_input:
    output_container = st.container()
    st_callback = StreamlitCallbackHandler(output_container)
    config = {"callbacks": [st_callback]}

    query = f"{fixed_preferences} \n\n {contextual_preferences} \n\n I have following situation {chat_input}"
    
    with st.chat_message("human"):
        with st.expander("Asking LLM", expanded=True): 
            st.write(query)
    
    with st.spinner("Running agent...", show_time=True):
        messages = [HumanMessage(content=query)]
        result = agent.runnable.invoke({"messages": messages}, )
                                    #    config={"callbacks": [get_streamlit_cb(st.empty())]})
    
    for msg in result["messages"]:
        if isinstance(msg, HumanMessage):
            pass
        elif isinstance(msg, AIMessage):
            if hasattr(msg, 'additional_kwargs') and 'tool_calls' in msg.additional_kwargs:
                for tool_call in msg.additional_kwargs['tool_calls']:
                    fn = tool_call["function"]
                    with st.chat_message("assistant"):
                        if fn["name"] == "web_search":
                            query = json.loads(fn["arguments"])
                            query_text = query.get("query", "")
                            
                            st.markdown(f"**Searching:** {query_text}")
                        else:
                            st.write(msg.content)
            else:
                with st.chat_message("assistant"):
                    st.write(msg.content)
        elif isinstance(msg, ToolMessage):
            if msg.name == "web_search":
                with st.chat_message("Search resutls", avatar=":material/manage_search:"):
                    st.expander("Search results").json(msg.content, expanded=False)
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

    # st.write(result["messages"][-1].content)
 

    # st.write(SimpleAgent.build_report(
    #     output=result["intermediate_steps"][-1].tool_input
    # ))
        
else:
    col1, col2 = st.columns([2, 2])
    img = agent.runnable.get_graph().draw_png()
    with col1:
        st.image(img, width=400, caption="Agentic AI based venue recommendation")
    with col2:
        st.subheader(":gray[Agent description]")
        st.write(myprompts.system_agent_description)
        st.write(myprompts.system_agent_web_search)
        st.subheader(":gray[Summarize prompt]")
        st.write(myprompts.system_agent_summarize)



