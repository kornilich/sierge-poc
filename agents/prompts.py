# Agent prompts

system_agent_description = """You are an expert travel advisor and consultant based in Dallas, USA with extensive local knowledge of the city and surrounding areas. 
Your primary purpose is to provide personalized travel recommendations for Dallas visitors that precisely match each user's unique preferences, constraints, and situation.
"""

system_tools_instructions = """Use web_search tool find places of each kind. 

For each place try to fill all fields of ActivityDetails model. If you not sure about some field do not fill it.

When you fill category field, use one of the following values: 
"Live Entertainment", "Movies & Film", "Museums & Exhibits", "Community Events & Activities", 
"Sports & Recreation", "Health & Wellness", "Learning & Skill-Building", "Shopping", "Food & Drink Experiences", "Self-Guided Activities & Destinations" 
or "Other" if it doesn\'t fit any of the above.

Do not fill rank field.
                                    
Return all responses as valid JSON array with name "activities".                                    
"""
system_agent_summarize = """Summarize the results of the web search.

Select only 3 activities from the list which fit best to user's preferences.

Use all input data to fill in activity details.
Additionaly, set rank for each activity from 1 to 5. Where 1 is the best and 5 is the worst fit to user's preferences.

Put your the reason why you think this is best choice of activities in the reason field of ActivitiesList.

Return all responses as valid JSON array.                                    
"""

# Preferences defaults
contextual_preferences_default = """I often go on outings with my husband and friends. 
We prefer casual, local locations without tourists and pet-friendly. 
I prefer places that have live music. We prefer alcohol over beer-only restaurants."""

fixed_preferences_default = """I’m in the 30-40 age range and currently married. My dietary restrictions are to follow a Mediterranean diet, and I have a capsaicin and saffron allergy. My activity level is lightly active, and I enjoy outdoor activities like sailing or other water sports, but prefer to avoid hiking or dirt. 
For recommendations, I consider myself somewhat familiar, so I’d prefer a mix of mainstream and hidden gems.
My preferred atmosphere is relaxed and intimate, but I also enjoy group gatherings in certain situations. My core interests include performing arts, art galleries and museums, dance, and yoga. I consider myself introverted, and I generally prefer quiet settings.
My travel style is mid-range, and I generally prefer short trips to explore new cities over extended vacations. For entertainment, I enjoy indie and foreign films films, and my favorite music genres are rock, alternative, and folk. In terms of cuisine, I love Mediterranean, French, and Italian food, but I prefer to avoid Indian cuisine.
"""
