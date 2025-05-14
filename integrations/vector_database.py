import logging
import os
from datetime import datetime
import uuid
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import Filter, FieldCondition
from pyuploadcare import Uploadcare

from agents.activities import ActivityDetails

class VectorDatabase:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        
        self.uploadcare = Uploadcare(
            public_key=os.environ["UPLOADCARE_PUBLIC_KEY"],
            secret_key=os.environ["UPLOADCARE_SECRET_KEY"]
        )
        
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
            # Query for existing documents with same name and full_address
            # TODO: Consider using local embeddings like FastEmbed instead of OpenAI API calls
            
            # Generate ID based on name and full_address
            activity_uuid = str(uuid.uuid5(
                uuid.NAMESPACE_URL, (activity.name + activity.full_address).lower()))
            # TODO: Can be optimized by calling once before the loop
            existing_activities = self.get_by_ids([activity_uuid])
            
            current_timestamp = int(datetime.now().timestamp())
            activity.updated_at = current_timestamp
            activity.created_at = current_timestamp

            if existing_activities:
                existing_activity = existing_activities[0]
                # Id and created_at should remain the same
                activity.id = existing_activity.id
                activity.created_at = existing_activity.created_at                
                
                # Copy over any non-null values from existing activity
                for field in activity.model_dump().keys():
                    if getattr(activity, field) is None and hasattr(existing_activity, field):
                        setattr(activity, field, getattr(
                            existing_activity, field))
            else:
                activity.id = activity_uuid
                
            if activity.image_url:
                try:
                    ucare_file = self.uploadcare.upload(activity.image_url, store=True, metadata={
                                                    "activity_id": f"{activity.id}"})
                    activity.image_url = ucare_file.cdn_url
                except Exception as e:
                    logging.error(f"Error uploading image: {e}")
                    activity.image_url = None

        points = []
        for activity in activities:
            activity_dump = activity.model_dump()
            points.append(
                models.PointStruct(
                    id=str(activity.id),
                    vector=self.embeddings.embed_query(str(activity_dump)),
                    payload=activity_dump
                )
            )
        
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
            ids=[str(id) for id in cleared_ids]
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

    
    
    
    