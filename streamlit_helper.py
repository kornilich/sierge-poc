from dotenv import load_dotenv
import pandas as pd
import requests
import streamlit as st
import inspect
import os
import pytz
from dateutil import parser
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
from streamlit.external.langchain import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from typing import TypeVar, Callable
from agents.geocoding import get_location_from_string
import agents.prompts as prmt
import json
import googlemaps

from langchain_core.runnables.graph import NodeStyles


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

def get_weather_data(latitude, longitude):
    """Get current weather data from Google Weather API using coordinates."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
    try:
        url = f"https://weather.googleapis.com/v1/currentConditions:lookup?key={api_key}&location.latitude={latitude}&location.longitude={longitude}&unitsSystem=IMPERIAL"
        
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        weather_data = response.json()
        
        if weather_data:
            return {
                "current_time": weather_data['currentTime'],
                "time_zone": weather_data['timeZone']['id'],
                "temperature": weather_data['temperature']['degrees'],
                "unit": weather_data['temperature']['unit'],
                "condition": weather_data['weatherCondition']['description']['text'],
                "icon_url": weather_data['weatherCondition']['iconBaseUri'],
                "humidity": weather_data['relativeHumidity'],
                "wind_speed": weather_data['wind']['speed']['value'],
                "wind_direction": weather_data['wind']['direction']['degrees'],
                "feels_like": weather_data['feelsLikeTemperature']['degrees'],
                "pressure": weather_data['airPressure']['meanSeaLevelMillibars'],
            }
        else:
            st.error("No weather data found")
            return None
    except Exception as e:
        st.error(f"Error fetching weather data: {str(e)}")
        return None

def streamlit_settings(chat_mode_list, current_chat_mode=None):
    st.set_page_config(page_title='Sierge PoC', layout='wide')

    user_preferences = ""
    data_collection_prompt = ""
    itinerary_instructions = ""
    search_limit = 2
    number_of_results = 5
    search_radius = 0

    with st.sidebar:
        chat_mode = st.segmented_control(
            "Data mode", chat_mode_list, default=current_chat_mode, selection_mode="single"
        )

        if chat_mode in [COLLECTION_MODE, ITINERARY_MODE]:
            with st.expander("Preferences"):
                user_preferences = st.text_area(
                    ":red[**Fixed, Contextual, Situational**]", value=prmt.user_preferences, height=72*6)
        
        if chat_mode == COLLECTION_MODE:
            with st.expander("Instructions"):
                data_collection_prompt = st.text_area(
                    ":red[**Data collection**]",
                    value=prmt.data_collection_system_prompt, height=72*6)

        if chat_mode == ITINERARY_MODE:
            with st.expander("Instructions"):
                itinerary_instructions = st.text_area(
                    ":red[**Itinerary**]",
                    value=prmt.itinerary_system_prompt, height=72*6)

        with st.expander("Agent settings", expanded=True):
            base_location = st.selectbox(
                "Location", ("Dallas, Texas, United States", "Los Angeles, California, United States"))
            area_location = st.text_input("Area", placeholder="Zip code, place or coordinates")
            
            exact_location = {}
            area_location = area_location if area_location else base_location
            
            location_details = get_location_from_string(area_location)
            if location_details:
                st.info(f"📍 {location_details['formatted_address']}")
                exact_location = {
                    'lat': location_details['latitude'],
                    'lon': location_details['longitude'],
                    'formatted_address': location_details['formatted_address']
                }
                
            if chat_mode != COLLECTION_MODE:
                search_radius = st.slider(
                        "Search radius (meters)", min_value=0, max_value=20000, value=5000)
            
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
        "base_location": base_location,
        "exact_location": exact_location,
        "search_limit": search_limit,
        "number_of_results": number_of_results,
        "search_radius": search_radius,
        "chat_mode": chat_mode
    }

def streamlit_show_home(agent, tools, title, image_name, description, hide_diagram=False):
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
    
    node_styles = NodeStyles(
        default='fill:#ff4b4b,line-height:1.2,fill-opacity:0.5, stroke:#ff4b4b',
        first='fill-opacity:0',
        last='fill-opacity:0',
    )
    
    img = agent.get_graph().draw_mermaid_png(node_colors=node_styles)

    def _list_tools():
        st.subheader(":gray[Tools]")
        st.write("Tool name and instructions for the agent on when and how using it")
        for tool in tools:
            st.markdown(f"**{tool.name}**: {tool.description}")

    if hide_diagram:
        _list_tools()
    else: 
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image(img, width=300, caption="Congitive model")
        with col2:
            _list_tools()

    return

def streamlit_prepare_execution(settings, config, agent, query, mode):    
    with st.chat_message("ai"):
        if mode == COLLECTION_MODE:
            with st.expander("Data collection prompt", expanded=False):
                st.write(agent.get_system_prompt(
                    settings["data_collection_prompt"], config))
        else:
            cfg = config.get('configurable', config)
            base_location = cfg.get('base_location', '')

            with st.expander("Itinerary prompt", expanded=False):
                st.write(prmt.format_prompt(settings["itinerary_instructions"], location=base_location))
                
    exact_location = settings['exact_location']

    col1, col2, col3 = st.columns(3)
    with col1:
        st.map(pd.DataFrame({
            'lat': [exact_location['lat']],
            'lon': [exact_location['lon']]
        }), height=300)
        
    weather_data = get_weather_data(
        exact_location['lat'], exact_location['lon'])
    
    if weather_data:
        with col2:
            st.subheader("Time and Location")
            
            dt = parser.isoparse(weather_data['current_time'])
            dt = dt.astimezone(pytz.timezone(weather_data['time_zone']))
            
            st.write(f"{dt.strftime('%A, %B %d, %Y at %H:%M')}")
            st.write(f"Time zone: {weather_data['time_zone']}")
            st.info(
                f"📍{exact_location['formatted_address']}\n\n{exact_location['lat']}, {exact_location['lon']}")
        with col3:        
            st.subheader("Current Weather")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="Temperature",
                    value=f"{weather_data['temperature']}° {weather_data['unit'][0]}",
                    delta=None
                )
                st.write(f"Feels like: {weather_data['feels_like']}° {weather_data['unit'][0]}")
            if 'icon_url' in weather_data:
                st.image(f"{weather_data['icon_url']}.png", width=50)
            with col2:
                st.write(f"Humidity: {weather_data['humidity']}%")
                st.write(f"Pressure: {weather_data['pressure']} hPa")
                st.write(f"Wind: {weather_data['wind_speed']} m/s")
                if weather_data['wind_direction'] != 'N/A':
                    st.write(f"Wind Direction: {weather_data['wind_direction']}°")
            st.write(f"Condition: {weather_data['condition'].title()}")

    with st.chat_message("human"):
        with st.expander("Human prompt", expanded=False):
            st.write(query)          
            
    settings_bages = f":gray-badge[Model: {settings['model']}] :gray-badge[Location: {settings['base_location']}]"

    if mode == COLLECTION_MODE:
        settings_bages += f":gray-badge[Search limit: {settings['search_limit']}] :gray-badge[Number of results: {settings['number_of_results']}]"
        
    st.markdown(settings_bages)

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
                    try:
                        json_content = json.loads(msg.content)
                    except json.JSONDecodeError:
                        st.write(msg.name)
                        st.error(f"Error parsing tool message: {msg.content}")
                        continue
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

def streamlit_display_storage(storage, data_ids, group_by=None):
    # Display stored search results
    st.subheader(":gray[Affected data]")

    if len(data_ids) < 2: # First record always "Blank"
        st.info("No data available")
        return

    activities = storage.get_by_ids(data_ids)

    # Convert activities to DataFrame
    df = pd.DataFrame([activity.model_dump() for activity in activities])

    # Move id column to the end if it exists
    cols = [col for col in df.columns if col != 'id'] + ['id']
    
    # Reorder columns to put full_address and coordinates after location
    if 'location' in cols:
        loc_idx = cols.index('location')
        # Remove these columns from their current position if they exist
        cols = [c for c in cols if c not in ['full_address', 'coordinates']]
        # Insert them after location
        cols[loc_idx+1:loc_idx+1] = ['full_address', 'coordinates']
    
    # Remove columns where all values are None or 'N/A'
    df = df.replace('N/A', None)
    empty_cols = [col for col in cols if df[col].isna().all()]
    if empty_cols:
        st.info("These columns have no data: " + ", ".join(empty_cols))
    cols = [col for col in cols if not df[col].isna().all()]

    if len(cols) < 2:
        st.error("Not enough columns to display data")
        return

    df = df[cols]

    # Convert timestamp fields to datetime using .loc
    df.loc[:, 'created'] = pd.to_datetime(df['created_at'], unit='s')
    df.loc[:, 'updated'] = pd.to_datetime(df['updated_at'], unit='s')

    # Add 'new' column based on created_at and updated_at comparison using .loc
    df.loc[:, 'new'] = (df['created_at'] == df['updated_at']).map({True: 'yes', False: 'no'})
    # Move 'new' column to first position
    cols = ['new'] + [col for col in df.columns if col != 'new']
    df = df[cols]

    # Remove timestamp columns
    df = df.drop(['created_at', 'updated_at'], axis=1)

    if len(df) == 0:
        st.info("No data collected")
        return
    
    # Group by source and display in expandable sections
    if group_by in df.columns:
        for source in df[group_by].unique():
                source_df = df[df[group_by] == source]
                with st.expander(f"{group_by}: {source}"):
                    st.dataframe(source_df.drop(group_by, axis=1),
                                use_container_width=True)
        return
    elif group_by:
        st.error(f"Structure issue: no {group_by} column found")
    
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
    # os.environ["PINECONE_API_KEY"] = st.secrets["PINECONE_API_KEY"]
    # os.environ["PINECONE_INDEX"] = st.secrets["PINECONE_INDEX"]
    os.environ["QDRANT_API_KEY"] = st.secrets["QDRANT_API_KEY"]
    os.environ["QDRANT_URL"] = st.secrets["QDRANT_URL"]
    os.environ["GOOGLE_MAPS_API_KEY"] = st.secrets["GOOGLE_MAPS_API_KEY"]

    return
