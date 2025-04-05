import os
from serpapi import GoogleSearch
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool("web_search")
def web_search(query: str, config: RunnableConfig):
    """Finds general knowledge information using Google search. Can also be used
    to augment more 'general' knowledge to a previous specialist query."""
    
    return "test"
    
    params = {
        "engine": "google",
        "api_key": os.getenv("SERPAPI_KEY"),
        "location": config["location"],
        "num": config["number_of_results"],
        "q": query
    }
    
    search = GoogleSearch(params)
    results = search.get_json()
    
    filtered_results = {}
    
    if "local_results" in results and results["local_results"]:
        filtered_results["local_results"] = results["local_results"]['places']
        
    if "organic_results" in results and results["organic_results"]:
        filtered_results["organic_results"] = results["organic_results"]
        
    if "knowledge_graph" in results and results["knowledge_graph"]:
        filtered_results["knowledge_graph"] = results["knowledge_graph"]
        
    if "discover_more_places" in results and results["discover_more_places"]:
        filtered_results["discover_more_places"] = results["discover_more_places"]

    if "events_results" in results and results["events_results"]:
        filtered_results["events_results"] = results["events_results"]
        
    if "top_sights" in results and results["top_sights"]:
        filtered_results["top_sights"] = results["top_sights"]
        
    contexts = filtered_results
    
    return contexts
    # return "The Best Vegan Restaurants Around Dallas\nThe Best Vegan Restaurants Around Dallas · Recipe Oak Cliff · Spiral Diner & Bakery · Maiden · Casa Del Vegano · Vegan Food House · El Palote ...\nhttps://dallas.eater.com/maps/dallas-best-vegan-restaurants\n---\nThe Best Vegan Restaurants in Dallas: Our Picks\nVegan Spots in Dallas · Casa Del Vegano · Kalachandjis · HG Sply Co. · HopeBoy's Kitchen · Recipe Oak Cliff · Vegan Food House · Vegan Food House · Related ...\nhttps://www.visitdallas.com/blog/vegan-spots-in-dallas/\n---\nNice restaurants with good vegan options? : r/Dallas\nResident Taqueria in Lake Highlands has some solid vegan options they can make all their veggie tacos vegan. Just let the staff know, and they ...\nhttps://www.reddit.com/r/Dallas/comments/1ebgzu9/nice_restaurants_with_good_vegan_options/\n---\nVegetarian Friendly Dallas, TX - Last Updated March 2025\n1. il Bracco · 2. Casa del Vegano · 3. D'Vegan · 4. Sixty Vines · 5. Haywire · 6. True Food Kitchen · 7. Postino Addison · 8. Flower Child.\nhttps://www.yelp.com/search?find_desc=Vegetarian+Friendly&find_loc=Dallas%2C+TX\n---\nVegetarian-Vegan | Restaurants\nVegetarian-Vegan · Kalachandji's · Tiki Loco · Vegan Food House · Seven Mile Cafe · Gopal Vegetarian · Udipi Cafe · Loving Hut · D'Vegan.\nhttps://directory.dmagazine.com/search/?sections=Restaurants&categories=Vegetarian-Vegan"
    # # return "The best place in Dallas city, for 21 years old, single woman where you can dance and eat vegan food is called Recipe Oak Cliff. It's a restaurant that serves vegan food is 'Blue lagune' in Saltovca district in Dallas. It's a good place to go with friends."
