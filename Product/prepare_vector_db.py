import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from typing import List
import numpy as np

# Khai báo biến
pdf_data_path = "data"
vector_db_path = "vectorstores/db_faiss"
bge_m3_model_path = "models/bge-m3"  # Đường dẫn lưu mô hình BGE-M3
max_length = 512  # Giới hạn độ dài token của BGE-M3

# Tạo lớp embedding tùy chỉnh cho SentenceTransformer
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Tạo embedding cho danh sách các tài liệu."""
        embeddings = self.model.encode(
            texts, convert_to_tensor=False, show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Tạo embedding cho một câu hỏi."""
        embedding = self.model.encode([text], convert_to_tensor=False, show_progress_bar=False).tolist()[0]
        return embedding

def create_db_from_files():
    # Khai báo loader để quét toàn bộ thư mục data
    loader = DirectoryLoader(pdf_data_path, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()

    # Chia tài liệu thành các đoạn với các tham số được tối ưu
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=True
    )
    chunks = text_splitter.split_documents(documents)

    # In ra các đoạn để kiểm tra
    print("Các đoạn văn bản sau khi chia:")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {chunk.page_content[:100]}...")

    # Kiểm tra và tải/lưu mô hình BGE-M3
    if not os.path.exists(bge_m3_model_path):
        print(f"Thư mục {bge_m3_model_path} không tồn tại. Đang tải mô hình BGE-M3...")
        embedding_model = SentenceTransformer('BAAI/bge-m3')  # Tải từ Hugging Face
        print(f"Đang lưu mô hình vào {bge_m3_model_path}...")
        embedding_model.save(bge_m3_model_path)  # Lưu mô hình vào thư mục models
        print(f"Đã lưu mô hình BGE-M3 vào {bge_m3_model_path}.")
    else:
        print(f"Thư mục {bge_m3_model_path} đã tồn tại. Đang tải mô hình BGE-M3 từ local...")
        embedding_model = SentenceTransformer(bge_m3_model_path)  # Tải từ local
        print(f"Tải xong mô hình BGE-M3 từ {bge_m3_model_path}.")

    # Tạo đối tượng embedding tùy chỉnh
    custom_embeddings = SentenceTransformerEmbeddings(bge_m3_model_path)

    # Tạo FAISS vector store
    print("Đang tạo FAISS vector store...")
    db = FAISS.from_documents(chunks, custom_embeddings)
    db.save_local(vector_db_path)
    print("Đã tạo và lưu FAISS vector store thành công!")
    return db

# Gọi hàm
if __name__ == "__main__":
    # Đảm bảo thư mục models tồn tại
    if not os.path.exists("models"):
        os.makedirs("models")
        print("Đã tạo thư mục models.")
    create_db_from_files()