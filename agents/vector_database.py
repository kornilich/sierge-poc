import logging
import os
from datetime import datetime
import uuid
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import Filter, FieldCondition, MatchValue

from agents.activities import ActivityDetails

class VectorDatabase:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        
        self.client = QdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        
        # Create collection if it doesn't exist
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=1536,  # OpenAI embedding dimension for text-embedding-3-small
                    distance=models.Distance.COSINE)
            )
            
        # Create indecies if not exist
        collection = self.client.get_collection(self.collection_name)
        existing_indices = collection.payload_schema
        if "name" not in existing_indices:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="name",
                field_schema="keyword",
            )
        
        if "coordinates" not in existing_indices:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="coordinates",
                field_schema="geo",
            )
                
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.environ["OPENAI_API_KEY"]
        )
    
    def safe_point_to_activity(self, point: models.PointStruct) -> ActivityDetails:
        activity = ActivityDetails()
        activity.id = point.id
        for key, value in point.payload.items():
            try:
                setattr(activity, key, value)
            except AttributeError:
                logging.warning(f"Skipping attribute {key} for activity {point.id} (safe_point_to_activity)")
                
        return activity
    
    def save_activities(self, activities: list[ActivityDetails]):
        for activity in activities:
            # Query for existing documents with same name and location
            # TODO: Consider using local embeddings like FastEmbed instead of OpenAI API calls
            existing_point = self.client.search(
                collection_name=self.collection_name,
                query_vector=self.embeddings.embed_query(
                    "name: " + activity.name + " location: " + activity.location),
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="name",
                            match=MatchValue(value=activity.name)
                        )
                    ]
                ),
                limit=1,
            )
            
            current_timestamp = int(datetime.now().timestamp())
            activity.updated_at = current_timestamp
            activity.created_at = current_timestamp

            if existing_point:
                # Id and created_at should remain the same
                activity.id = existing_point[0].id
                if "created_at" in existing_point[0].payload:
                    activity.created_at = existing_point[0].payload["created_at"]
            else:
                if not activity.id:
                    activity.id = str(uuid.uuid4())

        points = [
            models.PointStruct(
                id=activity.id,
                vector=self.embeddings.embed_query(str(activity.model_dump())),
                payload={
                    "name": activity.name,
                    "location": activity.location,
                    "full_address": activity.full_address,
                    "coordinates": activity.coordinates,
                    "category": activity.category,
                    "data_source": activity.data_source,
                    "created_at": activity.created_at,
                    "updated_at": activity.updated_at,
                }
            )
            for activity in activities
        ]
        
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            logging.error(f"Error upserting activities: {e}")
            raise e
        
    
    def get_metrics(self):
        collection = self.client.get_collection(self.collection_name)
        return collection.model_dump()
        
    def similarity_search(self, query: str, limit: int = 5, geo_filter: dict = None):
        if geo_filter is None:
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=self.embeddings.embed_query(query),
                limit=limit,
            )
        else:
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=self.embeddings.embed_query(query),
                limit=limit,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="coordinates",
                            geo_radius=models.GeoRadius(
                                center=models.GeoPoint(
                                    lat=geo_filter["lat"],
                                    lon=geo_filter["lon"],
                                ),
                                radius=geo_filter["radius"],
                            ),
                        )
                    ]
                ),
            )
        
        activities = []
        for point in points:
            activity = self.safe_point_to_activity(point)
            activity.similarity_score = point.score
            activities.append(activity)

        return activities
    
    def get_by_ids(self, ids: list[str]):
        # HACK: Remove "Blank" from ids. The only reason it's there is to make the config work
        cleared_ids = [id for id in ids if id != "Blank"]
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=cleared_ids
        )
        
        activities = []
        for point in points:
            activity = self.safe_point_to_activity(point)
            activities.append(activity)
            
        return activities
            
    def delete_by_ids(self, ids: list[str]):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=ids
            )
        )
    
    def scroll_collection(self, offset: str = None, limit: int = 10):
        results = self.client.scroll(
            collection_name=self.collection_name,
            offset=offset,
            limit=limit
        )
        
        activities = []
        for point in results[0]:
            activity = self.safe_point_to_activity(point)
            activities.append(activity)

        return activities

    
    
    
    