import os
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_core.documents import Document

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
    
    def add_documents(self, documents: list[Document]):
        self.vector_store.add_documents(documents)
    
    
    