from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, TypedDict, Annotated, Dict, Literal
from pydantic import ValidationError
from pydantic import create_model


class ActivityDetails(BaseModel):
    """Represents detailed information about an activity or event.
If certain fields lack sufficient data or are unavailable, they will be assigned the value `N/A`    
    """

    name: Optional[str] = Field(
        default=None, description="Name/Title of the activity (e.g., Event Name, Venue Name, Destination Name).")
    description: Optional[str] = Field(default=None,
                                       description="Brief overview of what the activity/event is about.")


class ActivitiesListByCategory(BaseModel):
    """Holds a collection of activity details representing recommendations by category in activities property."""
    activities: Dict[str, List[ActivityDetails]] = Field(
        ...,
        description="Dictionary where key is a catagory and value is ActivityDetails",
        min_items=0
    )    


activities_data = {
  "restaurants": [
    {
      "name": "Café Izmir",
      "cuisine": "Mediterranean",
      "atmosphere": "Relaxed and intimate",
      "features": "Pet-friendly, live music, casual local vibe",
      "location": "Lower Greenville"
    },
    {
      "name": "Bistro 31",
      "cuisine": "French",
      "atmosphere": "Intimate and upscale casual",
      "features": "Pet-friendly patio, wine selection, local art",
      "location": "Highland Park Village"
    },
  ],
}


activity = {
   "name": "Café Izmir",
   "description": "Pet-friendly, live music, casual local vibe",
}   
 

try:
    validated_activities = ActivitiesListByCategory(
activities=activities_data)

    print(validated_activities.model_dump())
except ValidationError as e:
    print("Validation Error:", e)
