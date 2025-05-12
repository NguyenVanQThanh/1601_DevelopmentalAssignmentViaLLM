# custom_embeddings.py
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from typing import List

class BGEM3Embeddings(Embeddings):
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_tensor=False).tolist()
    
    def embed_query(self, text: str) -> List[float]:
        return self.model.encode(text, convert_to_tensor=False).tolist()