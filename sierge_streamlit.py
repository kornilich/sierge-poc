import streamlit as st
from agents.data_collection_agent import DataCollectionAgent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from agents.vector_database import VectorDatabase
import agents.tools as tools_set
import agents.prompts as prmt

from streamlit_helper import COLLECTION_MODE, DISCOVERY_MODE, ITINERARY_MODE
from streamlit_helper import (
    get_streamlit_cb,
    streamlit_settings,
    streamlit_show_home,
    streamlit_prepare_execution,
    streamlit_report_execution,
    streamlit_display_storage,
    load_environment
)

######## Start here ########
chat_mode_list = [COLLECTION_MODE, DISCOVERY_MODE, ITINERARY_MODE]

# Initialize session state
if "memory" not in st.session_state:
    st.session_state.memory = MemorySaver()

vector_store = VectorDatabase()
# HACK: Keep this to preserve var in runnable config, otherwise it will be removed
affected_records = ["Blank"]

load_environment()

settings = streamlit_settings(chat_mode_list, DISCOVERY_MODE)
chat_mode = settings["chat_mode"]

if chat_mode == COLLECTION_MODE:
    config = RunnableConfig({
        "location": settings["location"],
        "search_limit": settings["search_limit"],
        "number_of_results": settings["number_of_results"],
        "affected_records": affected_records,
        "callbacks": [get_streamlit_cb(st.empty())],
    })

    # tools = [tools_set.save_results, tools_set.google_organic_search, tools_set.google_events_search, tools_set.google_local_search, tools_set.yelp_search]
    tools = [tools_set.save_results]
    agent = DataCollectionAgent(vector_store, tools, settings)
    agent.setup()

    chat_input = st.chat_input(
        "Type additonal query here to start data collection...")

    if chat_input:
        query = f"{settings['user_preferences']} \n\n {chat_input}"
        streamlit_prepare_execution(settings, config, agent, query, COLLECTION_MODE)

        with st.spinner("Collecting data...", show_time=True):
            messages = [HumanMessage(content=query)]

            result = agent.runnable.invoke(
                input={"messages": messages},
                config=config
            )

        streamlit_report_execution(result, tools)

        streamlit_display_storage(
            vector_store, affected_records, settings["location"])
    else:
        # streamlit_show_collection_home(agent)
        streamlit_show_home(agent.runnable, tools, "Data collection mode", "data-mining.png",
                                    "Instructions usage:\n\n **Common** - used for all AI LLM calls. Addtionally to that **Data collection** - used for data collection, **Summarize** - used for summarization")                
elif chat_mode == DISCOVERY_MODE:
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [tools_set.vector_store_search, tools_set.vector_store_by_id,
             tools_set.vector_store_delete, tools_set.vector_store_stats]

    # memory = st.session_state.memory
    agent = create_react_agent(name="Discovery",
        model=model, tools=tools, store=vector_store)

    chat_input = st.chat_input("Type query to search vector store...")
    if chat_input:
        config = RunnableConfig({
            "location": settings["location"],
            "thread_id": "1",
            "affected_records": affected_records,
            "callbacks": [get_streamlit_cb(st.empty())],
        })
        messages = [HumanMessage(content=chat_input)]
        messages.append(SystemMessage(content=prmt.discovery_system_prompt))

        result = agent.invoke(input={"messages": messages}, config=config)

        streamlit_report_execution(result, tools)
        streamlit_display_storage(vector_store, affected_records, "new", settings["location"])
    else:
        streamlit_show_home(agent, tools, "Discovery mode", "pinecone-logo.png",
                                    "Query the cached database (vector store) for existing information")
else: # Itinerary mode
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [tools_set.vector_store_search, tools_set.vector_store_stats]

    # memory = st.session_state.memory
    agent = create_react_agent(name="Itinerary",
                               model=model, tools=tools, store=vector_store)

    chat_input = st.chat_input(
        "Type additonal query here to start itinerary generation...")
    if chat_input:
        config = RunnableConfig({
            "location": settings["location"],
            "thread_id": "1",
            "affected_records": affected_records,
            "callbacks": [get_streamlit_cb(st.empty())],
        })
        messages = [HumanMessage(content=settings["user_preferences"] + "\n\n" + chat_input)]
        messages.append(SystemMessage(content=prmt.itinerary_system_prompt))

        streamlit_prepare_execution(
            settings, config, agent, messages[0].content, ITINERARY_MODE)
        
        result = agent.invoke(input={"messages": messages}, config=config)

        streamlit_report_execution(result, tools)
        streamlit_display_storage(
            vector_store, affected_records, "category", settings["location"])
    else:
        streamlit_show_home(agent, tools, "Itinerary mode", "itinerary.jpg",
                                    "Itinerary generation based on user preferences and query. AI uses cached database (vector store) to generate itinerary.")
