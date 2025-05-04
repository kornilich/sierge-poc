import re

import streamlit as st
from agents.data_collection_agent import DataCollectionAgent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from agents.geocoding import get_datetime_info, get_weather_data
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
    st.session_state.memory = InMemorySaver()


# HACK: Keep this to preserve var in runnable config, otherwise it will be removed
affected_records = ["Blank"]

load_environment()

settings = streamlit_settings(chat_mode_list, ITINERARY_MODE)
chat_mode = settings["chat_mode"]

vector_store = VectorDatabase(collection_name=settings["base_location"])

if chat_mode == COLLECTION_MODE:
    config = RunnableConfig({
        "base_location": settings["base_location"],
        "exact_location": settings["exact_location"],
        "search_limit": settings["search_limit"],
        "number_of_results": settings["number_of_results"],
        "affected_records": affected_records,
        "callbacks": [get_streamlit_cb(st.empty())],
    })

    tools = [tools_set.save_results, tools_set.google_organic_search,
             tools_set.google_events_search, tools_set.google_local_search, tools_set.yelp_search]
    # tools = [tools_set.save_results, tools_set.yelp_search]

    agent = DataCollectionAgent(vector_store, tools, settings)
    agent.setup()

    chat_input = st.chat_input(
        "Type additonal query here to start data collection...")

    if chat_input:
        query = f"{settings['user_preferences']} \n\n {chat_input}"
        datetime_now_info = get_datetime_info(
            settings["exact_location"]["lat"], settings["exact_location"]["lon"])
        streamlit_prepare_execution(COLLECTION_MODE, settings, config, query, agent=agent, today=datetime_now_info)

        with st.spinner("Collecting data...", show_time=True):
            messages = [HumanMessage(content=query)]

            result = agent.runnable.invoke(
                input={"messages": messages},
                config=config
            )

        streamlit_report_execution(result, tools)

        streamlit_display_storage(vector_store, affected_records)
    else:
        hide_diagram = True if len(tools) > 3 else False
        streamlit_show_home(agent.runnable, tools, "Data collection mode", "data-mining.png",
                                    "Instructions usage:\n\n **Common** - used for all AI LLM calls. Addtionally to that **Data collection** - used for data collection, **Summarize** - used for summarization", hide_diagram)                
elif chat_mode == DISCOVERY_MODE:
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [tools_set.vector_store_search, tools_set.vector_store_scroll, tools_set.vector_store_by_id,
             tools_set.vector_store_delete, tools_set.vector_store_metrics]

    memory = st.session_state.memory
    agent = create_react_agent(name="Discovery",
        model=model, tools=tools, store=vector_store, checkpointer=memory)

    chat_input = st.chat_input("Type query to search vector store...")
    if chat_input:
        config = RunnableConfig({
            "base_location": settings["base_location"],
            "exact_location": settings["exact_location"],
            "search_radius": settings["search_radius"],
            "thread_id": "1",
            "affected_records": affected_records,
            "callbacks": [get_streamlit_cb(st.empty())],
        })
        messages = [HumanMessage(content=chat_input)]
        messages.append(SystemMessage(content=prmt.discovery_system_prompt))

        result = agent.invoke(input={"messages": messages}, config=config)

        streamlit_report_execution(result, tools)
        streamlit_display_storage(vector_store, affected_records)
    else:
        streamlit_show_home(agent, tools, "Discovery mode", "qdrant-logo.png",
                                    "Query the cached database (vector store) for existing information")
else: # Itinerary mode
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [tools_set.vector_store_search, tools_set.vector_store_metrics]

    agent = create_react_agent(name="Itinerary",
                               model=model, tools=tools, store=vector_store)

    chat_input = st.chat_input(
        "Type additonal query here to start itinerary generation...")
    if chat_input:
        datetime_now_info = get_datetime_info(settings["exact_location"]["lat"], settings["exact_location"]["lon"])
        
        weather_data = get_weather_data(settings["exact_location"]["lat"], settings["exact_location"]["lon"])
        
        config = RunnableConfig({
            "base_location": settings["base_location"],
            "exact_location": settings["exact_location"],
            "search_radius": settings["search_radius"],
            "thread_id": "1",
            "affected_records": affected_records,
            "callbacks": [get_streamlit_cb(st.empty())],
        })
        
        query = prmt.format_prompt(settings["user_preferences"], location=settings["base_location"]) 
        query = query +"\n\n" + chat_input
        extra_query = datetime_now_info + prmt.itinerary_extra_human_prompt
        system_prompt = prmt.format_prompt(settings["itinerary_instructions"], location=settings["base_location"])

        streamlit_prepare_execution(
            ITINERARY_MODE, settings, config, query, system_prompt, today=datetime_now_info, weather_data=weather_data)
        
        with st.chat_message("human"):
            with st.expander("Additional info", expanded=False):
                st.write(extra_query)

        messages = [HumanMessage(content=query + "\n\n" + extra_query)]
        messages.append(SystemMessage(content=system_prompt))

        result = agent.invoke(input={"messages": messages}, config=config)

        # need plan to spend one fancy day in dallas
        streamlit_report_execution(result, tools)
        streamlit_display_storage(
            vector_store, affected_records)
   
        # Extract used activities IDs from the response     
        if result.get("messages"):
            last_message = result["messages"][-1].content
    #         last_message = """
    # Combines your interest in yoga and outdoor activities, offering a serene environment.\n5. **The Granada Theater**: Provides an opportunity to enjoy live indie and alternative music in a relaxed setting.\n\n### used_activities:\n```json\n{\n    "ids": [\n        "6641d21f-46fb-4670-97a8-12e4b98bd89d",\n        "d27da075-a9e1-583b-9db1-50bd363f8d7c",\n        "4eb9e763-0d27-508c-995d-5555146a4c15",\n        "88aae41a-167f-52bf-8d7b-d7cf894aa583",\n        "ab9472bc-9c74-5725-a37a-95c5ce2103cb"\n    ]\n}\n```\n\nThis itinerary offers a balanced mix of activities that cater to your interests and preferences, ensuring a memorable day in Dallas.        
    #         """        
            # Extract JSON content between ```json and ``` using regex
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', last_message, re.DOTALL)
                if json_match:
                    json_content = eval(json_match.group(1))
                    st.json(json_content, expanded=True)
            except Exception as e:
                st.error(f"Error parsing JSON: {e}")


    else:
        streamlit_show_home(agent, tools, "Itinerary mode", "itinerary.jpg",
                                    "Itinerary generation based on user preferences and query. AI uses cached database (vector store) to generate itinerary.")
