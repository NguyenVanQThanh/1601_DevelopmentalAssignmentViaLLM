import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from typing import List
from custom_embeddings import BGEM3Embeddings
import numpy as np

# Configuration
pdf_data_path = "data"
vector_db_path = "vectorstores/db_faiss"
bge_m3_model_path = "models/bge-m3"
chunk_size = 1000
chunk_overlap = 200

def validate_pdf_files():
    """Kiểm tra tính hợp lệ của file PDF"""
    if not os.path.exists(pdf_data_path):
        raise FileNotFoundError(f"Thư mục {pdf_data_path} không tồn tại")
    
    pdf_files = [f for f in os.listdir(pdf_data_path) if f.endswith('.pdf')]
    if not pdf_files:
        raise ValueError(f"Không tìm thấy file PDF nào trong {pdf_data_path}")
    return pdf_files

def load_and_split_documents():
    """Tải và chia nhỏ tài liệu"""
    try:
        loader = DirectoryLoader(pdf_data_path, glob="*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        return text_splitter.split_documents(documents)
    except Exception as e:
        raise RuntimeError(f"Lỗi khi tải hoặc chia tài liệu: {str(e)}")

def create_vector_store(chunks):
    """Tạo và lưu vector store"""
    try:
        # Tạo embeddings
        embeddings = BGEM3Embeddings(bge_m3_model_path)
        
        # Tạo FAISS vector store (không cần truyền metadatas)
        db = FAISS.from_documents(chunks, embeddings)
        
        # Kiểm tra tính toàn vẹn trước khi lưu
        if len(db.index_to_docstore_id) != len(chunks):
            raise ValueError("Số lượng vector không khớp với số lượng chunks")
            
        # Lưu vector store
        os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)
        db.save_local(vector_db_path)
        
        # Kiểm tra sau khi lưu
        if not os.path.exists(f"{vector_db_path}/index.faiss"):
            raise RuntimeError("Lưu vector store thất bại")
            
        return db
    except Exception as e:
        raise RuntimeError(f"Lỗi khi tạo vector store: {str(e)}")

def main():
    try:
        print("Đang kiểm tra file PDF...")
        pdf_files = validate_pdf_files()
        print(f"Tìm thấy {len(pdf_files)} file PDF hợp lệ")
        
        print("Đang tải và chia nhỏ tài liệu...")
        chunks = load_and_split_documents()
        print(f"Đã chia thành {len(chunks)} chunks")
        
        print("Đang tạo vector store...")
        db = create_vector_store(chunks)
        print(f"Đã tạo và lưu vector store tại {vector_db_path}")
        
        # Test thử
        test_query = "Nội dung chính của tài liệu là gì?"
        results = db.similarity_search(test_query, k=1)
        print(f"\nKết quả test với query '{test_query}':")
        print(f"Chunk đầu tiên: {results[0].page_content[:100]}...")
        print(f"Nguồn: {results[0].metadata.get('source', 'unknown')}")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        if os.path.exists(vector_db_path):
            import shutil
            shutil.rmtree(vector_db_path)
            print(f"Đã xóa vector store không hợp lệ tại {vector_db_path}")

if __name__ == "__main__":
    # Đảm bảo thư mục models tồn tại
    os.makedirs("models", exist_ok=True)
    main()