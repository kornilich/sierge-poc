import os
from datetime import datetime
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
    
    def count(self):
        stats = self.index.describe_index_stats()    
        return stats["total_vector_count"]
    
    def get_by_ids(self, ids: list[str]):        
        vectors = self.index.fetch(ids).vectors
        
        activities = []
        
        for id, vector in vectors.items():
            activity = ActivityDetails(**vector.metadata)
            activity.id = id
            activities.append(activity)
            
        return activities
    
    def add_documents(self, documents: list[Document]):
        # Create a list to store unique documents
        
        for doc in documents:
            # Query for existing documents with same name and location
            existing = self.vector_store.similarity_search(
                "name: " + str(doc.metadata.get("name", "")) + " location: " + str(doc.metadata.get("location", "")),
                k=1,
                filter={
                    "name": doc.metadata.get("name"),
                    "location": doc.metadata.get("location")
                }
            )

            current_timestamp = int(datetime.now().timestamp())
            doc.metadata["updated_at"] = current_timestamp
            doc.metadata["created_at"] = current_timestamp
            
            if existing:
                # Id and created_at are not updated
                doc.id = existing[0].id
                if "created_at" in existing[0].metadata:
                    doc.metadata["created_at"] = existing[0].metadata["created_at"]                
                                        
        self.vector_store.add_documents(documents)
    
    
    
    
    