import os
import traceback
import re
import json
import time
import psutil
from typing import List, Optional, Any, Dict
from contextlib import contextmanager
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

import redis
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from langchain_community.llms import Ollama

from custom_embeddings import BGEM3Embeddings 

import pandas as pd

from dotenv import load_dotenv
load_dotenv()

# ==== CONFIGURATION (Loaded from .env with defaults) ========================
# LLM_MODEL_NAME: str - Name of the LLM model in Ollama.
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "vistral-assistant")
# BGE_M3_MODEL_PATH: str - Filesystem path to the BGE-M3 embedding model.
BGE_M3_MODEL_PATH = os.getenv("BGE_M3_MODEL_PATH", "./models/bge-m3")
# VECTOR_DB_PATH: str - Filesystem path to the FAISS vector database.
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vectorstores/db_faiss_test")
# CTX_WINDOW: int - Context window size of the Ollama model.
CTX_WINDOW = int(os.getenv("CTX_WINDOW", "8192"))
# MAX_NEW_TOKENS: int - Maximum new tokens the LLM will generate.
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "8192"))
# PROMPT_LENGTH_BUFFER: int - Safety buffer for prompt length calculations.
PROMPT_LENGTH_BUFFER = int(os.getenv("PROMPT_LENGTH_BUFFER", "50"))
# stop_tokens_str: str - Comma-separated string of stop tokens from .env.
stop_tokens_str = os.getenv("STOP_TOKENS_STR", "<|im_end|>,</s>")
# STOP_TOKENS: List[str] - List of stop tokens for LLM generation.
STOP_TOKENS = [token.strip() for token in stop_tokens_str.split(',')] if stop_tokens_str else ["<|im_end|>", "</s>"]
# MAX_HISTORY_TURNS: int - Maximum number of conversation turns to include in the history for LLM prompt.
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "3"))

# REDIS_HOST: str - Hostname or IP address of the Redis server.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
# REDIS_PORT: int - Port number of the Redis server.
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# REDIS_DB_ASQ: int - Redis database number for ASQ data.
REDIS_DB_ASQ = int(os.getenv("REDIS_DB_ASQ", "0"))
# REDIS_DB_HISTORY: int - Redis database number for Chat History.
REDIS_DB_HISTORY = int(os.getenv("REDIS_DB_HISTORY", "1"))
# SESSION_TTL_SECONDS: int - Time-to-live in seconds for session data in Redis.
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "7200"))

# ASQ_DATA_DIR: str - Directory containing ASQ-3 JSON data files.
ASQ_DATA_DIR = os.getenv("ASQ_DATA_DIR", "./ASQ3API/data")
# DEFAULT_ASQ_FILENAME: str - Default ASQ-3 JSON filename.
DEFAULT_ASQ_FILENAME = os.getenv("DEFAULT_ASQ_FILENAME", "18month.json")
# ASQ_JSON_FILE: Optional[str] - Full path to the default ASQ-3 JSON file.
ASQ_JSON_FILE = os.path.join(ASQ_DATA_DIR, DEFAULT_ASQ_FILENAME) if DEFAULT_ASQ_FILENAME else None
# EXCEL_OUTPUT_DIR: str - Directory to store generated Excel files with ASQ results.
EXCEL_OUTPUT_DIR = os.getenv("EXCEL_OUTPUT_DIR", "./asq_excel_results")
# FIXED_EXCEL_RESULTS_FILE: str - Fixed filename for ASQ test results.
FIXED_EXCEL_RESULTS_FILE = os.path.join(EXCEL_OUTPUT_DIR, "results_test.xlsx")
# FIXED_EXCEL_INFO_FILE: str - Fixed filename for general test information.
FIXED_EXCEL_INFO_FILE = os.path.join(EXCEL_OUTPUT_DIR, "information_test.xlsx")


# SECRET_KEY: str - Secret key for signing JWTs. Should be strong and kept secret.
SECRET_KEY = os.getenv("SECRET_KEY", "please-set-a-strong-secret-key-in-your-env-file")
if SECRET_KEY == "please-set-a-strong-secret-key-in-your-env-file":
    print("WARNING: Default SECRET_KEY is being used. Please set a strong, unique SECRET_KEY in your .env file for security!")
# ALGORITHM: str - Algorithm used for JWT signing.
ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES: int - Expiry time for access tokens in minutes.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

# default_asq_questionnaire_rules: dict - Loaded default ASQ-3 questionnaire rules.
default_asq_questionnaire_rules = {}
if ASQ_JSON_FILE and os.path.exists(ASQ_JSON_FILE):
    try:
        with open(ASQ_JSON_FILE, "r", encoding="utf-8") as f: default_asq_questionnaire_rules = json.load(f)
    except Exception as e: print(f"Warning: Could not load default ASQ file {ASQ_JSON_FILE}: {e}")
elif ASQ_JSON_FILE: print(f"Warning: Default ASQ file {ASQ_JSON_FILE} not found.")

# ==== FASTAPI APP & MIDDLEWARE ===============================================
# app: FastAPI - The FastAPI application instance.
app = FastAPI(title="ASQ & Chatbot API", version="1.0.3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ==== REDIS CLIENT INITIALIZATION =============================================
# redis_client: Optional[redis.Redis] - Global Redis client instance.
redis_client: Optional[redis.Redis] = None
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()
    print(f"Connected to Redis server at {REDIS_HOST}:{REDIS_PORT}")
except redis.exceptions.ConnectionError as e:
    print(f"CRITICAL ERROR: Could not connect to Redis: {e}. Functionality will be limited."); redis_client = None

# ==== JWT & SECURITY =========================================================
# oauth2_scheme: OAuth2PasswordBearer - OAuth2 scheme for token-based authentication.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Function Name: create_access_token
# Functionality: Creates a new JWT access token.
# Input: data (dict) - Data to be encoded in the token (e.g., {"sub": session_id}).
# Input: expires_delta (Optional[timedelta]) - Optional custom expiry time for the token.
# Output: str - The encoded JWT access token.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire}); return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Function Name: get_current_session
# Functionality: Verifies the JWT token from the request and returns its payload, primarily extracting the session_id.
# Input: token (str) - The JWT token obtained from the 'Authorization: Bearer <token>' header (managed by Depends(oauth2_scheme)).
# Output: dict - A dictionary containing the session_id (e.g., {"session_id": "some-uuid", "token_payload": {...original_payload...}}).
# Raises: HTTPException (401) - If the token is invalid, expired, or missing.
async def get_current_session(token: str = Depends(oauth2_scheme)) -> dict:
    cred_exc = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]); session_id: Optional[str] = payload.get("sub")
        if session_id is None: raise cred_exc
        return {"session_id": session_id, "token_payload": payload}
    except JWTError: raise cred_exc
    except Exception: raise cred_exc

# ==== UTILITY FUNCTIONS =======================================================
# Function Name: timer
# Functionality: A context manager to measure and print the execution time of a code block.
# Input: description (str) - A description of the timed operation.
# Output: None (prints elapsed time).
@contextmanager
def timer(description: str): start = time.time(); yield; print(f"{description}: {(time.time() - start):.3f}s")
# Function Name: get_memory_usage
# Functionality: Gets the current RSS memory usage of the process.
# Input: None.
# Output: float - Memory usage in MB.
def get_memory_usage() -> float: return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

# Function Name: append_to_excel
# Functionality: Appends a list of dictionaries (new rows) to an existing Excel file, or creates a new file.
# Input: data_list (List[Dict]) - A list of dictionaries, where each dictionary is a new row.
# Input: file_path (str) - The full path to the Excel file.
# Input: sheet_name (str) - The name of the sheet in the Excel file.
# Output: None.
def append_to_excel(data_list: List[Dict], file_path: str, sheet_name: str = "Sheet1"):
    if not data_list: print(f"No data to append to Excel file: {file_path}"); return
    try:
        df_new = pd.DataFrame(data_list)
        if os.path.exists(file_path):
            try:
                df_existing = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            except FileNotFoundError: df_combined = df_new
            except Exception as e_read: print(f"Error reading existing Excel file {file_path}: {e_read}. Creating new."); df_combined = df_new
        else: df_combined = df_new
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df_combined.to_excel(file_path, index=False, sheet_name=sheet_name, engine='openpyxl')
        print(f"Data successfully appended/saved to Excel: {file_path}")
    except Exception as e: print(f"Error appending/saving data to Excel file {file_path}: {e}"); traceback.print_exc()

# ==== CHATBOT COMPONENTS LOADING ==============================================
def load_llm() -> Ollama:
    try:
        llm_i = Ollama(model=LLM_MODEL_NAME,temperature=0.5,stop=STOP_TOKENS); llm_i.invoke("Hello")
        print(f"Model '{LLM_MODEL_NAME}' ready. Mem: {get_memory_usage():.2f}MB"); return llm_i
    except Exception as e: raise HTTPException(status_code=500, detail=f"LLM init error: {e}")
def load_vector_db() -> FAISS:
    for f in ("index.faiss", "index.pkl"):
        if not os.path.exists(f"{VECTOR_DB_PATH}/{f}"): raise HTTPException(status_code=500, detail=f"VectorDB file {f} missing.")
    try:
        emb = BGEM3Embeddings(BGE_M3_MODEL_PATH); db = FAISS.load_local(VECTOR_DB_PATH, emb, allow_dangerous_deserialization=True)
        if db.index.ntotal == 0: raise HTTPException(status_code=500, detail="Vector store empty.")
        print(f"Vector DB loaded. Items: {db.index.ntotal}. Mem: {get_memory_usage():.2f}MB"); return db
    except Exception as e: raise HTTPException(status_code=500, detail=f"VectorDB load error: {e}")

# ==== CHAT HISTORY MANAGEMENT ===============================================
def get_session_history(session_id: str) -> Any:
    if redis_client: return RedisChatMessageHistory(session_id=session_id, url=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_HISTORY}", ttl=SESSION_TTL_SECONDS)
    else:
        if not hasattr(app.state, 'in_mem_hist'): app.state.in_mem_hist = {}
        if session_id not in app.state.in_mem_hist: app.state.in_mem_hist[session_id] = InMemoryChatMessageHistory()
        return app.state.in_mem_hist[session_id]
def format_chat_history(msgs: List[AIMessage | HumanMessage], max_turns: int = MAX_HISTORY_TURNS) -> str:
    r = msgs[-max_turns*2:] if msgs else []; lns = []
    for i in range(0,len(r),2):
        if i+1 < len(r): h,a=r[i],r[i+1]; hc=h.content if hasattr(h,'content') else str(h); ac=a.content if hasattr(a,'content') else str(a); lns.extend([f"Người dùng: {hc}",f"Trợ lý AI: {ac}"])
    return "\n".join(lns) if lns else "Chưa có lịch sử hội thoại trước đó."

# ==== GLOBAL CHATBOT COMPONENTS & PROMPT TEMPLATES ============================
llm_global: Optional[Ollama] = None
retriever_global: Any = None
qa_chain_global: Any = None
QA_PROMPT_GLOBAL: Optional[PromptTemplate] = None
ASQ_SOLUTION_PROMPT_GLOBAL: Optional[PromptTemplate] = None
current_date_global: str = datetime.now().strftime("%Y-%m-%d")

print("Initializing chatbot components…")
try:
    llm_global = load_llm()
    vector_db_global = load_vector_db()
    retriever_global = vector_db_global.as_retriever(search_type="similarity", search_kwargs={"k": 4, "score_threshold": 0.5})
    
    qa_template_str = """<|im_start|>system
Bạn là trợ lý AI chuyên về sức khỏe và tâm thần nhi khoa. Mục tiêu của bạn là cung cấp thông tin chính xác, dễ hiểu và hữu ích cho phụ huynh. **Hãy luôn trả lời bằng tiếng Việt.**
**Đặc biệt khi có câu hỏi liên quan đến thông tin liên lạc và đặt lịch phòng khám hãy sử dụng những thông tin sau:
Thông tin liên hệ /đặt lịch phòng khám Tâm Lý Nhi Đồng: 
Số điện thoại/Zalo: 0981502721 
Địa chỉ: 625 Hậu Giang, quận 6, Tp. Hồ Chí Minh **
**QUAN TRỌNG: Tất cả các câu trả lời, lời khuyên, và thông tin về mốc phát triển phải dựa vào độ tuổi so với ngày hiện tại ({current_date}) được điều chỉnh và phù hợp CHÍNH XÁC với ĐỘ TUỔI của trẻ được đề cập trong câu hỏi hoặc lịch sử trò chuyện. Nếu không có thông tin độ tuổi rõ ràng, bạn có thể hỏi lại một cách lịch sự để làm rõ.**
{asq_guidance_placeholder}

Hãy tuân thủ các hướng dẫn sau:
0.  **HIỂU ĐÚNG NGỮ NGHĨA:** Hãy phân tích kỹ lưỡng toàn bộ câu hỏi của người dùng để hiểu đúng ngữ nghĩa của từng từ và ý định tổng thể, đặc biệt với các từ có thể có nhiều nghĩa trong ngữ cảnh phát triển của trẻ (ví dụ: "bập bẹ" có thể là tập nói hoặc tập đi). Cố gắng xác định kỹ năng chính mà người dùng đang quan tâm. Nếu không chắc chắn, bạn có thể ưu tiên diễn giải theo cách phổ biến nhất hoặc lịch sự hỏi lại người dùng để làm rõ.
1.  **Ưu tiên Context:** Lấy thông tin từ phần **Context** được cung cấp làm nguồn chính để trả lời câu hỏi. Thông tin trong Context có thể bằng tiếng Việt hoặc tiếng Anh; bạn cần hiểu và diễn đạt lại câu trả lời bằng tiếng Việt, đảm bảo phù hợp với độ tuổi.
2.  **Bổ sung từ kiến thức của bạn:** Nếu Context không có thông tin, không đầy đủ, hoặc bạn cảm thấy kiến thức đã được huấn luyện (fine-tuned) của mình có thể làm rõ hơn hoặc bổ sung giá trị cho câu trả lời, hãy sử dụng nó. Thông tin bổ sung phải liên quan trực tiếp đến câu hỏi, lĩnh vực chuyên môn của bạn, và **phù hợp với độ tuổi của trẻ.**
3.  **Chính xác và không bịa đặt:** Dù thông tin lấy từ Context hay từ kiến thức của bạn, nó phải chính xác, dựa trên cơ sở khoa học, và **hoàn toàn phù hợp với độ tuổi của trẻ đang được hỏi đến.** Tuyệt đối không bịa đặt thông tin hoặc đưa ra lời khuyên không phù hợp lứa tuổi.
4.  **Tập trung vào câu hỏi:** Luôn trả lời trực tiếp vào câu hỏi ({question}).
5.  **Khi không có thông tin:** Nếu cả Context và kiến thức đã huấn luyện của bạn đều không có thông tin để trả lời câu hỏi, hãy thông báo một cách lịch sự, ví dụ: "Tôi rất tiếc, hiện tại tôi không có đủ thông tin về chủ đề này từ cả tài liệu được cung cấp lẫn kiến thức của mình."
6.  **Diễn đạt:** Tự nhiên, không trích dẫn nguyên văn từ Context trừ khi đó là một định nghĩa quan trọng hoặc trích dẫn ngắn cần thiết.
7.  **Định dạng:** Rõ ràng, dùng gạch đầu dòng (-) hoặc số (1., 2.) nếu phù hợp, câu đầy đủ, đúng ngữ pháp.
8.  **Giọng điệu:** Ngôn ngữ đơn giản, thân thiện, cảm thông và hỗ trợ.
9.  **Lịch sử hội thoại:** Sử dụng lịch sử ({chat_history}) để hiểu ngữ cảnh các câu hỏi trước đó, nhưng câu trả lời của bạn phải tập trung vào CÂU HỎI HIỆN TẠI, hạn chế sử dụng câu trả lời trước đó trong câu trả lời hiện tại.

**Context**:
{context}

**Lịch sử hội thoại**:
{chat_history}
<|im_end|>
<|im_start|>user
{question}<|im_end|>
<|im_start|>assistant
"""
    QA_PROMPT_GLOBAL = PromptTemplate(
        template=qa_template_str,
        input_variables=["chat_history", "context", "question", "asq_guidance_placeholder", "current_date"]
    )
    qa_chain_global = create_stuff_documents_chain(llm_global, QA_PROMPT_GLOBAL)

    asq_solution_template_str = """<|im_start|>system
Bạn là một chuyên gia phát triển nhi khoa. Dựa trên kết quả ASQ-3 của một trẻ và các thông tin chuyên ngành được cung cấp, hãy thực hiện nhiệm vụ sau.
Luôn trả lời bằng tiếng Việt, ngôn ngữ thân thiện, dễ hiểu. Nhấn mạnh tầm quan trọng của việc tham khảo ý kiến chuyên gia nếu có lo ngại.

**Thông tin trẻ và kết quả ASQ-3:**
- Tuổi: {age_details}
- Tóm tắt kết quả ASQ-3: {asq_summary}
- Chi tiết các lĩnh vực có thể cần chú ý dựa trên điểm số:
{asq_areas_of_concern}

**Nhiệm vụ cụ thể của bạn:**
{task_description}

**Định dạng các câu trả lời dạng danh sách cần xuống dòng rõ ràng.**
**Thông tin chuyên ngành tham khảo (nếu có để hỗ trợ nhiệm vụ):**
{rag_context}
<|im_end|>
<|im_start|>user
Dựa vào các thông tin trên, vui lòng {task_description_short}.
<|im_end|>
<|im_start|>assistant
"""
    ASQ_SOLUTION_PROMPT_GLOBAL = PromptTemplate(
        template=asq_solution_template_str,
        input_variables=["age_details", "asq_summary", "asq_areas_of_concern", "task_description", "rag_context", "task_description_short"]
    )
    print("Chatbot components initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR - Chatbot Init: {e}"); traceback.print_exc()
    llm_global = retriever_global = qa_chain_global = QA_PROMPT_GLOBAL = ASQ_SOLUTION_PROMPT_GLOBAL = None
    
class Answer(BaseModel): id: int; answer: str
class ASQQuestionAnswerPair(BaseModel): question_id: int; question_text: str; user_answer: str
class ASQSectionResultDetail(BaseModel): display_name: str; total_score: float; status: str; cutoff: float; monitor: float; answers_processed: List[Answer]
class ASQStoredResult(BaseModel): session_id: str; age_at_test_months: Optional[int] = None; questionnaire_title: Optional[str] = None; overall_summary: str; sections: Dict[str, ASQSectionResultDetail]
class ChildInfoSubmitted(BaseModel): fullName: Optional[str]=None; birthDate: Optional[str]=None; childAgeInDays: Optional[int]=None; location: Optional[str]=None; gender: Optional[str]=None; pre_birth: Optional[str]=None; pre_result: Optional[str]=None; result: Optional[str]=None; resultDate: Optional[str]=None; hospital: Optional[str]=None; doctor: Optional[str]=None; pre_test: Optional[str]=None
class ParentInfoSubmitted(BaseModel): parentFullName: Optional[str]=None; phone: Optional[str]=None; email: Optional[str]=None; address: Optional[str]=None; relationship: Optional[str]=None; place: Optional[str]=None
class ASQSubmissionPayload(BaseModel):
    age_at_test_months: Optional[int] = None; questionnaire_title: Optional[str] = None
    communication: Optional[List[Answer]] = None; gross_motor: Optional[List[Answer]] = None
    fine_motor: Optional[List[Answer]] = None; problem_solving: Optional[List[Answer]] = None
    personal_social: Optional[List[Answer]] = None
    child_information: Optional[ChildInfoSubmitted] = None
    parent_information: Optional[ParentInfoSubmitted] = None

def get_asq_questionnaire_rules(title: Optional[str]=None, age_months: Optional[int]=None) -> dict:
    if title and os.path.isdir(ASQ_DATA_DIR) :
        month_str = "".join(filter(str.isdigit, title.split("m")[0])) if title and "m" in title else ""
        if month_str:
            f_path = os.path.join(ASQ_DATA_DIR, f"{month_str}month.json")
            if os.path.exists(f_path):
                try:
                    with open(f_path, "r", encoding="utf-8") as f: return json.load(f)
                except Exception as e: print(f"Error loading ASQ rules {f_path}: {e}")
    if age_months and os.path.isdir(ASQ_DATA_DIR):
        age_days = age_months * 30.44
        for fname in os.listdir(ASQ_DATA_DIR):
            if fname.endswith(".json"):
                f_path = os.path.join(ASQ_DATA_DIR, fname)
                try:
                    with open(f_path, "r", encoding="utf-8") as f: r_data = json.load(f)
                    age_info = r_data.get("age", {}).get("range_in_days", {})
                    min_d, max_d = age_info.get("min_days"), age_info.get("max_days")
                    if min_d is not None and max_d is not None and min_d <= age_days <= max_d: return r_data
                except: pass
    return default_asq_questionnaire_rules
def apply_scoring_logic(section: str,answers: List[Answer],q_data: dict)-> List[Answer]:
    s_data=q_data.get("question",{}).get(section,{});note=s_data.get("scoring_note")
    if not note:return answers
    ans_dict={a.id:a for a in answers if isinstance(a,Answer)}
    cond=note.get("condition",{});act=note.get("action",{})
    if not cond or not act or "question_id" not in cond or "question_id" not in act:return answers
    cond_ans=ans_dict.get(cond["question_id"])
    if cond_ans and cond_ans.answer in cond.get("values",[])and act["question_id"]in ans_dict:ans_dict[act["question_id"]].answer=act.get("set_value")
    return list(ans_dict.values())
def calculate_score(answers:List[Answer])->float:m={"Có":10,"Thỉnh Thoảng":5,"Chưa":0};return sum(m.get(a.answer,0)for a in answers if isinstance(a,Answer))
def determine_status(score:float,cutoff:float,monitor:float)->str:
    if cutoff==0 and monitor==0:return"Không áp dụng điểm chuẩn"
    if score<cutoff:return"CHẬM RÕ RỆT (Cần đánh giá chuyên sâu)"
    if score<=monitor:return"CÓ NGUY CƠ CHẬM (Cần theo dõi sát)"
    return"PHÁT TRIỂN BÌNH THƯỜNG"
def replace_image_placeholders(data:dict)->dict:
    t2p={"2m Questionnaire":"image2_","4m Questionnaire":"image4_", "6m Questionnaire":"image6_","8m Questionnaire":"image8_","9m Questionnaire":"image9_","10m Questionnaire":"image10_","12m Questionnaire":"image12_","14m Questionnaire":"image14_","16m Questionnaire":"image16_","18m Questionnaire":"image18_","20m Questionnaire":"image20_","22m Questionnaire":"image22_","24m Questionnaire":"image24_","27m Questionnaire":"image27_","30m Questionnaire":"image30_","33m Questionnaire":"image33_","36m Questionnaire":"image36_","42m Questionnaire":"image42_","48m Questionnaire":"image48_","54m Questionnaire":"image54_","60m Questionnaire":"image60_"}
    t=data.get("age",{}).get("title");p=t2p.get(t)
    if not p:return data
    for sv in data.get("question",{}).values():
        if isinstance(sv,dict)and"questions"in sv:
            c=1
            for qi in sv.get("questions",[]):
                if isinstance(qi,dict)and qi.get("image_filepath")=="image_placeholder.png":qi["image_filepath"]=f"{p}{c}.png";c+=1
    return data

async def generate_llm_response_with_rag_for_asq(session_id: str, asq_data: ASQStoredResult, task_description: str, task_description_short: str) -> str:
    if not all([llm_global, retriever_global, ASQ_SOLUTION_PROMPT_GLOBAL]): raise HTTPException(status_code=503, detail="AI components for ASQ advice not ready.")
    age_details = f"{asq_data.age_at_test_months} tháng tuổi" if asq_data.age_at_test_months is not None else "không rõ độ tuổi"
    areas_concern_list = [f"- Lĩnh vực {s.display_name}: {s.status} (điểm {s.total_score:.0f})" for s in asq_data.sections.values() if "CHẬM" in s.status.upper()]
    asq_areas_str = "\n".join(areas_concern_list) if areas_concern_list else "Không có lĩnh vực nào được đánh giá là chậm hoặc có nguy cơ chậm rõ rệt từ kết quả điểm số."
    rag_query_parts = [f"gợi ý can thiệp và hoạt động cho trẻ {age_details} dựa trên kết quả ASQ sau: {asq_data.overall_summary}"]
    if areas_concern_list: rag_query_parts.append(f"Đặc biệt tập trung vào các lĩnh vực: {', '.join(s.split(':')[0].replace('Lĩnh vực ','') for s in areas_concern_list).strip(', ')}.")
    rag_query = " ".join(rag_query_parts)
    with timer(f"RAG for ASQ Task (session {session_id})"): rag_docs: List[Document] = retriever_global.invoke(rag_query)
    rag_context_str = "\n\n---\n\n".join([doc.page_content for doc in rag_docs]) if rag_docs else "Không tìm thấy thông tin chuyên ngành bổ sung từ tài liệu."
    max_rag_ctx_tokens = CTX_WINDOW // 4; current_rag_tokens = llm_global.get_num_tokens(rag_context_str)
    if current_rag_tokens > max_rag_ctx_tokens:
        ratio = max_rag_ctx_tokens / current_rag_tokens if current_rag_tokens > 0 else 0
        estimated_len = int(len(rag_context_str) * ratio); rag_context_str = rag_context_str[:estimated_len]
        print(f"Truncated RAG context for ASQ to approx. {llm_global.get_num_tokens(rag_context_str)} tokens.")
    final_prompt_for_llm = ASQ_SOLUTION_PROMPT_GLOBAL.format(age_details=age_details, asq_summary=asq_data.overall_summary, asq_areas_of_concern=asq_areas_str, task_description=task_description, rag_context=rag_context_str, task_description_short=task_description_short)
    with timer(f"LLM for ASQ Task '{task_description_short}'"): raw_response = llm_global.invoke(final_prompt_for_llm)
    cleaned_response = raw_response.strip()
    for token in STOP_TOKENS + ["<|im_start|>", "<|im_end|>"]: cleaned_response = cleaned_response.replace(token, "")
    return re.sub(r"^\s*assistant:\s*", "", cleaned_response, flags=re.I).strip()

class TokenResponse(BaseModel): access_token: str; token_type: str; session_id: str
@app.post("/token", response_model=TokenResponse, summary="Get Session Token")
async def get_session_token_route():
    session_id=str(uuid.uuid4());token=create_access_token(data={"sub":session_id});print(f"Token for session {session_id} generated.")
    return {"access_token":token,"token_type":"bearer","session_id":session_id}

@app.get("/asq/form", response_class=JSONResponse, summary="Get ASQ-3 Form by Age")
async def get_asq_form_route(age_in_days: int = Query(...,ge=0, description="Child's age in days.")):
    if not os.path.isdir(ASQ_DATA_DIR):raise HTTPException(status_code=500,detail=f"ASQ dir missing: {ASQ_DATA_DIR}")
    matched_data=None
    for fname in os.listdir(ASQ_DATA_DIR):
        if fname.endswith(".json"):
            fpath=os.path.join(ASQ_DATA_DIR,fname)
            try:
                with open(fpath,"r",encoding="utf-8")as f:d=json.load(f)
                r=d.get("age",{}).get("range_in_days",{})
                min_d,max_d=r.get("min_days"),r.get("max_days")
                if min_d is not None and max_d is not None and min_d<=age_in_days<=max_d:matched_data=d;break
            except:pass
    if not matched_data:raise HTTPException(status_code=404,detail="No ASQ form for age.")
    return JSONResponse(content=replace_image_placeholders(matched_data))

# Function Name: submit_asq_form_route
# Functionality: Receives submitted ASQ-3 answers, child, and parent information.
#                It processes the answers to calculate scores and determine developmental status for each section.
#                The processed results are stored in Redis, associated with the session ID.
#                Additionally, it prepares and appends the submitted information and processed results
#                to two separate Excel files: one for general information and one for detailed test results.
# Input: data (ASQSubmissionPayload) - Pydantic model containing the ASQ answers and related information.
# Input: current_session (dict) - Dependency injected by Depends(get_current_session),
#                                  contains the validated session_id from the JWT token.
# Output: JSONResponse - Contains the fully processed ASQ-3 results (ASQStoredResult model) for the current session.
# Raises: HTTPException (503) - If the Redis service is unavailable.
# Raises: HTTPException (500) - If ASQ scoring rules are missing for the specified questionnaire/age,
#                                or if any other unexpected server error occurs during processing or Excel saving.
# Raises: HTTPException (400) - If no valid ASQ answers are provided in the submission.
@app.post("/asq/result", response_class=JSONResponse, summary="Submit ASQ-3 Answers, Get Results, and Log to Excel")
async def submit_asq_form_route(data:ASQSubmissionPayload,current_session:dict=Depends(get_current_session)):
    # session_id: str - The unique identifier for the current user's session, extracted from the JWT.
    session_id=current_session["session_id"]
    if not redis_client:raise HTTPException(status_code=503,detail="Redis unavailable.")
    
    # rules: dict - The ASQ-3 questionnaire rules (questions, cutoffs, etc.) for the specified age/title.
    rules=get_asq_questionnaire_rules(data.questionnaire_title,data.age_at_test_months)
    if not rules or "question" not in rules: # Check if rules were successfully loaded and are valid
        raise HTTPException(status_code=500,detail=f"ASQ rules missing for {data.questionnaire_title or data.age_at_test_months}.")
    
    # current_timestamp_iso: str - ISO formatted timestamp for when the test results are processed.
    current_timestamp_iso = datetime.now(timezone.utc).isoformat()

    # --- Prepare data for "information_test.xlsx" ---
    # information_data_for_excel: Dict - Dictionary to hold a single row of general information for the 'information_test.xlsx' file.
    information_data_for_excel = {
        "session_id": session_id,
        "test_timestamp": current_timestamp_iso,
        "age_at_test_months": data.age_at_test_months,
        "questionnaire_title": data.questionnaire_title or rules.get("age",{}).get("title","Unknown"),
    }
    if data.child_information:
        information_data_for_excel["child_fullName"] = data.child_information.fullName
        information_data_for_excel["child_birthDate"] = data.child_information.birthDate
        information_data_for_excel["child_ageInDays"] = data.child_information.childAgeInDays
        information_data_for_excel["child_gender"] = data.child_information.gender
        information_data_for_excel["child_location"] = data.child_information.location
        information_data_for_excel["child_pre_birth"] = data.child_information.pre_birth
        information_data_for_excel["child_pre_result_diagnosis"] = data.child_information.pre_result
        if data.child_information.pre_result and data.child_information.pre_result.lower() == "có":
            information_data_for_excel["child_diagnosis_result"] = data.child_information.result
            information_data_for_excel["child_diagnosis_date"] = data.child_information.resultDate
            information_data_for_excel["child_diagnosis_hospital"] = data.child_information.hospital
            information_data_for_excel["child_diagnosis_doctor"] = data.child_information.doctor
            information_data_for_excel["child_pre_screened_asq_mchatr"] = data.child_information.pre_test
    
    if data.parent_information:
        information_data_for_excel["parent_fullName"] = data.parent_information.parentFullName
        information_data_for_excel["parent_phone"] = data.parent_information.phone
        information_data_for_excel["parent_email"] = data.parent_information.email
        information_data_for_excel["parent_address"] = data.parent_information.address
        information_data_for_excel["parent_relationship"] = data.parent_information.relationship
        information_data_for_excel["screening_place"] = data.parent_information.place
    # --- CLEAR CHAT HISTORY FOR THIS SESSION AFTER NEW ASQ SUBMISSION ---
    try:
        # history_obj_to_clear: RedisChatMessageHistory | InMemoryChatMessageHistory - History object for the session.
        history_obj_to_clear = get_session_history(session_id)
        if isinstance(history_obj_to_clear, RedisChatMessageHistory):
            history_obj_to_clear.clear() 
            print(f"Chat history for session {session_id} (key: {history_obj_to_clear.key}) cleared after new ASQ submission.")
        elif isinstance(history_obj_to_clear, InMemoryChatMessageHistory): # Fallback
            if hasattr(app.state, 'in_mem_hist') and session_id in app.state.in_mem_hist:
                app.state.in_mem_hist[session_id].clear()
                print(f"InMemory chat history for session {session_id} cleared after new ASQ submission.")
    except Exception as e_clear_hist:
        print(f"Warning: Could not clear chat history for session {session_id} after ASQ submission: {e_clear_hist}")
        # Continue even if clearing history fails, as ASQ data is already saved.
    try:
        # summary_parts: List[str] - List to accumulate summary strings for each ASQ section.
        summary_parts=[]
        # result_data_to_store: ASQStoredResult - Pydantic model instance to store structured processed results in Redis.
        result_data_to_store=ASQStoredResult(
            session_id=session_id,
            age_at_test_months=data.age_at_test_months,
            questionnaire_title=data.questionnaire_title or rules.get("age",{}).get("title","Unknown"),
            overall_summary="", 
            sections={}
        )
        
        # --- Prepare data for "results_test.xlsx" ---
        # results_details_for_excel_list: List[Dict] - A list where each dictionary represents a row (one question's details)
        #                                            for the 'results_test.xlsx' file.
        results_details_for_excel_list = []
        
        # section_keys_list: List[str] - Standard ASQ-3 section keys.
        section_keys_list = ["communication","gross_motor","fine_motor","problem_solving","personal_social"]
        for sec_key in section_keys_list:
            # answers_raw: Optional[List[Answer]] - Raw answers for the current section from the submission payload.
            answers_raw=getattr(data,sec_key,None)
            if answers_raw:
                # ans_objs: List[Answer] - List of Answer Pydantic model instances for the current section.
                ans_objs=[a if isinstance(a,Answer)else Answer(**a.model_dump())for a in answers_raw]
                # proc_ans: List[Answer] - Answers after applying specific scoring logic (e.g., conditional scoring).
                proc_ans=apply_scoring_logic(sec_key,ans_objs,rules);
                # score: float - Total calculated score for the current section.
                score=calculate_score(proc_ans)
                # sec_rules: dict - Scoring rules (cutoff, monitor) for the current section.
                sec_rules=rules.get("question",{}).get(sec_key,{});
                # cut: float - Cutoff score for "clear delay" status.
                cut=sec_rules.get("cutoff",0.0);
                # mon: float - Monitor threshold score for "at risk" status.
                mon=sec_rules.get("monitor_cutoff",sec_rules.get("cutoff",0.0)+15.0)
                # status: str - Determined developmental status for the section.
                status=determine_status(score,cut,mon);
                # title_map: Dict[str, str] - Mapping from section keys to display names.
                title_map={"communication":"Giao tiếp","gross_motor":"Vận động thô","fine_motor":"Vận động tinh","problem_solving":"Giải quyết vấn đề","personal_social":"Cá nhân xã hội"}
                # disp_name: str - Display name for the current section.
                disp_name=title_map.get(sec_key,sec_key.replace('_',' ').title());
                summary_parts.append(f"{disp_name}: {status} ({score:.0f}đ).")
                
                # section_result_detail_obj: ASQSectionResultDetail - Pydantic model instance for detailed section results.
                section_result_detail_obj = ASQSectionResultDetail(
                    display_name=disp_name,total_score=score,status=status,cutoff=cut,monitor=mon,
                    answers_processed=[Answer(id=a.id,answer=a.answer)for a in proc_ans]
                )
                result_data_to_store.sections[sec_key]=section_result_detail_obj

                # q_rules: List[Dict] - List of question definitions for the current section from the ASQ rules.
                q_rules = rules.get("question", {}).get(sec_key, {}).get("questions", [])
                # q_text_map: Dict[int, str] - Mapping from question ID to question text for easy lookup.
                q_text_map = {q_rule.get("id"): q_rule.get("text") for q_rule in q_rules}

                for ans_proc_item in proc_ans:
                    # excel_row_result: Dict - Dictionary representing a single row for the detailed results Excel file.
                    excel_row_result = {
                        "session_id": session_id, 
                        "test_timestamp": current_timestamp_iso,
                        "parent_phone": data.parent_information.phone if data.parent_information else None,
                        "age_at_test_months": data.age_at_test_months,
                        "questionnaire_title": result_data_to_store.questionnaire_title,
                        "section_key": sec_key,
                        "section_display_name": disp_name,
                        "question_id": ans_proc_item.id,
                        "question_text": q_text_map.get(ans_proc_item.id, f"Question ID {ans_proc_item.id}"),
                        "answer": ans_proc_item.answer,
                        "section_total_score": score,
                        "section_status": status,
                        "section_cutoff": cut,
                        "section_monitor": mon
                    }
                    results_details_for_excel_list.append(excel_row_result)

        if not summary_parts:raise HTTPException(status_code=400,detail="No valid ASQ answers.")
        result_data_to_store.overall_summary=" ".join(summary_parts)
        
        redis_client.set(f"asq_data:{session_id}",result_data_to_store.model_dump_json(exclude_none=True),ex=SESSION_TTL_SECONDS)
        print(f"ASQ results saved for session {session_id} to Redis.")

        if not os.path.exists(EXCEL_OUTPUT_DIR): os.makedirs(EXCEL_OUTPUT_DIR, exist_ok=True)
        
        append_to_excel([information_data_for_excel], FIXED_EXCEL_INFO_FILE, sheet_name="Information")
        append_to_excel(results_details_for_excel_list, FIXED_EXCEL_RESULTS_FILE, sheet_name="Test_Details_Per_Question")
        
        return JSONResponse(content=result_data_to_store.model_dump(exclude_none=True))
    except Exception as e:print(f"ASQ Submit Error: {e}");traceback.print_exc();raise HTTPException(status_code=500,detail=str(e))
    
class InitialEngagementResponse(BaseModel): initial_remark: Optional[str] = None; asq_solutions: Optional[str] = None; error: Optional[str] = None
@app.post("/chatbot/asq_initial_engagement", response_model=InitialEngagementResponse, summary="Get Initial Chatbot Remark & Solutions Post-ASQ (with RAG)")
async def chatbot_asq_initial_engagement_route(current_session: dict = Depends(get_current_session)):
    session_id = current_session["session_id"]
    if not redis_client: return InitialEngagementResponse(error="Dịch vụ Redis không khả dụng.")
    if not all([llm_global, retriever_global, ASQ_SOLUTION_PROMPT_GLOBAL]): return InitialEngagementResponse(error="Trợ lý AI chưa sẵn sàng.")
    asq_json_str = redis_client.get(f"asq_data:{session_id}")
    if not asq_json_str: return InitialEngagementResponse(error="Không tìm thấy kết quả ASQ-3 cho phiên này.")
    try:
        asq_data = ASQStoredResult(**json.loads(asq_json_str))
        task1_desc = "soạn lời chào thân thiện, nhận xét tổng quan ngắn gọn về ASQ-3, và mời phụ huynh đặt câu hỏi hoặc yêu cầu giải pháp chi tiết."
        task1_short = "lời chào và nhận xét tổng quan ban đầu"
        remark = await generate_llm_response_with_rag_for_asq(session_id,asq_data,task1_desc,task1_short)
        task2_desc = "đưa ra gợi ý hoạt động và lời khuyên cụ thể, dễ thực hiện tại nhà cho từng lĩnh vực phát triển dựa trên ASQ-3, tập trung vào lĩnh vực 'CHẬM' hoặc 'CÓ NGUY CƠ CHẬM'. Nếu bình thường, đưa ra lời khuyên chung."
        task2_short = "các giải pháp và hoạt động gợi ý chi tiết"
        solutions = await generate_llm_response_with_rag_for_asq(session_id,asq_data,task2_desc,task2_short)
        if remark: get_session_history(session_id).add_ai_message(remark)
        print(f"Generated initial engagement for session {session_id}")
        return InitialEngagementResponse(initial_remark=remark, asq_solutions=solutions)
    except Exception as e: print(f"Error in initial engagement {session_id}: {e}"); traceback.print_exc(); return InitialEngagementResponse(error=f"Lỗi tạo nhận xét ASQ: {e}")

class ChatMessageClient(BaseModel): sender: str; text: str
class ChatHistoryResponse(BaseModel): history: List[ChatMessageClient]; error: Optional[str] = None
@app.get("/chat/history", response_model=ChatHistoryResponse, summary="Get Chat History for Session")
async def get_chat_history_route(current_session: dict = Depends(get_current_session)):
    session_id = current_session["session_id"]
    if not redis_client: return ChatHistoryResponse(history=[], error="Dịch vụ lịch sử tạm thời không khả dụng.")
    try:
        hist_obj = get_session_history(session_id); raw_msgs = list(hist_obj.messages)
        recent_msgs = raw_msgs[-(MAX_HISTORY_TURNS*2):] if raw_msgs else []
        client_hist: List[ChatMessageClient] = []
        for msg_obj in recent_msgs:
            s,t = "unknown",""
            if isinstance(msg_obj,HumanMessage): s="user"; t=msg_obj.content
            elif isinstance(msg_obj,AIMessage): s="bot"; t=msg_obj.content
            elif hasattr(msg_obj,'type') and hasattr(msg_obj,'content') and msg_obj.type not in ["system"]: s=msg_obj.type; t=msg_obj.content
            if s!="unknown" and t: client_hist.append(ChatMessageClient(sender=s,text=t))
        print(f"Retrieved {len(client_hist)} history messages for session {session_id}.")
        return ChatHistoryResponse(history=client_hist)
    except Exception as e: print(f"Error retrieving history {session_id}: {e}"); traceback.print_exc(); return ChatHistoryResponse(history=[],error=f"Lỗi lấy lịch sử: {e}")

class ClearHistoryResponse(BaseModel): message: str; cleared_asq_too: bool
@app.post("/chat/history/clear", response_model=ClearHistoryResponse, summary="Clear Chat History & ASQ Data for Session")
async def clear_chat_history_route(current_session:dict=Depends(get_current_session), clear_asq:bool=Query(True)):
    session_id = current_session["session_id"]
    if not redis_client: raise HTTPException(status_code=503, detail="Redis unavailable.")
    try:
        hist_obj = get_session_history(session_id)
        if isinstance(hist_obj,RedisChatMessageHistory): hist_obj.clear(); print(f"Redis history for session {session_id} cleared.")
        elif isinstance(hist_obj,InMemoryChatMessageHistory) and hasattr(app.state,'in_mem_hist') and session_id in app.state.in_mem_hist: app.state.in_mem_hist[session_id].clear(); print(f"InMemory history for session {session_id} cleared.")
        asq_cleared = False
        if clear_asq:
            key_asq = f"asq_data:{session_id}"; del_count = redis_client.delete(key_asq)
            asq_cleared = del_count > 0; print(f"ASQ data for session {session_id} deleted: {asq_cleared}")
        return ClearHistoryResponse(message="History and related data cleared.", cleared_asq_too=asq_cleared)
    except Exception as e: print(f"Error clearing history {session_id}: {e}"); traceback.print_exc(); raise HTTPException(status_code=500,detail=f"Error clearing: {e}")

class ChatQuestionRequest(BaseModel): msg: str
@app.post("/ask", response_class=JSONResponse, summary="Ask the Chatbot a Question")
async def ask_bot_route(request_data: ChatQuestionRequest, current_session: dict = Depends(get_current_session)):
    session_id = current_session["session_id"]; msg = request_data.msg
    if not all([qa_chain_global,llm_global,retriever_global, QA_PROMPT_GLOBAL]): raise HTTPException(status_code=503,detail="Chatbot not ready.")
    if not msg.strip(): raise HTTPException(status_code=400,detail="Question empty.")
    print(f"\n--- Ask (session:{session_id}): {msg} ---")
    chat_history_obj = get_session_history(session_id); asq_guidance = ""
    if redis_client:
        asq_json=redis_client.get(f"asq_data:{session_id}")
        if asq_json:
            asq_data=ASQStoredResult(**json.loads(asq_json)); summary=asq_data.overall_summary
            age=asq_data.age_at_test_months; age_str=f"{age} tháng tuổi"if age is not None else"của trẻ"
            asq_guidance=(f"\n\nThông tin từ ASQ-3 của {age_str}: {summary}\nCân nhắc thông tin này.")
    try:
        with timer("RAG Doc"): docs:List[Document]=retriever_global.invoke(msg)
        with timer("RAG Ctx/Hist"):
            hist_msgs=list(chat_history_obj.messages); chat_hist_str=format_chat_history(hist_msgs,MAX_HISTORY_TURNS)
            partial_prompt = QA_PROMPT_GLOBAL.partial(current_date=current_date_global)
            base_template_str = partial_prompt.template
            # Initialize with a value to avoid UnboundLocalError if loop doesn't run
            # This part is tricky if input_variables can be empty or not fully present in template
            temp_template_for_token_calc = base_template_str 
            for var in QA_PROMPT_GLOBAL.input_variables:
                if var != "current_date": # current_date is already filled by partial
                    temp_template_for_token_calc = temp_template_for_token_calc.replace(f"{{{var}}}", "")
            base_t = llm_global.get_num_tokens(temp_template_for_token_calc)

            msg_t,hist_t,asq_t=(llm_global.get_num_tokens(s)for s in[msg,chat_hist_str,asq_guidance])
            avail_t=CTX_WINDOW-MAX_NEW_TOKENS-PROMPT_LENGTH_BUFFER-base_t-msg_t-hist_t-asq_t
            max_ctx_t=max(100,avail_t);ctx_t_count,ctx_docs=0,[]
            for d_item in docs:
                c,c_t=d_item.page_content,llm_global.get_num_tokens(d_item.page_content)
                if ctx_t_count+c_t<=max_ctx_t:ctx_docs.append(d_item);ctx_t_count+=c_t
                else:
                    rem=max_ctx_t-ctx_t_count
                    if rem>PROMPT_LENGTH_BUFFER/2:l=int(len(c)*(rem/c_t))if c_t>0 else 0;trunc=c[:l];ctx_docs.append(Document(page_content=trunc,metadata=d_item.metadata));ctx_t_count+=llm_global.get_num_tokens(trunc)
                    break
        with timer("LLM Chain"):resp_data=qa_chain_global.invoke({"chat_history":chat_hist_str,"context":ctx_docs,"question":msg,"asq_guidance_placeholder":asq_guidance, "current_date": current_date_global})
        resp_text=str(resp_data);cleaned_text=resp_text.strip()
        patterns=[r"<\|im_start\|>system.*?<\|im_end\|>",r"<\|im_start\|>user.*?<|im_end\|>",r"<\|im_end\|>",r"^\s*<\|im_start\|>assistant\s*",r"^\s*assistant:\s*",r"^\s*trả lời:\s*",r"\[/INST\]",]
        for p in patterns:cleaned_text=re.sub(p,"",cleaned_text,flags=re.I|re.S|re.M).strip()
        cleaned_text=re.sub(r"^\s*[-#*=_]{2,}\s*$","",cleaned_text,flags=re.M)
        cleaned_text=re.sub(r"(\s*#\s*){3,}|(#){3,}|(\s*-\s*){3,}"," ",cleaned_text)
        cleaned_text=re.sub(r"\s{2,}"," ",cleaned_text).strip()
        lines=cleaned_text.split('\n');res_lines=[];first=True
        for l_item in lines:
            s_l=l_item.strip()
            if not s_l or set(s_l)<= {"#","-","*","_","="}:continue
            if s_l.startswith(("* ","• ","+ ")):s_l="- "+s_l[2:].strip()
            if s_l.startswith("- ")and len(s_l)>2 and'a'<=s_l[2].lower()<='z':s_l="- "+s_l[2].upper()+s_l[3:]
            elif first and len(s_l)>0 and not s_l.startswith("-")and'a'<=s_l[0].lower()<='z':s_l=s_l[0].upper()+s_l[1:]
            res_lines.append(s_l)
            if s_l:first=False
            elif not res_lines or res_lines[-1]:first=True
        cleaned_text="\n".join(res_lines)
        if not cleaned_text:
             cleaned_text="Xin lỗi, tôi không thể đưa ra phản hồi vào lúc này."
        chat_history_obj.add_user_message(msg)
        chat_history_obj.add_ai_message(cleaned_text)
        return JSONResponse(content={"reply":cleaned_text})
    except HTTPException as http_exc:raise http_exc
    except Exception as e:print(f"Ask Error (session {session_id}): {e}");traceback.print_exc();raise HTTPException(status_code=500,detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Ensuring dirs..."); os.makedirs("./models",exist_ok=True)
    if VECTOR_DB_PATH and os.path.dirname(VECTOR_DB_PATH) and not os.path.exists(os.path.dirname(VECTOR_DB_PATH)): os.makedirs(os.path.dirname(VECTOR_DB_PATH),exist_ok=True)
    if ASQ_DATA_DIR and not os.path.exists(ASQ_DATA_DIR): os.makedirs(ASQ_DATA_DIR,exist_ok=True)
    if EXCEL_OUTPUT_DIR and not os.path.exists(EXCEL_OUTPUT_DIR): os.makedirs(EXCEL_OUTPUT_DIR, exist_ok=True)
    if not llm_global: print("CRITICAL: LLM not initialized.")
    print(f"POST to http://localhost:8000/token for session token")
    print(f"FastAPI server starting on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)