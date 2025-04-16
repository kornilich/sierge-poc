import json
import os
import uuid
from serpapi import GoogleSearch
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedStore
from typing import List, Dict, Annotated
from langchain_core.documents import Document

from agents.vector_database import VectorDatabase
from agents.activities import ActivitiesList
@tool("google_organic_search")
def google_organic_search(query: str, config: RunnableConfig):
    """Universal search tool to find all places to go out using Google search. Can also be used
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


@tool("google_events_search")
def google_events_search(query: str, config: RunnableConfig):
    """A specialized search tool that leverages Google's Event Search engine to find detailed, 
real-time information about events. 
This tool is designed to help users discover concerts, festivals, workshops, sports games, 
and other activities based on their query, location, and preferences."""

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
This tool helps users discover nearby locations such as restaurants, attractions, 
shops, and services based on their query and current location."""

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
        "find_loc": cfg["location"],
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
        "location": cfg["location"],
        "num": cfg["number_of_results"],
        "q": query
    }

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
        search_query = results.get("find_desc", {}).get("q", "")  # Yelp

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

    store.add_documents(activities=data.activities)
    
    cfg = config.get("configurable", {})
    if "affected_records" in cfg:
        cfg["affected_records"].extend([activity.id for activity in data.activities])
        
    return {
        "status": "success",
        "message": "Data saved",
        "data_source": data.activities[0].data_source if data.activities else "n/a",
        "records_affected": len(data.activities),
    }
    

@tool("vector_store_search")
def vector_store_search(query: str, config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()], k: int = 4):
    """
        Search and retrieve data from vector store
        Parameters:
            query: query to search for
            k: number of results to return
    """
    
    activities = store.similarity_search(query, k)
    
    cfg = config.get("configurable", {})
    if "affected_records" in cfg:
        cfg["affected_records"].extend([activity.id for activity in activities])
    
    return {
        "similarity_search": {
            "data_source": "pinecone",
            "search_type": "vector_store",
            "search_url": "https://www.pinecone.io",
            "search_query": query,
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

    activities = store.get_by_ids(ids)

    cfg = config.get("configurable", {})
    if "affected_records" in cfg:
        cfg["affected_records"].extend([document.id for document in activities])

    return {
        "vector_store_by_id": {
            "data_source": "pinecone",
            "search_type": "vector_store",
            "search_url": "https://www.pinecone.io",
            "search_query": str(ids),
            "search_results": [activity.model_dump() for activity in activities]
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
            "data_source": "pinecone",
            "search_type": "vector_store",
            "search_url": "https://www.pinecone.io",
            "search_query": str(ids),
            "search_results": []
        }
    }


@tool("vector_store_stats")
def vector_store_stats(config: RunnableConfig, store: Annotated[VectorDatabase, InjectedStore()]):
    """
        Get stats from vector store
    """

    stats = store.stats()

    return {
        "vector_store_stats": {
            "data_source": "pinecone",
            "search_type": "vector_store",
            "search_url": "https://www.pinecone.io",
            "search_query": "Store stats",
            "search_results": [stats]
        }
    }
