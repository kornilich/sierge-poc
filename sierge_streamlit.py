import streamlit as st
from agents.data_collection_agent import DataCollectionAgent
from agents.itinerary_agent import ItineraryAgent
from langchain_core.messages import  HumanMessage
from langchain_core.runnables import RunnableConfig
from agents.vector_database import VectorDatabase
import agents.tools as tools_set

from streamlit_helper import (
    get_streamlit_cb,
    streamlit_settings,
    streamlit_show_collection_home,
    streamlit_show_itinerary_home,
    streamlit_prepare_execution,
    streamlit_report_execution,
    streamlit_display_storage,
    load_environment
)

######## Start here ########

# Initialize session state
if 'chat_mode' not in st.session_state:
    st.session_state.chat_mode = "collect"
    st.session_state.storage = VectorDatabase()
    st.session_state.affected_records = ["0"] #HACK: Keep this to preserve var in runnable config, otherwise it will be removed
    
chat_mode = st.session_state.chat_mode
    
load_environment()
settings = streamlit_settings()

if chat_mode == "collect":     
    config = RunnableConfig({
        "location": settings["location"],
        "search_limit": settings["search_limit"],
        "number_of_results": settings["number_of_results"],
        "affected_records": st.session_state.affected_records,
        "callbacks": [get_streamlit_cb(st.empty())],
    })

    # tools = [tools_set.save_results, tools_set.google_organic_search, tools_set.google_events_search, tools_set.google_local_search, tools_set.yelp_search]
    tools = [tools_set.save_results]
    agent = DataCollectionAgent(st.session_state.storage, tools, settings)
    agent.setup()

    chat_input = st.chat_input("Type additonal query here to start data collection..")

    if chat_input:
        query = streamlit_prepare_execution(settings, config, agent, chat_input)

        with st.spinner("Collecting data...", show_time=True):
            messages = [HumanMessage(content=query)]
            
            result = agent.runnable.invoke(
                input={"messages": messages},
                config=config
            )

        streamlit_report_execution(result, tools)
            
        streamlit_display_storage(st.session_state.storage, st.session_state.affected_records)
        
        # def click_button():
        #     st.session_state.chat_mode = "itinerary"

        # st.divider()
        # st.write("Choose action")
        # col1, col2 = st.columns([1, 5], gap="small")
        # with col1:
        #     st.button('Generate itinerary', on_click=click_button, type="primary")
        # with col2:
        #     st.button('Collect data again', type="secondary")
    else:
        streamlit_show_collection_home(agent)
else:
    # streamlit_show_itinerary_home(agent)
    st.write("Itinerary")