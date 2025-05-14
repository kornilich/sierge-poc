import re
import json
from urllib.parse import quote

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
import numpy as np
import pandas as pd


from integrations.geocoding import PlaceAddressDetails, get_route_plan
from agents.data_collection_agent import DataCollectionAgent
from integrations.geocoding import get_datetime_info, get_weather_data
from integrations.vector_database import VectorDatabase
import agents.tools as tools_set
import agents.prompts as prmt

import streamlit as st
from streamlit_helper import COLLECTION_MODE, DISCOVERY_MODE, ITINERARY_MODE, get_plan_description
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

settings = streamlit_settings(chat_mode_list, COLLECTION_MODE)
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
             tools_set.google_events_search, tools_set.google_local_search, tools_set.yelp_search, tools_set.web_page_data_extraction]
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
                                    "Query the cached database (vector store) for existing information", hide_diagram=True)
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
        extra_query = datetime_now_info + "\n\n" + "When necessary, use the following weather forecast: " + \
            str(weather_data["forecastDays"]) + "\n\n" + prmt.itinerary_extra_human_prompt
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
            vector_store, affected_records, expand=False)
   
        # Extract used activities IDs from the response     
        # result = {"messages": [HumanMessage(content="")]}        
        
        if result.get("messages"):
            last_message = result["messages"][-1].content

            # Find JSON content between ```json and ```
            json_match = re.search(r'```json\s*(.*?)\s*```', last_message, re.DOTALL)
            
            # json_match = True
            
            if json_match:
                try:
                    # Parse the JSON content
                    activities_json = json.loads(json_match.group(1))
                    
                    # activities_json = json.load(open("mockups/itinerary-response-2.json"))
                    
                    # Save activities JSON to file
                    # with open("mockups/itinerary-response-2.json", "w") as f:
                    #     json.dump(activities_json, f, indent=4)
                    
                    # Add starting point
                    place = PlaceAddressDetails(
                        name="Start point",
                        formatted_address=settings["exact_location"]["formatted_address"],
                        latitude=settings["exact_location"]["lat"],
                        longitude=settings["exact_location"]["lon"]
                    )
                    places = [place]

                                        
                    # Extract activities list if it exists
                    map_df = pd.DataFrame(
                        np.array([[settings["exact_location"]["lat"], settings["exact_location"]["lon"]]]),
                        columns=["lat", "lon"],
                    )
                    
                    if "activities" in activities_json:                      
                        for activity in activities_json["activities"]:
                            # Convert each activity to PlaceAddressDetails
                            lat = activity.get("latitude")
                            lon = activity.get("longitude")
                            
                            if lat is None or lon is None:
                                lat = settings["exact_location"]["lat"]
                                lon = settings["exact_location"]["lon"]
                            
                            place = PlaceAddressDetails(
                                name=activity.get("name"),
                                formatted_address=activity.get("full_address"),
                                latitude=lat,
                                longitude=lon
                            )
                            
                            map_df.loc[len(map_df)] = [place.latitude, place.longitude]
                            places.append(place)
                except json.JSONDecodeError:
                    st.error("Failed to parse activities JSON")
                except Exception as e:
                    st.error(f"Error processing activities: {str(e)}")
                                                
                st.write("Route plan with original waypoint order")
                route_plan = get_route_plan(places)
                                
                st.json(route_plan, expanded=False)
        
                map_waypoints_param, route_df = get_plan_description(places, route_plan['routes'][0])
                st.dataframe(route_df, use_container_width=True)
                
                st.write("Route plan with optimized waypoint order")
                route_plan = get_route_plan(places, optimize_waypoint_order=True)
                st.json(route_plan, expanded=False)

                # Rearange places order according to optimized waypoints
                route = route_plan['routes'][0]
                
                new_places = [places[0]]                
                for idx in route['optimizedIntermediateWaypointIndex']:
                    new_places.append(places[idx + 1])                    
                new_places.append(places[-1])
                
                map_waypoints_optimized_param, route_df = get_plan_description(
                    new_places, route)
                st.dataframe(route_df, use_container_width=True)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.map(map_df, height=300)
                with col2:
                    st.link_button(
                        "Open original route", f"https://www.google.com/maps/dir/{map_waypoints_param}", type="primary", icon=":material/map:")
                    st.link_button(
                        "Open optimized route", f"https://www.google.com/maps/dir/{map_waypoints_optimized_param}", type="primary", icon=":material/map:")

    else:
        streamlit_show_home(agent, tools, "Itinerary mode", "itinerary.jpg",
                                    "Itinerary generation based on user preferences and query. AI uses cached database (vector store) to generate itinerary.", hide_diagram=True)
