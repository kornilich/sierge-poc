system_common_prompt = """You are an expert travel advisor and consultant based in {location} with extensive local knowledge of the city and surrounding areas. 
Your primary purpose is to provide personalized travel recommendations for {location} visitors that precisely match each user's unique preferences, constraints, and situation.
"""

system_data_collection_prompt_template = """{commont_prompt}
{data_sources_prompt}
"""

data_sources_prompt = """Core Objective: 
Generate comprehensive activity lists while respecting operational constraints.
    
- Provide chain of thoughts
- Do not show detailed recommendations or summary

Operational Constraints:
- Number of results should be close to {number_of_results} but not exceed it
- Save ALL results even if they are not relevant to user's preferences
- If data_source field is not defined, set "Model knowledge" value to it
"""

system_agent_summarize = """Return a single recommended plan (schedule or itinerary), including time-based sequencing, location feasibility, and activity diversity. Return results in the form of a table with name, rank, description, address, rating, and link to the place. Rank is a number from 1 to 5. Where 1 is the best and 5 is the worst fit to the user's preferences. if you don't have any information about the place, just put "n/a" in the table.
Avoid suggesting experiences that lack date/time/location availability unless clearly flagged (e.g., with an asterisk "*").
Prioritize feasibility based on logistics, weather, timing, and budget over user interests if there is a conflict.
Provide brief explanations for why each item was chosen or excluded (e.g., noise level, allergens, availability).
Apply user preferences and constraints as soft filters, allowing flexibility while honoring the intent of the request.
Use stored user fixed preferences and contextual preferences to interpret relevance, tone, and detail level.
"""

# system_agent_summarize = """Summarize the results of the tools.

# Use all input data to fill in activity details.
# Additionaly, set rank for each activity from 1 to 5. Where 1 is the best and 5 is the worst fit to user's preferences.
# """


# Preferences defaults
contextual_preferences_default = """I often go on outings with my husband and friends. 
We prefer casual, local locations without tourists and pet-friendly. 
I prefer places that have live music. We prefer alcohol over beer-only restaurants."""

fixed_preferences_default = """I’m in the 30-40 age range and currently married. My dietary restrictions are to follow a Mediterranean diet, and I have a capsaicin and saffron allergy. My activity level is lightly active, and I enjoy outdoor activities like sailing or other water sports, but prefer to avoid hiking or dirt. 
For recommendations, I consider myself somewhat familiar, so I’d prefer a mix of mainstream and hidden gems.
My preferred atmosphere is relaxed and intimate, but I also enjoy group gatherings in certain situations. My core interests include performing arts, art galleries and museums, dance, and yoga. I consider myself introverted, and I generally prefer quiet settings.
My travel style is mid-range, and I generally prefer short trips to explore new cities over extended vacations. For entertainment, I enjoy indie and foreign films films, and my favorite music genres are rock, alternative, and folk. In terms of cuisine, I love Mediterranean, French, and Italian food, but I prefer to avoid Indian cuisine.
"""
