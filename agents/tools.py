import json
import os
from serpapi import GoogleSearch
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedStore
from typing import List, Dict, Annotated

from agents.geocoding import get_place_address, get_validated_address
from agents.vector_database import VectorDatabase
from agents.activities import ActivitiesList, ActivityDetails
from uule_convertor import UuleConverter

from langchain_hyperbrowser import HyperbrowserExtractTool

# check this page https://blog.offerpad.com/things-to-do-dallas-tx
# check this page https://www.visitdallas.com
@tool("web_page_data_extraction")
def web_page_data_extraction(url: str):
    """
        Extract data from a single web page
    """
    results = HyperbrowserExtractTool().run(
        {
            "url": url,
            "schema": ActivitiesList,
            "session_options": {"session_options": {"use_proxy": True}},
        }
    )
    
    results_info = {
        "data_source": "hyperbrowser",
        "search_type": "extraction",
        "search_url": url,
        "search_query": "Extract data from web page",
        "search_results": results["data"]["activities"]
    }

    return {"search_type": "web_page_data_extraction",
            "results": results_info}

@tool("google_organic_search")
def google_organic_search(query: str, config: RunnableConfig):
    """Universal search tool to find all places to go out using Google search. 

Use it to search:
- Movies & Film (showtimes, cinemas)
- Other categories which are not covered by specialized search tools

Can also be used to augment more 'general' knowledge to a previous specialist query."""
    # TODO: Consider pagination vs number of results

    result_types = [
        "organic_results",
        "local_results",
        "local_ads",
        "knowledge_graph",
        "discover_more_places",
        "events_results",
        "top_sights",
        "showtimes",
    ]

    results = serpapi_search(query, "google", config, result_types)
    #  , mock_file = "mockups/serpapi-1.json")

    return results

@tool("google_events_search")
def google_events_search(query: str, config: RunnableConfig):
    """A specialized search tool that leverages 
Google's Event Search engine to find detailed, real-time information about events. 
Use this tool to find 
- Live Entertainment Events: Music Concerts, Sporting events, comedy shows
- Community Activities
- Learning & Skillbuilding: cooking classes, art classes, workshops, seminars
and other activities based on your query"""

    result_types = [
        "events_results",
    ]

    results = serpapi_search(query, "google_events", config, result_types)
    #  , mock_file = "mockups/serpapi-events-1.json")

    return results

@tool("google_local_search")
def google_local_search(query: str, config: RunnableConfig):
    """A specialized search tool that uses Google's Local Search engine to find 
geographically constrained results for places, businesses, and activities. 

Use it to find following categories:
- Outdoor & Recreation Activities: Hiking trails, Biking, Water sports, parks, apple picking, zoo, park events, farms, beach
- Health & Wellness
- Shopping: shopping mall, lifestyle center, boutique, outdoor shopping plaza, sample sales, estate sales, warehouse sales
- Food & Drink Experiences
- Self-Guided Activities
- Attractions
"""

    result_types = [
        "ads_results",
        "local_results",
        "discover_more_places",
    ]

    results = serpapi_search(query, "google_local", config, result_types)
    #  , mock_file = "mockups/serpapi-locals-1.json")

    return results

@tool("yelp_search")
def yelp_search(query: str, config: RunnableConfig):
    """
    Search tool which performs a Yelp search to retrieve 
    information about restaurants, bars, nightlife, businesses or services based on the provided query. 
    """
    # TODO: Maybe use advanced search parameters

    result_types = [
        "ads_results",
        "organic_results",
    ]

    cfg = config.get("configurable", {})
    extra_params = {
        "find_desc": query,
        "find_loc": cfg["exact_location"]["formatted_address"],
    }

    results = serpapi_search(query, "yelp", config, result_types, extra_params)
    #  , mock_file = "mockups/serpapi-locals-1.json")

    return results

def serpapi_search(query: str, engine: str, config: RunnableConfig, result_types: List[str] = None, extra_params: Dict[str, str] = None, mock_file: str = None):
    # TODO: Consider use pagination together with number of results


    cfg = config.get("configurable", {})
    params = {
        "engine": engine,
        "api_key": os.getenv("SERPAPI_KEY"),
        "num": cfg["number_of_results"],
        "q": query
    }
    
    exact_location = cfg["exact_location"]
    params["uule"] = UuleConverter.encode(
        exact_location["lat"], exact_location["lon"])

    if extra_params:
        params.update(extra_params)

    results = {}
    if mock_file:
        with open(mock_file, 'r') as f:
            results = json.load(f)
    else:
        search = GoogleSearch(params)
        results = search.get_json()

    filtered_results = {}

    search_url = next((v for k, v in results.get("search_metadata", {}).items(
    ) if k.startswith("google") and k.endswith("_url")), "")
    if search_url == "":
        search_url = results.get("search_metadata", {}).get("yelp_url", "")

    search_query = results.get("search_parameters", {}).get("q", "")
    if search_query == "":
        search_query = results.get("search_parameters", {}).get(
            "find_desc", "")  # Yelp

    if mock_file:
        search_query = "Mockup results"

    # Put only selected items in result
    for item in results.items():
        if not result_types or item[0] in result_types:
            filtered_results[item[0]] = {
                "data_source": engine,
                "search_type": item[0],
                "search_url": search_url,
                "search_query": search_query,
                "search_results": item[1]
            }

    # Add error information if present
    if "error" in results:
        filtered_results["error"] = {
            "data_source": engine,
            "search_type": "error",
            "search_url": search_url,
            "search_query": search_query,
            "search_results": [results["error"]]
        }
        
    return filtered_results
    
def add_full_address(activities: List[ActivityDetails], base_location: str, location_bias_lat: float, location_bias_lon: float):
# Goal find most likely address for activity

# Correct address has priority over Place name 
#
# That means if Address exists and Place exists
# but Place has difference address we will assign
# this address to place even if it's wrong
#
# Using opposite approach fails when activity is not in
# Google Places database. It uses similarity search and
# returns random results for places
#
# Address considered correct if passes address validation
# If place search is used, it will be normalized by address validation
# to reduce dublicates
    
    for activity in activities:
        if not activity.full_address:
            address_normalized = False
            if activity.location:
                address_details = get_validated_address(activity.location, base_location)
                if not address_details:
                    address_details = get_place_address(
                        f"{activity.name}, {activity.location}", location_bias_lat, location_bias_lon)
                else:
                    address_normalized = True
            else:
                address_details = get_place_address(
                    activity.name, location_bias_lat, location_bias_lon)
                                    
            if address_details:
                if not address_normalized:
                    validated_address_details = get_validated_address(
                        address_details.formatted_address, base_location)
                    if validated_address_details:
                        address_details = validated_address_details

                activity.full_address = address_details.formatted_address
                activity.coordinates = {
                    "lat": address_details.latitude, "lon": address_details.longitude}
         
@tool("save_results")
def save_results(data: ActivitiesList, config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()]):
    """
        Save the results provided by other tools to persistent storage for future use.
        Parameters:
            data: The results in ActivitiesList schema to save  
        Returns:
            status: "success" if the result was saved successfully
            message: "Data saved" if the result was saved successfully
            data_source: "data_source" of the result
            records_affected: number of records saved
    """
    cfg = config.get("configurable", {})    
    exact_location = cfg["exact_location"]
    
    add_full_address(
        data.activities, cfg["base_location"], exact_location["lat"], exact_location["lon"])

    store.save_activities(activities=data.activities)
    
    if "affected_records" in cfg:
        cfg["affected_records"].extend([activity.id for activity in data.activities])
        
    return {
        "status": "success",
        "message": "Data saved",
        "data_source": data.activities[0].data_source if data.activities else "n/a",
        "records_affected": len(data.activities),
    }
    
@tool("vector_store_search")
def vector_store_search(query: str, config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()], limit: int = 5):
    """
        Search and retrieve data from vector store
        Parameters:
            query: query to search for
            limit: number of results to return
    """
    
    cfg = config.get("configurable", {})
    
    if cfg["search_radius"] > 0:
        geo_filter = {
            "lat": cfg["exact_location"]["lat"],
            "lon": cfg["exact_location"]["lon"],
            "radius": cfg["search_radius"]
        }
        activities = store.similarity_search(query, limit, geo_filter)
    else:    
        activities = store.similarity_search(query, limit)
        
    
    if "affected_records" in cfg:
        cfg["affected_records"].extend([activity.id for activity in activities])
    
    return {
        "similarity_search": {
            "data_source": "qdrant",
            "search_type": "vector_store",
            "search_url": "https://qdrant.io",
            "search_query": query,
            "search_results": [activity.model_dump() for activity in activities]
        }
    }

@tool("vector_store_scroll")
def vector_store_scroll(config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()], offset: str = None, limit: int = 10):
    """
        Returns all records(points) in a page-by-page manner. 
        All resulting points are sorted by id. 
        To query the next page specify the last id in the offset field. 

        Parameters:
            offset: id of the last record to start from
            limit: number of results to return
    """

    cfg = config.get("configurable", {})

    activities = store.scroll_collection(offset, limit)

    if "affected_records" in cfg:
        cfg["affected_records"].extend(
            [activity.id for activity in activities])

    return {
        "database_scroll": {
            "data_source": "qdrant",
            "search_type": "vector_store",
            "search_url": "https://qdrant.io",
            "search_query": f"Scroll from {offset}",
            "search_results": [activity.model_dump() for activity in activities]
        }
    }

@tool("vector_store_by_id")
def vector_store_by_id(ids: List[str], config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()]):
    """
        Search and retrieve data from vector store by ids
        Parameters:
            ids: list of ids to search for
    """
    cfg = config.get("configurable", {})

    activities = store.get_by_ids(ids)

    if "affected_records" in cfg:        
        cfg["affected_records"].extend([document.id for document in activities])

    return {
        "vector_store_by_id": {
            "data_source": "qdrant",
            "search_type": "vector_store",
            "search_url": "https://qdrant.io",
            "search_query": str(ids),
            "search_results": [activity.model_dump() for activity in activities]
        }
    }
    
@tool("vector_store_metrics")
def vector_store_metrics(config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()]):
    """
        Get metrics from vector store
    """

    metrics = store.get_metrics()

    return {
        "vector_store_metrics": {
            "data_source": "qdrant",
            "search_type": "vector_store",
            "search_url": "https://qdrant.io",
            "search_query": "Store metrics",
            "search_results": [metrics]
        }
    }

@tool("vector_store_delete")
def vector_store_delete(ids: List[str], config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()]):
    """
        Delete data from vector store by ids
        Parameters:
            ids: list of ids to delete
    """

    store.delete_by_ids(ids)

    return {
        "vector_store_by_id": {
            "data_source": "qdrant",
            "search_type": "vector_store",
            "search_url": "https://qdrant.io",
            "search_query": str(ids),
            "search_results": []
        }
    }
