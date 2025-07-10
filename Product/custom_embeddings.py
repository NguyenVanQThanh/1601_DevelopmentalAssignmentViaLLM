from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from typing import List
from huggingface_hub import snapshot_download
import torch
import os

def is_valid_sentence_transformer_model(path: str) -> bool:
    required_files = ['config.json', 'pytorch_model.bin', 'sentence_bert_config.json']
    return all(os.path.isfile(os.path.join(path, f)) for f in required_files)

class BGEM3Embeddings(Embeddings):
    def __init__(self, model_path: str, device: str = "auto"):
        """
        BGEM3Embeddings: Ưu tiên tải model từ local nếu có, ngược lại sẽ tải từ Hugging Face và lưu lại.

        :param model_path: Đường dẫn thư mục local để kiểm tra hoặc lưu model.
        :param device: 'auto' (mặc định, ưu tiên CUDA), 'cpu', hoặc 'cuda'
        """
        self.device_to_use = "cuda" if (device == "auto" and torch.cuda.is_available()) else device
        print(f"Sử dụng thiết bị: {self.device_to_use}")

        if os.path.isdir(model_path) and is_valid_sentence_transformer_model(model_path):
            print(f"Phát hiện model hợp lệ tại '{model_path}', đang tải lên '{self.device_to_use}'...")
            model_source = model_path
        else:
            print(f"Không tìm thấy model hợp lệ tại '{model_path}', đang tải từ Hugging Face...")
            try:
                snapshot_download(
                    repo_id="BAAI/bge-m3",
                    local_dir=model_path,
                    local_dir_use_symlinks=False,
                    resume_download=True
                )
                print(f"Đã tải và lưu model tại '{model_path}'")
                model_source = model_path
            except Exception as e:
                print(f"Lỗi khi tải model từ Hugging Face: {e}")
                raise

        try:
            self.model = SentenceTransformer(model_source, device=self.device_to_use)
            print(f"Đã tải thành công model từ '{model_source}' lên thiết bị '{self.device_to_use}'.")
        except Exception as e:
            print(f"Lỗi khi load SentenceTransformer từ '{model_source}': {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return embedding.tolist()
