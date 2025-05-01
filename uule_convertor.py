# This is port of https://github.com/serpapi/uule_converter/blob/master/lib/serpapi-uule-converter.rb
import base64
import time
from typing import Dict, Optional

class UuleConverter:
    E7_FACTOR = 10_000_000

    @staticmethod
    def encode(
        latitude: float,
        longitude: float,
        radius: int = -1,
        role: int = 1,
        producer: int = 12,
        provenance: int = 0,
        timestamp: Optional[int] = None
    ) -> str:
        """Encode location data into a UULE string."""
        if timestamp is None:
            timestamp = int(time.time() * 1_000_000)
        
        lat_e7 = int(latitude * UuleConverter.E7_FACTOR)
        lon_e7 = int(longitude * UuleConverter.E7_FACTOR)

        uule_string = f"""role: {role}
producer: {producer}
provenance: {provenance}
timestamp: {timestamp}
latlng{{
    latitude_e7: {lat_e7}
    longitude_e7: {lon_e7}
}}
radius: {radius}"""

        return 'a+' + UuleConverter._urlsafe_encode64(uule_string)

    @staticmethod
    def decode(uule_encoded: str) -> Dict:
        """Decode a UULE string back into location data."""
        uule_string = UuleConverter._urlsafe_decode64(uule_encoded[2:])  # Remove the 'a+' prefix
        data = {}

        for line in uule_string.splitlines():
            if ':' in line:
                key, value = line.strip().split(':', 1)
                data[key.strip()] = value.strip()

        # Convert E7 coordinates back to decimal degrees
        if 'latitude_e7' in data and 'longitude_e7' in data:
            data['latitude'] = int(data['latitude_e7']) / UuleConverter.E7_FACTOR
            data['longitude'] = int(data['longitude_e7']) / UuleConverter.E7_FACTOR
            del data['latitude_e7']
            del data['longitude_e7']

        return data

    @staticmethod
    def _urlsafe_encode64(s: str) -> str:
        """URL-safe base64 encoding."""
        return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

    @staticmethod
    def _urlsafe_decode64(s: str) -> str:
        """URL-safe base64 decoding."""
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += '=' * padding
        return base64.urlsafe_b64decode(s.encode()).decode()

# No change has been observed by changing provenance and radius parameters
# I still added them there in case they matter in the future.
# Setting radius to `-1` and provenance to `0` works for now.
# Setting user to `1` means `USER_SPECIFIED_FOR_REQUEST`.
# Setting producer to `12`` means `LOGGED_IN_USER_SPECIFIED`.
# Changing the value for the user and producer is shifting precision of the search.
