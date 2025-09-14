#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_vector_db.py
Build a cosine-similarity FAISS vector store from Vietnamese PDFs
using the BGE-M3 sentence-embedding model.
"""

# ========= 1. STANDARD LIBRARY =========
import os
import traceback

# ========= 2. THIRD-PARTY LIBS =========
from typing import List
from transformers import AutoTokenizer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
import faiss
import numpy as np

# ========= 3. CUSTOM EMBEDDING =========
from custom_embeddings import BGEM3Embeddings

# ========= 4. GLOBAL CONFIG =========
pdf_data_path:   str = "data"
vector_db_path:  str = "vectorstores/db_faiss_final"
bge_m3_model_path: str = "models/bge-m3"
chunk_size:      int = 128
chunk_overlap:   int = 50
_tokenizer_bge_m3 = None    

# ========= 5. TOKENIZER =========
def get_bge_m3_tokenizer():
    """Lazy-load & cache BGE-M3 tokenizer."""
    global _tokenizer_bge_m3
    if _tokenizer_bge_m3 is None:
        try:
            _tokenizer_bge_m3 = AutoTokenizer.from_pretrained(bge_m3_model_path)
            print(f"Loaded tokenizer from {bge_m3_model_path}")
        except Exception:
            _tokenizer_bge_m3 = AutoTokenizer.from_pretrained("BAAI/bge-m3")
            print("Loaded tokenizer from Hugging Face hub.")
    return _tokenizer_bge_m3

def count_bge_m3_tokens(text: str) -> int:
    """Return token count of *text* for BGE-M3."""
    return len(get_bge_m3_tokenizer().encode(text, add_special_tokens=False))

# ========= 6. PDF VALIDATION =========
def validate_pdf_files() -> List[str]:
    """Ensure pdf_data_path exists + has PDFs."""
    if not os.path.exists(pdf_data_path):
        raise FileNotFoundError(f"No dir '{pdf_data_path}'")
    pdfs = [f for f in os.listdir(pdf_data_path) if f.lower().endswith(".pdf")]
    if not pdfs:
        raise ValueError(f"No PDFs in '{pdf_data_path}'")
    return pdfs

# ========= 7. LOAD & SPLIT =========
def load_and_split_documents():
    """Load PDFs and split into token-based chunks."""
    try:
        loader = DirectoryLoader(pdf_data_path, glob="*.pdf", loader_cls=PyPDFLoader)
        docs = loader.load()
        print(f"Loaded {len(docs)} documents")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=count_bge_m3_tokens,
            separators=["\n\n", "\n", ". ", " "],
            keep_separator=True,
        )
        chunks = splitter.split_documents(docs)
        if not chunks:
            raise ValueError("Splitting produced 0 chunks")
        return chunks
    except Exception as exc:
        traceback.print_exc()
        raise RuntimeError(f"Load/split error: {exc}")

# ========= 8. VECTOR STORE (COSINE) =========
def create_vector_store(chunks):
    """
    Build a FAISS vector store whose .index is IndexFlatIP
    (cosine similarity on unit vectors).
    """
    try:
        print(f"Embedding {len(chunks)} chunks …")

        # 8.1  Wrapper that always outputs unit vectors
        from faiss import normalize_L2
        class NormBGEM3(BGEM3Embeddings):
            def embed_documents(self, texts):
                vecs = super().embed_documents(texts)
                arr = np.asarray(vecs, dtype="float32")
                normalize_L2(arr)
                return arr.tolist()
            def embed_query(self, text):
                vec = super().embed_query(text)
                arr = np.asarray([vec], dtype="float32")
                normalize_L2(arr)
                return arr[0].tolist()
        embed_model = NormBGEM3(model_path=bge_m3_model_path)

        # 8.2  Create temporary vector store (L2) just to get mapping/docstore
        db = FAISS.from_documents(chunks, embed_model)   # uses default L2 index

        # 8.3  Re-build IndexFlatIP with same vectors
        dim = len(embed_model.embed_query("sample"))
        ip_index = faiss.IndexFlatIP(dim)

        # Re-embed all chunks as np.float32 and add to cosine index
        texts = [c.page_content for c in chunks]
        vecs  = np.asarray(embed_model.embed_documents(texts), dtype="float32")
        ip_index.add(vecs)

        # 8.4  Replace L2 index with our cosine index
        db.index = ip_index

        # 8.5  Persist vector store
        os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)
        db.save_local(vector_db_path)
        print(f"Vector store saved to '{vector_db_path}'")
        return db
    except Exception as exc:
        traceback.print_exc()
        raise RuntimeError(f"Vector-store error: {exc}")

# ========= 9. MAIN =========
def main():
    """Validate, split, build cosine store, run quick tests."""
    try:
        print("Validating PDFs …")
        validate_pdf_files()

        print("Loading & splitting …")
        chunks = load_and_split_documents()
        print(f"Total chunks: {len(chunks)}")

        print("Creating cosine FAISS store …")
        db = create_vector_store(chunks)

        print("\nVector store tests:")

        # Test 1 – index size
        if db.index.ntotal == len(chunks):
            print("[OK] Index size matches chunk count")
        else:
            print("[WARN] Index size mismatch")

        # Test 2 – normal query
        query = "Tự kỷ và rối loạn phổ tự kỷ giống và khác nhau như thế nào?"
        res = db.similarity_search_with_score(query, k=3)

        if res:
            # -------- get the single most relevant chunk --------
            top_doc, top_score = res[0]

            # str – full chunk content
            top_content: str = top_doc.page_content

            # dict – metadata (e.g., filename, page number)
            top_meta: dict = top_doc.metadata

            # int – token count for the chunk (optional diagnostic)
            top_tokens: int = count_bge_m3_tokens(top_content)

            # -------- print FULL chunk (no truncation) ----------
            print("\n[OK] ===== Top-1 result =====")
            print(f"Cosine score : {top_score:.4f}")
            print(f"Token count  : {top_tokens}")
            print(f"Metadata     : {top_meta}")
            print("------------- FULL CHUNK -------------")
            print(top_content)        # full text
            print("=========== END OF CHUNK =============\n")
        else:
            print("[WARN] No hits for test query")
        self_txt = chunks[0].page_content
        self_res = db.similarity_search_with_score(self_txt, k=1)
        if self_res:
            _, self_score = self_res[0]
            print(f"[OK] Self cosine={self_score:.4f}")
        else:
            print("[WARN] Self search returned no hits")

    except Exception as exc:
        print(f"MAIN ERROR: {exc}")
        traceback.print_exc()
        if os.path.exists(vector_db_path):
            import shutil
            shutil.rmtree(vector_db_path, ignore_errors=True)

# ========= 10. ENTRY POINT =========
if __name__ == "__main__":
    os.makedirs("models",                       exist_ok=True)
    os.makedirs(pdf_data_path,                  exist_ok=True)
    os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)

    print(f"PDF dir   : {os.path.abspath(pdf_data_path)}")
    print(f"FAISS dir : {os.path.abspath(vector_db_path)}")
    print(f"Model dir : {os.path.abspath(bge_m3_model_path)}\n")

    main()
