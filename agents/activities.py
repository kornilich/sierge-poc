from typing import Optional, List, Literal
from pydantic import BaseModel, Field

CategoryEnum = Literal["Live Entertainment", "Movies & Film", "Museums & Exhibits", "Community Events & Activities",
                       "Sports & Recreation", "Health & Wellness", "Learning & Skill-Building", "Shopping", "Food & Drink Experiences", "Self-Guided Activities & Destinations", "Other"]


class ActivityDetails(BaseModel):
    """Represents detailed information about an activity or event.
If certain fields lack sufficient data or are unavailable, they will be assigned the value `N/A`    
    """
# Internal fields
    id: Optional[str] = Field(
        default=None, description="For internal use only. Unique identifier for the activity.")
    created_at: Optional[int] = Field(
        default=None, description="For internal use only. Timestamp of when the activity was created.")
    updated_at: Optional[int] = Field(
        default=None, description="For internal use only. Timestamp of when the activity was updated.")
    full_address: Optional[str] = Field(
        default=None, description="For internal use only.")
    coordinates: Optional[dict] = Field(
        default=None, description="For internal use only.")
    similarity_score: Optional[float] = Field(
        default=None, description="For internal use only. Similarity score of the activity to the query.")

    data_source: Optional[str] = Field(
        default="Model", description="Source of the information. Can be 'Model' or tool name.")
    category: Optional[str] = Field(default="Other")
    name: Optional[str] = Field(
        default=None, description="Name/Title of the activity (e.g., Event Name, Venue Name, Destination Name).")
    description: Optional[str] = Field(default=None,
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
    reason: Optional[str] = Field(
        default="No reason provided", description="Reason for the recommendations and tools selection.")
