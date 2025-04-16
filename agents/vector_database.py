import os
from datetime import datetime
import uuid
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_core.documents import Document

from agents.activities import ActivityDetails

class VectorDatabase:
    def __init__(self):
        client = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        self.index = client.Index(os.environ["PINECONE_INDEX"])

        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.environ["OPENAI_API_KEY"]
        )
        
        self.vector_store = PineconeVectorStore(index=self.index, embedding=embeddings)
    
    def stats(self):
        stats = self.index.describe_index_stats()
        return stats.to_dict()
        
    def similarity_search(self, query: str, k: int = 4, namespace: str = ""):
        results = self.vector_store.similarity_search(query, k=k, namespace=namespace)
        
        activities = []
        for doc in results:
            activity = ActivityDetails(**doc.metadata)
            activity.id = doc.id
            activities.append(activity)
        
        return activities
    
    
    def get_by_ids(self, ids: list[str], namespace: str):        
        vectors = self.index.fetch(ids, namespace=namespace).vectors
        
        activities = []
        
        for id, vector in vectors.items():            
            activity = ActivityDetails(**eval(vector.metadata["text"]))
            activity.id = id
            activities.append(activity)
            
        return activities
    
    def add_documents(self, activities: list[ActivityDetails], namespace: str):
        # Create a list to store unique documents 
        
        for activity in activities:
            # TODO: Make advanced duplicates processing
            # Query for existing documents with same name and location
            existing_rec = self.vector_store.similarity_search(
                "name: " + activity.name + " location: " + activity.location,
                k=1,
                filter={
                    "name": activity.name,
                }
            )

            current_timestamp = int(datetime.now().timestamp())
            activity.updated_at = current_timestamp
            activity.created_at = current_timestamp
            
            if existing_rec:
                # Id and created_at are not updated
                activity.id = existing_rec[0].id
                if "created_at" in existing_rec[0].metadata:
                    activity.created_at = existing_rec[0].metadata["created_at"]                
            else:
                if not activity.id:
                    activity.id = str(uuid.uuid4())
                        
        documents = []

        for activity in activities:
            document = Document(
                id=activity.id,
                page_content=str(activity.model_dump()),
                metadata={
                    "name": activity.name,
                    "location": activity.location,
                    "category": activity.category,
                    "data_source": activity.data_source,
                    "created_at": activity.created_at,
                    "updated_at": activity.updated_at,
                }
            )
            documents.append(document)
                                        
            self.vector_store.add_documents(documents, namespace=namespace)
            
    def delete_by_ids(self, ids: list[str]):
        self.index.delete(ids)
    
    
    
    
    
    