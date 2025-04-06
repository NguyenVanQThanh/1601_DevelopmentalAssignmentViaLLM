from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import GPT4AllEmbeddings

# Khai bao bien
pdf_data_path = "data"
vector_db_path = "vectorstores/db_faiss"

def create_db_from_files():
    # Khai bao loader de quet toan bo thu muc data
    loader = DirectoryLoader(pdf_data_path, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()

    # Chia tài liệu thành các đoạn
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,  
        chunk_overlap=50,  
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],  
        keep_separator=True  
    )
    chunks = text_splitter.split_documents(documents)

    # In ra các đoạn để kiểm tra
    print("Các đoạn văn bản sau khi chia:")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {chunk.page_content[:100]}...") 

    # Embeding
    embedding_model = GPT4AllEmbeddings(model_file="models/all-MiniLM-L6-v2-f16.gguf")
    db = FAISS.from_documents(chunks, embedding_model)
    db.save_local(vector_db_path)
    print("Đã tạo và lưu FAISS vector store thành công!")
    return db

# Gọi hàm
create_db_from_files()