from typing import TypedDict, Annotated
import operator

import os
from serpapi import GoogleSearch

from langchain_core.agents import AgentAction
from langchain_core.tools import tool
from langchain_core.agents import AgentAction
from langchain_core.messages import BaseMessage

serpapi_params = {
    "engine": "google",
    "api_key": os.getenv("SERPAPI_KEY")
}


class AgentState(TypedDict):
    input: str
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]


search = GoogleSearch({
    **serpapi_params,
    "q": "Dallas",
    "num": 3
})

# results = search.get_dict()["organic_results"]

# contexts = "\n---\n".join(
#     ["\n".join([x["title"], x["snippet"], x["link"]]) for x in results]
# )


@tool("web_search")
def web_search(query: str):
    """Finds general knowledge information using Google search. Can also be used
    to augment more 'general' knowledge to a previous specialist query."""
    # search = GoogleSearch({
    #     **serpapi_params,
    #     "q": query,
    #     "num": 5
    # })
    # results = search.get_dict()["organic_results"]
    # contexts = "\n---\n".join(
    #     ["\n".join([x["title"], x["snippet"], x["link"]]) for x in results]
    # )
    # return contexts
    return "The Best Vegan Restaurants Around Dallas\nThe Best Vegan Restaurants Around Dallas · Recipe Oak Cliff · Spiral Diner & Bakery · Maiden · Casa Del Vegano · Vegan Food House · El Palote ...\nhttps://dallas.eater.com/maps/dallas-best-vegan-restaurants\n---\nThe Best Vegan Restaurants in Dallas: Our Picks\nVegan Spots in Dallas · Casa Del Vegano · Kalachandjis · HG Sply Co. · HopeBoy's Kitchen · Recipe Oak Cliff · Vegan Food House · Vegan Food House · Related ...\nhttps://www.visitdallas.com/blog/vegan-spots-in-dallas/\n---\nNice restaurants with good vegan options? : r/Dallas\nResident Taqueria in Lake Highlands has some solid vegan options they can make all their veggie tacos vegan. Just let the staff know, and they ...\nhttps://www.reddit.com/r/Dallas/comments/1ebgzu9/nice_restaurants_with_good_vegan_options/\n---\nVegetarian Friendly Dallas, TX - Last Updated March 2025\n1. il Bracco · 2. Casa del Vegano · 3. D'Vegan · 4. Sixty Vines · 5. Haywire · 6. True Food Kitchen · 7. Postino Addison · 8. Flower Child.\nhttps://www.yelp.com/search?find_desc=Vegetarian+Friendly&find_loc=Dallas%2C+TX\n---\nVegetarian-Vegan | Restaurants\nVegetarian-Vegan · Kalachandji's · Tiki Loco · Vegan Food House · Seven Mile Cafe · Gopal Vegetarian · Udipi Cafe · Loving Hut · D'Vegan.\nhttps://directory.dmagazine.com/search/?sections=Restaurants&categories=Vegetarian-Vegan"


@tool("final_answer")
def final_answer(
    introduction: str,
    research_steps: str,
    main_body: str,
    conclusion: str,
    sources: str
):
    """Returns a natural language response to the user in the form of a research
    report. There are several sections to this report, those are:
    - `introduction`: a short paragraph introducing the user's question and the
    topic we are researching.
    - `research_steps`: a few bullet points explaining the steps that were taken
    to research your report.
    - `main_body`: this is where the bulk of high quality and concise
    information that answers the user's question belongs. It is 3-4 paragraphs
    long in length.
    - `conclusion`: this is a short single paragraph conclusion providing a
    concise but sophisticated view on what was found.
    - `sources`: a bulletpoint list provided detailed sources for all information
    referenced during the research process
    """
    if type(research_steps) is list:
        research_steps = "\n".join([f"- {r}" for r in research_steps])
    if type(sources) is list:
        sources = "\n".join([f"- {s}" for s in sources])
    return ""
