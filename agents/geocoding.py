from datetime import datetime
import logging
import os
import googlemaps
import pytz
import requests

from pydantic import BaseModel
from typing import Optional

class PlaceAddressDetails(BaseModel):
    name: Optional[str] = None
    formatted_address: str
    latitude: float 
    longitude: float


def get_validated_address(location_str, base_location) -> Optional[PlaceAddressDetails]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    try:
        url = f"https://addressvalidation.googleapis.com/v1:validateAddress?key={api_key}"

        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "address": {
                "regionCode": "US",
                "locality": base_location,
                "addressLines": [location_str]
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes

        result = response.json()["result"]
        
        if result["verdict"]["validationGranularity"] in ["PREMISE_PROXIMITY", "PREMISE", "SUB_PREMISE"]:
            place = PlaceAddressDetails(
                formatted_address=result["address"]["formattedAddress"],
                latitude=result["geocode"]["location"]["latitude"],
                longitude=result["geocode"]["location"]["longitude"]
            )
            return place
        else:
            return None        
    except Exception as e:
        logging.error(
            f"Error fetching address data (get_validated_address): {str(e)}")
        
        return None

def get_weather_data(latitude, longitude, days=3):
    """Get current weather data from Google Weather API using coordinates."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    try:
        url = f"https://weather.googleapis.com/v1/forecast/days:lookup?key={api_key}&location.latitude={latitude}&location.longitude={longitude}&days={days}&unitsSystem=IMPERIAL"

        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        weather_data = response.json()

        return weather_data
    except Exception as e:
        logging.error(
            f"Error fetching weather data (get_weather_data): {str(e)}")
        return { "weather": "Forecast is not available due to error"}

def get_timezone_from_coordinates(latitude, longitude):
    gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))
    timezone_result = gmaps.timezone(
        location=(latitude, longitude)
    )
    
    if timezone_result.get("status") == "OK":
        timezone_id = timezone_result["timeZoneId"]
    else:
        timezone_id = "America/Chicago"
    
    return timezone_id

#TODO: Would be good to add Location/Region bias
def get_location_from_string(location_str) -> Optional[PlaceAddressDetails]:
    """Get formatted address and coordinates from Google Maps API using location description like zip code, district, full address etc."""
    if not location_str:
        return None

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    try:
        gmaps = googlemaps.Client(key=api_key)
        result = gmaps.geocode(location_str)

        if result:
            location = result[0]['geometry']['location']
            formatted_address = result[0]['formatted_address']

            return PlaceAddressDetails(
                formatted_address=formatted_address,
                latitude=location['lat'],
                longitude=location['lng']
            )
        else:
            return None
    except Exception as e:
        logging.error(
            f"Error fetching location data (get_location_from_string): {str(e)}")
        return None

def get_place_address(searchText, bias_latitude, bias_longitude, radius=20000) -> Optional[PlaceAddressDetails]:
    """Get formatted address from Google Maps API using coordinates."""
    # Default radius is set to 20km (Dallas) to be able to find all places in the city
    # Maybe it even make sense to diameter or bigger
    #
    # Searches use only coords, but no radius, so we don't know how to limit radius param here
    #
 
    if not searchText:
        return None

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    try:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
        }
        payload = {
            "textQuery": searchText,
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": bias_latitude,
                        "longitude": bias_longitude
                    },
                    "radius": radius
                }
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if result and 'places' in result:
            place = result['places'][0]
            return PlaceAddressDetails(
                name=place['displayName']['text'],
                formatted_address=place['formattedAddress'],
                latitude=place['location']['latitude'],
                longitude=place['location']['longitude']
            )
        else:
            return None
    except Exception as e:
        logging.error(
            f"Error fetching address data (get_place_address): {str(e)}")
        return None

def get_datetime_info(latitude, longitude):
    datetime_now_utc = datetime.now(pytz.timezone("UTC"))
    tz = get_timezone_from_coordinates(latitude, longitude)

    datetime_now_local = datetime_now_utc.astimezone(pytz.timezone(tz))
    datetime_now_info = f"Local time: {datetime_now_local.strftime('%m/%d/%Y %I:%M %p %Z')} {tz}\n\n"
    datetime_now_info += f"UTC time: {datetime_now_utc.strftime('%Y-%m-%d %H:%M')}"

    return datetime_now_info
