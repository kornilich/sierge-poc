import json
import os
from serpapi import GoogleSearch
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from typing import Optional, List, TypedDict, Annotated, Dict, Literal
from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field, ConfigDict, RootModel, model_validator, root_validator


CategoryEnum = Literal["Live Entertainment", "Movies & Film", "Museums & Exhibits", "Community Events & Activities",
                "Sports & Recreation", "Health & Wellness", "Learning & Skill-Building", "Shopping", "Food & Drink Experiences", "Self-Guided Activities & Destinations", "Other"]

class ActivityDetails(BaseModel):
    """Represents detailed information about an activity or event.
If certain fields lack sufficient data or are unavailable, they will be assigned the value `N/A`    
    """

    source: str = Field(
        default="Model", description="Source of the information. Can be 'Model' or tool name.")
    rank: Optional[int] = Field(default=None, description="Rank of the activity. Can be 1 to 5. Where 1 is the best and 5 is the worst fit to user's preferences."  )
    category: Optional[str] = Field(default="Other")
    name: Optional[str] = Field(
        default=None, description="Name/Title of the activity (e.g., Event Name, Venue Name, Destination Name).")
    description: Optional[str] = Field(default = None,
                                       description="Brief overview of activity, including cuisine, atmosphere, features and other relevant information")
    location: Optional[str] = Field(
        default=None, description="Location details (Address, GPS coordinates, or general area).")
    website: Optional[str] = Field(
        default=None, description="Website of the activity.")
    start_time: Optional[str] = Field(
        default=None, description="Start time for time-bound activities.")
    end_time: Optional[str] = Field(
        default=None, description="End time for time-bound activities.")
    hours_of_operation: Optional[str] = Field(
        default=None, description="Hours of operation for ongoing activities.")
    cost: Optional[str] = Field(
        default=None, description="Cost & Pricing details (Free, Ticket Price, Price Range).")
    booking_info: Optional[str] = Field(
        default=None, description="Booking or registration info (e.g., where to buy tickets or RSVP requirements).")

    # Nice-to-Have Fields
    family_friendliness: Optional[str] = Field(
        None, description="Indicates if the activity is family-friendly.")
    accessibility_features: Optional[List[str]] = Field(
        None,
        description=(
            "Accessibility features available (e.g., wheelchair accessible, ASL interpretation). "
            "Alternatively, a method to assess whether accessibility features are needed."
        )
    )
    age_restrictions: Optional[str] = Field(
        None, description="Age restrictions for the activity (e.g., All ages, 18+, etc.).")
    indoor_outdoor: Optional[str] = Field(
        None, description="Indicates if the activity is indoor or outdoor.")
    recommended_attire_or_equipment: Optional[str] = Field(
        None,
        description="Recommended attire or equipment for the activity (e.g., dress code or bring your own gear)."
    )
    weather_considerations: Optional[str] = Field(
        None,
        description=(
            "Weather-related considerations (Rain date, weather-related cancellations, recommended conditions)."
        )
    )


class ActivitiesList(BaseModel):
    """Holds a collection of activity details representing recommendations"""
    activities: List[ActivityDetails]
    reason: Optional[str] = Field(default="No reason provided", description="Reason for the recommendations and tools selection.")
    

@tool("web_search")
def web_search(query: str, config: RunnableConfig):
    """Universal search to find all places to go out using Google search. Can also be used
    to augment more 'general' knowledge to a previous specialist query."""
    # TODO: Consider pagination vs number of results
    
    result_types = [
        "organic_results",
        "local_results",
        "local_ads",
        "knowledge_graph",
        "discover_more_places",
        "events_results",
        "top_sights"
    ]

    results = serpapi_search(query, "google", config, result_types)
                            #  , mock_file = "mockups/serpapi-1.json")
    
    return results


@tool("events_search")
def events_search(query: str, config: RunnableConfig):
    """A specialized search utility that leverages Google's Event Search engine to find detailed, 
real-time information about events. 
This tool is designed to help users discover concerts, festivals, workshops, sports games, 
and other activities based on their query, location, and preferences."""
    # TODO: Consider pagination vs number of results
    
    result_types = [
        "events_results",
    ]
    
    results = serpapi_search(query, "google_events", config, result_types)
                            #  , mock_file = "mockups/serpapi-events-1.json")
    
    return results


@tool("local_search")
def local_search(query: str, config: RunnableConfig):
    """A specialized search utility that uses Google's Local Search engine to find 
geographically constrained results for places, businesses, and activities. 
This tool helps users discover nearby locations such as restaurants, attractions, 
shops, and services based on their query and current location."""
    # TODO: Consider pagination vs number of results
    
    result_types = [
        "ads_results",
        "local_results",
        "discover_more_places",
    ]

    results = serpapi_search(query, "google_local", config, result_types)
                            #  , mock_file = "mockups/serpapi-locals-1.json")
    
    return results

def serpapi_search(query: str, engine: str, config: RunnableConfig, result_types: List[str] = None, mock_file: str = None):
    
    cfg = config.get("configurable", {})
    params = {
        "engine": engine,
        "api_key": os.getenv("SERPAPI_KEY"),
        "location": cfg["location"],
        "num": cfg["number_of_results"],
        "q": query
    }

    results = {}
    if mock_file:
        with open(mock_file, 'r') as f:
            results = json.load(f)
    else:
        search = GoogleSearch(params)
        results = search.get_json()
        
    filtered_results = {}

    search_url = next((v for k, v in results.get("search_metadata", {}).items() if k.startswith("google") and k.endswith("_url")), "")
    
    # if search_url == "":
    #     search_url = results.get("search_metadata", {}).get("google_url", "")
    search_query = results.get("search_parameters", {}).get("q", "")
    if mock_file:
        search_query = "Mockup results"

    # Put only selected items in result
    for item in results.items():
        if not result_types or item[0] in result_types:
            filtered_results[item[0]] = {
                "search_type": item[0],
                "search_url": search_url,
                "search_query": search_query,
                "search_results": item[1]
            }

    return filtered_results
