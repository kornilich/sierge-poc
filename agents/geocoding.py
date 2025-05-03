import logging
import os
import googlemaps
import requests

#TODO: Would be good to add Location bias

def get_location_from_string(location_str):
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

            return {
                "formatted_address": formatted_address,
                "latitude": location['lat'],
                "longitude": location['lng']
            }
        else:
            return None
    except Exception as e:
        logging.error(
            f"Error fetching location data (get_location_from_string): {str(e)}")
        return None


def get_place_address(searchText, bias_lat, bias_lon, radius=20000):
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
                        "latitude": bias_lat,
                        "longitude": bias_lon
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
            return {
                "name": place['displayName']['text'],
                "formatted_address": place['formattedAddress'], 
                "latitude": place['location']['latitude'],
                "longitude": place['location']['longitude']
            }
        else:
            return None
    except Exception as e:
        logging.error(
            f"Error fetching address data (get_place_address): {str(e)}")
        return None

