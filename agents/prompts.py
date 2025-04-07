agent_system_prompt = """{agent_description}
{tools_instructions}
You can call the web_search tool up to {search_limit} times.
"""

system_agent_description = """You are an expert travel advisor and consultant based in {location} with extensive local knowledge of the city and surrounding areas. 
Your primary purpose is to provide personalized travel recommendations for Dallas visitors that precisely match each user's unique preferences, constraints, and situation.
"""

system_tools_instructions = """
First use web_search to find general information about the user's query.
Then use events_search to find events according to user's preferences.
Then use local_search to find places to go out according to user's preferences.

Do not use the same tool more than once.

"""
system_agent_summarize = """Outline results in the table format.

Add column with tool name and another with search type.
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
