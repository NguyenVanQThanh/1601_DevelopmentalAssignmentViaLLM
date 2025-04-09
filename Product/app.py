import os
import traceback
import torch
from typing import List, Optional
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult

# --- Configuration ---
BARTPHO_MODEL_PATH = "./models/bartpho-syllable"
LLM_MODEL_NAME = "vilm/vinallama-2.7b-chat"
LLM_LOCAL_PATH = "./models/vinallama-2.7b-chat"
BGE_M3_MODEL_PATH = "./models/bge-m3"
VECTOR_DB_PATH = "vectorstores/db_faiss"
HISTORY_FILE_PATH = "conversation_history.json"
USE_PREPROCESSING = False
MAX_HISTORY_TURNS = 2
MAX_LENGTH = 2048

# --- Custom SentenceTransformer Embeddings ---
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_tensor=False, show_progress_bar=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text], convert_to_tensor=False, show_progress_bar=False).tolist()[0]

# --- Custom LLM Wrapper for Transformers Pipeline ---
class TransformersPipelineLLM(BaseLLM):
    def __init__(self, pipeline_obj):
        super().__init__()
        self._pipeline = pipeline_obj

    def _generate(self, prompts: List[str], stop: Optional[List[str]] = None, **kwargs) -> LLMResult:
        responses = []
        for prompt in prompts:
            output = self._pipeline(prompt, max_new_tokens=256, num_return_sequences=1)[0]
            responses.append(Generation(text=output["generated_text"]))
        return LLMResult(generations=[responses])

    @property
    def _llm_type(self) -> str:
        return "transformers_pipeline"

# --- Model Loading ---
bartpho_tokenizer = None
bartpho_model = None
summarizer = None
if USE_PREPROCESSING and os.path.exists(BARTPHO_MODEL_PATH):
    try:
        bartpho_tokenizer = AutoTokenizer.from_pretrained(BARTPHO_MODEL_PATH, local_files_only=True)
        bartpho_model = AutoModelForCausalLM.from_pretrained(BARTPHO_MODEL_PATH, local_files_only=True)
        summarizer = pipeline("text2text-generation", model=bartpho_model, tokenizer=bartpho_tokenizer, device=-1)
    except Exception:
        USE_PREPROCESSING = False

def load_llm(model_name=LLM_MODEL_NAME, local_path=LLM_LOCAL_PATH):
    print(f"Checking and loading LLM...")
    if os.path.exists(local_path):
        print(f"Found model at {local_path}. Loading from local...")
        tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(local_path, torch_dtype=torch.float32, low_cpu_mem_usage=True)
    else:
        print(f"Model not found at {local_path}. Downloading from Hugging Face ({model_name})...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32, low_cpu_mem_usage=True)
        print(f"Saving model to {local_path}...")
        tokenizer.save_pretrained(local_path)
        model.save_pretrained(local_path)
    llm_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, max_length=MAX_LENGTH, truncation=True, return_full_text=False, device=-1)
    print("LLM loaded successfully.")
    return TransformersPipelineLLM(llm_pipeline)

def read_vectors_db(vector_db_path, bge_m3_model_path):
    print("Loading Embedding model and Vector DB...")
    if not os.path.exists(vector_db_path):
        raise FileNotFoundError(f"Vector DB not found at {vector_db_path}")
    if not os.path.exists(bge_m3_model_path):
        print(f"Directory {bge_m3_model_path} not found. Downloading BGE-M3 model...")
        embedding_model = SentenceTransformer('BAAI/bge-m3')
        embedding_model.save(bge_m3_model_path)
    else:
        embedding_model = SentenceTransformer(bge_m3_model_path)
    embedding_model = SentenceTransformerEmbeddings(bge_m3_model_path)
    db = FAISS.load_local(vector_db_path, embedding_model, allow_dangerous_deserialization=True)
    print("Embedding and Vector DB loaded.")
    return db

def preprocess_input(text):
    if not USE_PREPROCESSING or summarizer is None:
        return text
    try:
        return summarizer(text, max_length=128, min_length=5, do_sample=False, num_beams=5)[0]['generated_text']
    except Exception:
        return text

# --- RAG Setup ---
try:
    db = read_vectors_db(VECTOR_DB_PATH, BGE_M3_MODEL_PATH)
    llm = load_llm(LLM_MODEL_NAME, LLM_LOCAL_PATH)
    retriever = db.as_retriever(search_type="similarity", search_kwargs={'k': 2})
except FileNotFoundError as e:
    raise HTTPException(status_code=500, detail=f"Initialization error: {e}")
except Exception as e:
    traceback.print_exc()
    raise HTTPException(status_code=500, detail=f"Unexpected initialization error: {e}")

message_history = FileChatMessageHistory(file_path=HISTORY_FILE_PATH)

template = """<|im_start|>system
Bạn là trợ lý AI, trả lời tập trung vào trọng tâm câu hỏi ({question}) ngắn gọn, chính xác, chỉ dùng thông tin liên quan trực tiếp đến câu hỏi từ tài liệu (context).  
- Ưu tiên thông tin từ tài liệu phù hợp nhất với câu hỏi, bỏ qua nội dung không liên quan.  
- Nếu không có thông tin phù hợp, trả lời: "Không tìm thấy thông tin phù hợp."  
- Trả lời bằng tiếng Việt, dưới 50 từ.  

**Lịch sử hội thoại:**  
{chat_history}  

**Tài liệu:**  
{context}  
<|im_end|>  
<|im_start|>user  
{question}  
<|im_end|>  
<|im_start|>assistant
"""
QA_PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "context", "question"])

try:
    question_answer_chain = create_stuff_documents_chain(llm, QA_PROMPT)
except Exception as e:
    traceback.print_exc()
    raise HTTPException(status_code=500, detail=f"Error creating chain: {e}")

def format_limited_chat_history(history_messages, max_turns=MAX_HISTORY_TURNS):
    if not history_messages:
        return "Không có lịch sử hội thoại."
    num_messages_to_keep = max_turns * 2
    recent_messages = history_messages[-num_messages_to_keep:]
    formatted_history = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            formatted_history.append(f"<|im_start|>user\n{msg.content}<|im_end|>")
        elif isinstance(msg, AIMessage):
            formatted_history.append(f"<|im_start|>assistant\n{msg.content}")
    return "\n".join(formatted_history)

def chatbot_response(msg):
    processed_msg = preprocess_input(msg)
    try:
        relevant_docs = retriever.invoke(processed_msg)
        if relevant_docs:
            first_chunk_content = relevant_docs[0].page_content
            first_chunk_source = relevant_docs[0].metadata.get('source', 'N/A')
            print("\n--- Nội dung chunk đầu tiên ---")
            print(f"(Nguồn: {first_chunk_source})\n{first_chunk_content}")
            print("-----------------------------\n")
        else:
            print("Không tìm thấy chunk nào.")
        try:
            current_history_messages = FileChatMessageHistory(file_path=HISTORY_FILE_PATH).messages
        except Exception:
            current_history_messages = []
        formatted_limited_history = format_limited_chat_history(current_history_messages)
        final_input_dict = {"question": processed_msg, "context": relevant_docs, "chat_history": formatted_limited_history}
        response = question_answer_chain.invoke(final_input_dict)
        chatbot_response_text = response.split('<|im_end|>')[0].strip()
        message_history.add_user_message(processed_msg)
        message_history.add_ai_message(chatbot_response_text)
        return chatbot_response_text
    except Exception as e:
        print(f"RAG processing error: {e}")
        traceback.print_exc()
        return "Đã xảy ra lỗi trong quá trình xử lý yêu cầu của bạn."

# --- FastAPI App ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/get")
def get_bot_response(msg: str = Query(...)):
    if not msg.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")
    return chatbot_response(msg)

if os.path.exists(HISTORY_FILE_PATH):
    try:
        os.remove(HISTORY_FILE_PATH)
    except OSError as e:
        print(f"Error deleting history file: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
