import pytest
from agents.tools import add_full_address
from agents.activities import ActivityDetails
from typing import Optional
from pydantic import Field

# Dallas, TX
location_bias_lat = 32.7767
location_bias_lon = -96.7970

class ActivityDetailsAssert(ActivityDetails):
    assert_full_address: Optional[str] = Field(default=None)
    assert_coordinates: Optional[dict] = Field(default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assert_full_address = kwargs.get("assert_full_address")
        self.assert_coordinates = kwargs.get("assert_coordinates")

@pytest.fixture
def activities_with_wrong_location():
    return [
        ActivityDetailsAssert(
            id="1",
            description="Name: Correct | Location: Missing",
            name="Dallas Farmers Market Produce Shed",
            location="",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="2",
            description="Name: Non-existent | Location: Missing",
            name="asdfh;kjcvxzm",
            location="",
            assert_full_address=None,
            assert_coordinates=None,
        ),
        ActivityDetailsAssert(
            id="3",
            description="Name: Correct | Location: Incomplete",
            name="Dallas Farmers Market Produce Shed",
            location="Dallas, TX",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="4",
            description="Name: Correct | Location: Wrong - Address in priority (worst case)",
            name="Dallas Farmers Market Produce Shed",
            location="1224 S Cesar Chavez Blvd",
            assert_full_address="1224 South Cesar Chavez Boulevard, Dallas, TX 75201-6012, USA",
            assert_coordinates={'lat': 32.777044, 'lon': -96.7886267},
        ),
        ActivityDetailsAssert(
            id="5",
            description="Name: Correct | Location: Non-existent",
            name="Dallas Farmers Market Produce Shed",
            location="asdfh;kjcvxzm",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
    ]

@pytest.fixture
def activities_with_correct_location():
    return [
        ActivityDetailsAssert(
            id="6",
            description="Name: Correct | Location: Correct",
            name="Dallas Farmers Market Produce Shed",
            location="123 Taylor St",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="7",
            description="Name: Incomplete | Location: Correct",
            name="Farmers Market",
            location="123 Taylor St",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="8",
            description="Name: Variant | Location: Correct",
            name="The Shed at Dallas Farmers Market",
            location="123 Taylor St",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="9",
            description="Name: Ads | Location: Correct",
            name="Find Vendors",
            location="123 Taylor St",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="10",
            description="Name: Another place | Location: Correct",
            name="Footsal",
            location="123 Taylor St",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="11",
            description="Name: Non-existent | Location: Correct - Got more generic coords, probable not entrance just a building",
            name="Non-existent",
            location="123 Taylor St",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="12",
            description="Name: Not in places | Location: Correct - somewhere in residential area",
            name="Some gym",
            location="500-598 Vermont Ave",
            assert_full_address="500-598 Vermont Avenue, Dallas, TX 75216, USA",
            assert_coordinates={'lat': 32.7276954, 'lon': -96.8168467},
        )
    ]

# Collected from other activties lists
@pytest.fixture
def activities_hot_cases():
    return [
        ActivityDetailsAssert(
            id="3",
            description="Name: Correct | Location: Incomplete",
            name="Dallas Farmers Market Produce Shed",
            location="Dallas, TX",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="5",
            description="Name: Correct | Location: Non-existent",
            name="Dallas Farmers Market Produce Shed",
            location="asdfh;kjcvxzm",
            assert_full_address="123 Taylor Street, Dallas, TX 75201, USA",
            assert_coordinates={'lat': 32.777722, 'lon': -96.7888126},
        ),
        ActivityDetailsAssert(
            id="12",
            description="Name: Not in places | Location: Correct - somewhere in residential area",
            name="Some gym",
            location="500-598 Vermont Ave",
            assert_full_address="500-598 Vermont Avenue, Dallas, TX 75216, USA",
            assert_coordinates={'lat': 32.7276954, 'lon': -96.8168467},
        ),
        ActivityDetailsAssert(
            id="2",
            description="Name: Non-existent | Location: Missing",
            name="asdfh;kjcvxzm",
            location="",
            assert_full_address=None,
            assert_coordinates=None,
        ),
    ]

def test_add_full_address_hot_cases(activities_hot_cases):
    """Test add_full_address with most important cases
       Real API calls are made to verify the address and coordinates.
    """
    test_add_full_address_names(activities_hot_cases)

def test_add_full_address_locations(activities_with_wrong_location):
    """Test add_full_address with different location variations to verify address matching behavior.
       Real API calls are made to verify the address and coordinates.
    """
    test_add_full_address_names(activities_with_wrong_location)

def test_add_full_address_names(activities_with_correct_location):
    """Test add_full_address with different name variations to verify address matching behavior.
       Real API calls are made to verify the address and coordinates.
    """
    activities = activities_with_correct_location
    
    add_full_address(activities, "Dallas, Texas, United States",
                     location_bias_lat, location_bias_lon)
    
    for activity in activities:
        assert activity.full_address == activity.assert_full_address, \
            f"Address mismatch for {activity.description}:\n" \
            f"Expected: {activity.assert_full_address}\n" \
            f"Got: {activity.full_address}"
        
        assert activity.coordinates == activity.assert_coordinates, \
            f"Coordinates mismatch for {activity.description}:\n" \
            f"Expected: {activity.assert_coordinates}\n" \
            f"Got: {activity.coordinates}"

