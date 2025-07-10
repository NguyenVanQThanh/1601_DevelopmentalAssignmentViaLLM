# === Imports ===
# Standard library imports for system operations, file handling, and data manipulation
import os
import traceback
import re
import json
import time
import psutil
from typing import List, Optional, Any, Dict
from contextlib import asynccontextmanager, contextmanager
import uuid
from datetime import datetime, timedelta, timezone
from underthesea import text_normalize

# FastAPI imports for building the API
from fastapi import FastAPI, Query, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

# Redis and LangChain imports for caching, chat history, and AI components
import redis
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_community.llms import Ollama
import ollama

# Custom embeddings for vector database
from custom_embeddings import BGEM3Embeddings

# Data processing and MongoDB imports
import pandas as pd
import pymongo
from bson import ObjectId
import joblib

from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np


# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# === Configuration ===
# Environment variables for model, paths, and system settings
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "vistral-assistant")  # Default LLM model name
BGE_M3_MODEL_PATH = os.getenv("BGE_M3_MODEL_PATH", "./models/bge-m3")  # Path to BGE-M3 model
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vectorstores/db_faiss_final")  # Path to FAISS vector database
CTX_WINDOW = int(os.getenv("CTX_WINDOW", "8192"))  # Context window size for LLM
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "1024"))  # Max new tokens for LLM output
stop_tokens_str = os.getenv("STOP_TOKENS_STR", "<|im_end|>,</s>,[/INST],###")  # Stop tokens for LLM
STOP_TOKENS = [token.strip() for token in stop_tokens_str.split(',')] if stop_tokens_str else ["<|im_end|>", "</s>"]  # Parsed stop tokens
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "3"))  # Max chat history turns to retain

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  # Redis host
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))  # Redis port
REDIS_DB_ASQ = int(os.getenv("REDIS_DB_ASQ", "2"))  # Redis DB for ASQ data
REDIS_DB_HISTORY = int(os.getenv("REDIS_DB_HISTORY", "3"))  # Redis DB for chat history
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "7200"))  # Session TTL in seconds

# ASQ data configuration
ASQ_DATA_DIR = os.getenv("ASQ_DATA_DIR", "./ASQ3API/data")  # Directory for ASQ data
DEFAULT_ASQ_FILENAME = os.getenv("DEFAULT_ASQ_FILENAME", "18month.json")  # Default ASQ JSON file
ASQ_JSON_FILE = os.path.join(ASQ_DATA_DIR, DEFAULT_ASQ_FILENAME) if DEFAULT_ASQ_FILENAME else None  # Full path to ASQ JSON file

# MongoDB configuration
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")  # MongoDB connection URI
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "asq_app_db")  # MongoDB database name

# JWT authentication configuration
SECRET_KEY = os.getenv("SECRET_KEY", "please-set-a-strong-secret-key-in-your-env-file")  # Secret key for JWT
if SECRET_KEY == "please-set-a-strong-secret-key-in-your-env-file":
    print("WARNING: Default SECRET_KEY is being used. Please set a strong, unique SECRET_KEY in your .env file for security!")
ALGORITHM = "HS256"  # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))  # Token expiration time

# === Global Variables (Managed by Lifespan) ===
# Global variables to store Redis client, LLM, vector DB, and other components
redis_client: Optional[redis.Redis] = None
llm_global: Optional[Ollama] = None
vector_db_global: Optional[FAISS] = None
retriever_global: Any = None
QA_PROMPT_GLOBAL: Optional[PromptTemplate] = None
ASQ_SOLUTION_PROMPT_GLOBAL: Optional[PromptTemplate] = None
default_asq_questionnaire_rules: dict = {}
current_date_global: str = datetime.now().strftime("%Y-%m-%d")  # Current date for prompts
mongo_client_global: Optional[pymongo.MongoClient] = None
db: Optional[pymongo.database.Database] = None
scaler_global: Optional[Any] = None  # Scaler for OLA model
pca_global: Optional[Any] = None  # PCA for OLA model
pool_classifiers_global: Optional[List[Any]] = None  # Pool classifiers for OLA model
ola_model_global: Optional[Any] = None  # OLA model
OLA_INITIAL_REMARK_PROMPT_GLOBAL: Optional[PromptTemplate] = None  # Prompt for OLA initial remark
OLLAMA_CLARIFICATION_MODEL = os.getenv("OLLAMA_CLARIFICATION_MODEL", "vietnamese-llm")  # Model for clarification questions

# === Pydantic Models ===
# Models for request/response validation and data structures
class Answer(BaseModel):
    id: int  # Question ID
    answer: str  # Answer text

class ASQSectionResultDetail(BaseModel):
    display_name: str  # Display name of the section
    total_score: float  # Total score for the section
    status: str  # Status (e.g., normal, delayed)
    cutoff: float  # Cutoff score for the section
    monitor: float  # Monitor cutoff score
    answers_processed: List[Answer]  # Processed answers for the section

class ASQStoredResult(BaseModel):
    session_id: str  # Session ID
    age_at_test_months: Optional[int] = None  # Age of child in months
    questionnaire_title: Optional[str] = None  # Title of the ASQ questionnaire
    overall_summary: str  # Summary of ASQ results
    sections: Dict[str, ASQSectionResultDetail]  # Section-wise results

class ChildInfoSubmitted(BaseModel):
    fullName: Optional[str] = None  # Child's full name
    birthDate: Optional[str] = None  # Child's birth date
    childAgeInDays: Optional[int] = None  # Child's age in days
    location: Optional[str] = None  # Location
    gender: Optional[str] = None  # Gender
    pre_birth: Optional[str] = None  # Pre-birth information
    pre_result: Optional[str] = None  # Pre-test result
    result: Optional[str] = None  # Test result
    resultDate: Optional[str] = None  # Date of result
    hospital: Optional[str] = None  # Hospital name
    doctor: Optional[str] = None  # Doctor's name
    pre_test: Optional[str] = None  # Pre-test information

class ParentInfoSubmitted(BaseModel):
    parentFullName: Optional[str] = None  # Parent's full name
    phone: Optional[str] = None  # Parent's phone number
    email: Optional[str] = None  # Parent's email
    address: Optional[str] = None  # Parent's address
    relationship: Optional[str] = None  # Relationship to child
    place: Optional[str] = None  # Place information

class ASQSubmissionPayload(BaseModel):
    age_at_test_months: Optional[int] = None  # Age at test in months
    questionnaire_title: Optional[str] = None  # Questionnaire title
    communication: Optional[List[Answer]] = None  # Communication section answers
    gross_motor: Optional[List[Answer]] = None  # Gross motor section answers
    fine_motor: Optional[List[Answer]] = None  # Fine motor section answers
    problem_solving: Optional[List[Answer]] = None  # Problem-solving section answers
    personal_social: Optional[List[Answer]] = None  # Personal-social section answers
    child_information: Optional[ChildInfoSubmitted] = None  # Child information
    parent_information: Optional[ParentInfoSubmitted] = None  # Parent information

class InitialEngagementResponse(BaseModel):
    initial_remark: Optional[str] = None  # Initial chatbot remark
    asq_solutions: Optional[str] = None  # ASQ solutions and advice
    error: Optional[str] = None  # Error message, if any

class ChatMessageClient(BaseModel):
    sender: str  # Sender type (user or bot)
    text: str  # Message text

class ChatHistoryResponse(BaseModel):
    history: List[ChatMessageClient]  # List of chat messages
    error: Optional[str] = None  # Error message, if any

class ClearHistoryResponse(BaseModel):
    message: str  # Confirmation message
    cleared_asq_too: bool  # Whether ASQ data was cleared

class ChatQuestionRequest(BaseModel):
    msg: str  # User's question

class TokenResponse(BaseModel):
    access_token: str  # JWT access token
    token_type: str  # Token type (bearer)
    session_id: str  # Session ID

class UserFeedbackRequest(BaseModel):
    fullName: Optional[str] = Field(None)  # User's full name
    phone: Optional[str] = Field(None)  # User's phone number
    opinion: str = Field(..., min_length=1)  # User's feedback opinion
    rate: int = Field(..., ge=1, le=5)  # Rating (1-5)

    @field_validator('phone')
    @classmethod
    def validate_vietnamese_phone(cls, v: Optional[str]) -> Optional[str]:
        # Validate Vietnamese phone number format
        if v is not None:
            if not re.match(r"^(0[35789])([0-9]{8})$", v):
                raise ValueError('Invalid Vietnamese phone number format.')
        return v

class UserFeedbackResponse(BaseModel):
    feedback_id: str  # Feedback ID
    fullName: Optional[str] = None  # User's full name
    phone: Optional[str] = None  # User's phone number
    opinion: str  # Feedback opinion
    rate: int  # Rating
    submittedAt: datetime  # Submission timestamp
    sessionId: Optional[str] = None  # Session ID
    linked_to_parent_id: Optional[str] = None  # Linked parent ID

class OLAPredictionInput(BaseModel):
    # Input fields for OLA prediction model
    ChamNoi: float
    CoLap: float
    ChoiChucNang: float
    ChoiGiaVo: float
    HanhViLapLai: float
    KyNangGiaoTiepSom: float
    ChoiLuanPhien: float
    BatChuoc: float
    PhanUngTenGoi: float
    ChiTro: float
    TiepXucMat: float

class ASDTestPayload(BaseModel):
    userInfo: ChildInfoSubmitted  # User information
    answers: OLAPredictionInput  # OLA prediction inputs
    questionDetails: List[Dict[str, Any]]  # Question details

class OLAPredictionResult(BaseModel):
    prediction: int  # Prediction result (0 or 1)
    probability: float  # Prediction probability

class OLAStoredResult(BaseModel):
    session_id: str  # Session ID
    prediction_timestamp: datetime  # Prediction timestamp
    input_data: OLAPredictionInput  # Input data for prediction
    prediction_result: OLAPredictionResult  # Prediction result

class OLAPredictionResponse(BaseModel):
    prediction: int  # Prediction result
    probability_class_1: float  # Probability of class 1
    initial_remark: str  # Initial remark for prediction

class ColumnDropper(BaseEstimator, TransformerMixin):
    def __init__(self, columns, feature_names=None):
        self.columns = columns
        self.feature_names = feature_names

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            return X.drop(columns=self.columns, errors='ignore')
        elif isinstance(X, np.ndarray):
            if self.feature_names is None or X.shape[1] != len(self.feature_names):
                raise ValueError("ColumnDropper: mismatch or missing feature names.")
            df = pd.DataFrame(X, columns=self.feature_names)
            return df.drop(columns=self.columns, errors='ignore').values
        else:
            raise ValueError("Unsupported input type for ColumnDropper.")
# === Lifespan Manager ===
@asynccontextmanager
async def lifespan_manager(app_param: FastAPI):
    # Global variables for Redis, LLM, vector DB, and other components
    global redis_client, llm_global, vector_db_global, retriever_global
    global QA_PROMPT_GLOBAL, ASQ_SOLUTION_PROMPT_GLOBAL, default_asq_questionnaire_rules
    global mongo_client_global, db, scaler_global, pca_global, pool_classifiers_global, ola_model_global
    global OLA_INITIAL_REMARK_PROMPT_GLOBAL, current_date_global
    print("INFO: Application startup sequence initiated...")

    # Create necessary directories
    try:
        print("INFO: Ensuring required directories exist...")
        os.makedirs("./models", exist_ok=True)
        if BGE_M3_MODEL_PATH and os.path.dirname(BGE_M3_MODEL_PATH) and os.path.dirname(BGE_M3_MODEL_PATH) != '.':
            os.makedirs(os.path.dirname(BGE_M3_MODEL_PATH), exist_ok=True)
        if VECTOR_DB_PATH and os.path.dirname(VECTOR_DB_PATH) and os.path.dirname(VECTOR_DB_PATH) != '.':
            os.makedirs(os.path.dirname(VECTOR_DB_PATH), exist_ok=True)
        if ASQ_DATA_DIR:
            os.makedirs(ASQ_DATA_DIR, exist_ok=True)
    except Exception as e_dir:
        print(f"ERROR: Could not create directories: {e_dir}")

    # Initialize MongoDB connection
    try:
        print(f"INFO: Attempting MongoDB connection: {MONGO_URI}")
        mongo_client_global = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client_global.admin.command('ping')
        db = mongo_client_global[MONGO_DB_NAME]
        print(f"SUCCESS: Connected to MongoDB. Database: '{db.name}'")
        if db is not None:
            print("INFO: Ensuring MongoDB indexes...")
            # Create indexes for efficient querying
            db.user_feedbacks.create_index([("phone", pymongo.ASCENDING)], name="idx_feedback_phone", background=True)
            db.user_feedbacks.create_index([("submittedAt", pymongo.DESCENDING)], name="idx_feedback_submitted_at", background=True)
            db.asq_submissions.create_index([("sessionId", pymongo.ASCENDING)], name="idx_asqsub_session", background=True)
            db.asq_submissions.create_index([("submissionTimestamp", pymongo.DESCENDING)], name="idx_asqsub_timestamp", background=True)
            db.asq_submissions.create_index([("parentInformation.phone", pymongo.ASCENDING)], name="idx_asqsub_parent_phone", background=True)
            db.asd_predictions.create_index([("sessionId", pymongo.ASCENDING)], name="idx_asdpred_session", background=True)
            db.asd_predictions.create_index([("predictionTimestamp", pymongo.DESCENDING)], name="idx_asdpred_timestamp", background=True)
            print("INFO: MongoDB indexes checked/created.")
    except Exception as e_mongo:
        print(f"CRITICAL: MongoDB setup failed: {e_mongo}")
        db = None
        mongo_client_global = None

    # Initialize Redis connection
    try:
        print(f"INFO: Attempting Redis connection: {REDIS_HOST}:{REDIS_PORT}")
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_ASQ, decode_responses=True, socket_connect_timeout=5)
        redis_client.ping()
        print(f"SUCCESS: Connected to Redis for ASQ Data (DB {REDIS_DB_ASQ}).")
    except Exception as e_redis:
        print(f"CRITICAL: Redis connection failed: {e_redis}.")
        redis_client = None

    # Load default ASQ questionnaire rules
    if ASQ_JSON_FILE and os.path.exists(ASQ_JSON_FILE):
        try:
            with open(ASQ_JSON_FILE, "r", encoding="utf-8") as f:
                default_asq_questionnaire_rules.update(json.load(f))
            print("INFO: Default ASQ rules loaded.")
        except Exception as e_asq_rules:
            print(f"WARNING: Could not load default ASQ file: {e_asq_rules}")
    elif ASQ_JSON_FILE:
        print(f"WARNING: Default ASQ file {ASQ_JSON_FILE} not found.")

    # Initialize AI components (LLM, VectorDB, Prompts)
    print("INFO: Initializing AI components (LLM, VectorDB, Prompts)...")
    try:
        llm_global = _internal_load_llm()  # Load LLM model
        vector_db_global = _internal_load_vector_db()  # Load vector database

        if vector_db_global:
            # Initialize retriever for vector database
            retriever_global = vector_db_global.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
        else:
            retriever_global = None
            print("WARNING: VectorDB global instance not initialized, retriever will be None.")

        # Define QA prompt template for general chatbot responses
        qa_template_str = """<|im_start|>system
**Ngày hiện tại:** {current_date}
Bạn là trợ lý AI về sức khỏe – tâm thần nhi khoa của Phòng Khám Tâm Lý Nhi Đồng. Luôn trả lời bằng **tiếng Việt**.
CHỈ SỬ DỤNG thông tin dưới đây khi có câu hỏi về việc đặt lịch, tư vấn hoặc liên hệ với phòng khám:
Phòng Khám Tâm Lý Nhi Đồng 
• Zalo/ĐT: 0981502721
• Địa chỉ: 625 Hậu Giang, Q6, TP.HCM
TUYỆT ĐỐI KHÔNG cung cấp các địa chỉ khác ngoài thông tin trên.
**NỘI DUNG CÂU HỎI:** Nếu câu hỏi không rõ ràng (không dấu, sai chính tả hoặc có từ viết tắt), hãy yêu cầu làm rõ hoặc cung cấp thêm thông tin. Tập trung phân tích nội dung câu hỏi hiện tại. 
**ĐỘ TUỔI:** Mọi khuyến nghị phải phù hợp chính xác với tuổi trẻ; nếu tuổi chưa rõ hãy hỏi lại.
Luôn trả lời bằng **tiếng Việt**
**Context**:
{context}
**Kết quả bài test ASQ-3 hoặc ASD:**
{session_context}
Hướng dẫn trả lời
1. ĐẶC BIỆT ưu tiên **Context** và kiến thức, không bịa.
2. Trả lời ngắn gọn, gạch đầu dòng khi cần.
3. Thiếu dữ liệu thì xin lỗi và báo không đủ thông tin.
4. Câu văn mạch lạc, giọng điệu thân thiện, cảm thông, an ủi khi câu trả lời có tin xấu.
5. Trích dẫn ngắn, không chép nguyên văn dài.
6. Tham chiếu lịch sử để cần giữ mạch nhưng cần tập trung vào câu hỏi hiện tại.
7. Luôn đề cập độ tuổi trong câu hỏi.

**Lịch sử**:
{chat_history}
<|im_end|>
<|im_start|>user
{question}<|im_end|>
<|im_start|>assistant
"""
        QA_PROMPT_GLOBAL = PromptTemplate(
            template=qa_template_str,
            input_variables=["chat_history", "context", "question", "current_date","session_context"]
        )

        # Define ASQ solution prompt template
        asq_solution_template_str = """<|im_start|>system
Bạn là trợ lý AI về sức khỏe – tâm thần nhi khoa của Phòng Khám Tâm Lý Nhi Đồng. Nhiệm vụ của bạn là đưa ra lời khuyên và gợi ý dựa trên thông tin sau.
Luôn trả lời bằng tiếng Việt, ngôn ngữ thân thiện, dễ hiểu.

--- THÔNG TIN ĐẦU VÀO ---
**Thông tin trẻ và kết quả ASQ-3:**
- Tuổi: {age_details}
- Tóm tắt kết quả ASQ-3: {asq_summary}
- Chi tiết các lĩnh vực có thể cần chú ý dựa trên điểm số:
{asq_areas_of_concern}

**Thông tin chuyên ngành tham khảo (từ tài liệu):**
<rag_context_start>
{rag_context}
<rag_context_end>
--- KẾT THÚC THÔNG TIN ĐẦU VÀO ---

--- YÊU CẦU CỤ THỂ CHO BẠN (TRỢ LÝ AI) ---
**Nhiệm vụ của bạn là:** {task_description}

**QUAN TRỌNG KHI CÓ KẾT QUẢ "CHẬM RÕ RỆT":**
- Nếu có bất kỳ lĩnh vực nào là "CHẬM RÕ RỆT", hãy đặt ưu tiên cao nhất cho việc khuyên phụ huynh đưa trẻ đi đánh giá chuyên sâu ngay lập tức. Đây phải là thông điệp chính và được nhấn mạnh nhất.
- Các gợi ý hoạt động tại nhà cho lĩnh vực "CHẬM RÕ RỆT" chỉ nên mang tính hỗ trợ rất cơ bản, tạm thời trong lúc chờ chuyên gia, và phải luôn đi kèm cảnh báo không thay thế được ý kiến chuyên môn. Hạn chế các hoạt động phức tạp cho những lĩnh vực này.

**Yêu cầu định dạng cho phần gợi ý hoạt động và lời khuyên (NẾU được yêu cầu trong task_description):**
- Mỗi gợi ý chính (ví dụ: "Hoạt động tại nhà", "Lời khuyên chung") nên bắt đầu bằng một tiêu đề được **in đậm**.
- Các mục con trong mỗi gợi ý nên được liệt kê bằng gạch đầu dòng (-).
--- KẾT THÚC YÊU CẦU ---
<|im_end|>
<|im_start|>user
Dựa vào các thông tin và yêu cầu trên, vui lòng {task_description_short}.
<|im_end|>
<|im_start|>assistant
"""
        ASQ_SOLUTION_PROMPT_GLOBAL = PromptTemplate(
            template=asq_solution_template_str,
            input_variables=["age_details", "asq_summary", "asq_areas_of_concern", "task_description", "rag_context", "task_description_short"]
        )

        # Define OLA initial remark prompt template
        ola_remark_template_str = """<|im_start|>system
Bạn là trợ lý AI chuyên về tâm lý nhi khoa của Phòng Khám Tâm Lý Nhi Đồng. Nhiệm vụ của bạn là soạn một lời nhận xét ban đầu dựa trên kết quả sàng lọc nguy cơ tự kỷ.
Luôn trả lời bằng tiếng Việt, giọng điệu cực kỳ **thân thiện, cảm thông và trấn an**.

--- THÔNG TIN KẾT QUẢ SÀNG LỌC ASD ---
- Kết quả tóm tắt: {ola_summary}
- Điểm số chi tiết của trẻ: {ola_input_details}

--- THÔNG TIN THAM KHẢO (NẾU CÓ) ---
<rag_context_start>
{rag_context}
<rag_context_end>

--- YÊU CẦU ---
1.  **QUAN TRỌNG NHẤT:** Bắt đầu bằng việc trấn an phụ huynh. Luôn nhấn mạnh rằng đây **CHỈ LÀ SÀNG LỌC**, **KHÔNG PHẢI LÀ CHẨN ĐOÁN**.
2.  **Nếu kết quả là "Có nguy cơ":**
    - Nhẹ nhàng thông báo kết quả.
    - **Mạnh mẽ và rõ ràng** khuyên phụ huynh nên đưa trẻ đến gặp chuyên gia tâm lý nhi hoặc bác sĩ chuyên khoa để được đánh giá chuyên sâu. Đây là bước quan trọng nhất.
    - Tuyệt đối không đưa ra bất kỳ kết luận hay chẩn đoán nào.
3.  **Nếu kết quả là "Không có nguy cơ":**
    - Chúc mừng phụ huynh.
    - Khuyến khích họ tiếp tục theo dõi sự phát triển của con và có thể thực hiện lại các bài sàng lọc định kỳ khi con lớn hơn.
4.  Kết thúc bằng việc mời phụ huynh đặt câu hỏi thêm để bạn có thể tư vấn chi tiết hơn về các hoạt động hỗ trợ hoặc bất kỳ thắc mắc nào khác.
5.  Câu trả lời phải ngắn gọn, súc tích, dễ hiểu.
<|im_end|>
<|im_start|>user
Dựa vào kết quả sàng lọc ASD trên, hãy soạn một lời nhận xét ban đầu thật ngắn gọn và cảm thông để gửi cho phụ huynh.
<|im_end|>
<|im_start|>assistant
"""
        OLA_INITIAL_REMARK_PROMPT_GLOBAL = PromptTemplate(
            template=ola_remark_template_str,
            input_variables=["ola_summary", "ola_probability_percent", "ola_input_details", "rag_context"])

        # Check if all AI components are initialized
        if all([llm_global, retriever_global, QA_PROMPT_GLOBAL, ASQ_SOLUTION_PROMPT_GLOBAL]):
            print("INFO: All AI components (LLM, Retriever, Prompts) initialized successfully via lifespan.")
        else:
            missing = [name for name, var in [("LLM", llm_global), ("Retriever", retriever_global), ("QA_PROMPT", QA_PROMPT_GLOBAL), ("ASQ_PROMPT", ASQ_SOLUTION_PROMPT_GLOBAL)] if var is None]
            print(f"WARNING: Some AI components failed to initialize: {', '.join(missing)}")

        # Load OLA model components
        try:
            models_path = "./models/ola_usage"
            scaler_global = joblib.load(os.path.join(models_path, 'scaler.joblib'))
            pca_global = joblib.load(os.path.join(models_path, 'pca.joblib'))
            pool_classifiers_global = joblib.load(os.path.join(models_path, 'pool_classifiers.joblib'))
            ola_model_global = joblib.load(os.path.join(models_path, 'ola_model.joblib'))
            print("SUCCESS: OLA model components loaded successfully from ./models.")
        except FileNotFoundError as e:
            print(f"CRITICAL ERROR: One or more OLA model files not found in {models_path}: {e}")
            scaler_global = pca_global = pool_classifiers_global = ola_model_global = None
        except Exception as e_ola_load:
            print(f"CRITICAL ERROR: Failed to load OLA model components from {models_path}: {e_ola_load}")
            scaler_global = pca_global = pool_classifiers_global = ola_model_global = None

        # Final check for AI components
        if all([llm_global, retriever_global, QA_PROMPT_GLOBAL, ASQ_SOLUTION_PROMPT_GLOBAL, scaler_global, ola_model_global]):
            print("INFO: All AI components (LLM, Retriever, Prompts, OLA) initialized successfully via lifespan.")
        else:
            missing = [name for name, var in [("LLM", llm_global), ("Retriever", retriever_global), ("QA_PROMPT", QA_PROMPT_GLOBAL),
                                             ("ASQ_PROMPT", ASQ_SOLUTION_PROMPT_GLOBAL), ("Scaler", scaler_global), ("OLA", ola_model_global)]
                       if var is None]
            print(f"WARNING: Some AI components failed to initialize: {', '.join(missing)}")

    except HTTPException as e_http_ai:
        print(f"CRITICAL ERROR during AI component initialization (HTTPException caught in lifespan): {e_http_ai.detail}")
        llm_global = vector_db_global = retriever_global = QA_PROMPT_GLOBAL = ASQ_SOLUTION_PROMPT_GLOBAL = None
        scaler_global = pca_global = pool_classifiers_global = ola_model_global = None
    except Exception as e_ai:
        print(f"CRITICAL ERROR - AI Components Init (lifespan general exception): {e_ai}")
        traceback.print_exc()
        llm_global = vector_db_global = retriever_global = QA_PROMPT_GLOBAL = ASQ_SOLUTION_PROMPT_GLOBAL = None
        scaler_global = pca_global = pool_classifiers_global = ola_model_global = None
    try:
        ollama.list()  # Test Ollama connection
        print(f"INFO: Ollama is ready with clarification model {OLLAMA_CLARIFICATION_MODEL}")
        # Attempt to load clarification model
        ollama.show(OLLAMA_CLARIFICATION_MODEL)
    except Exception as e:
        print(f"WARNING: Failed to connect to Ollama or load clarification model {OLLAMA_CLARIFICATION_MODEL}: {e}")
    
    print("INFO: Application startup sequence complete.")
    yield

    # Shutdown logic
    print("INFO: Application shutdown sequence initiated (lifespan)...")
    print("INFO: Application has completed shutdown.")

# Initialize FastAPI app with lifespan manager
app_lifespan = FastAPI(title="ASQ & Chatbot API", version="1.3.0", lifespan=lifespan_manager)
# Add CORS middleware for cross-origin requests
app_lifespan.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tamlynhidongsupport.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# === Helper Functions ===
def _internal_load_llm() -> Optional[Ollama]:
    # Load and initialize the LLM model
    try:
        llm_i = Ollama(model=LLM_MODEL_NAME, temperature=0.3, stop=STOP_TOKENS)
        llm_i.invoke("Hello", max_tokens=5)
        print(f"SUCCESS: Model '{LLM_MODEL_NAME}' ready.")
        return llm_i
    except Exception as e:
        print(f"ERROR: LLM init failed: {e}")
        return None

def _internal_load_vector_db() -> Optional[FAISS]:
    # Load FAISS vector database
    for f_name in ("index.faiss", "index.pkl"):
        path_to_check = os.path.join(VECTOR_DB_PATH, f_name)
        if not os.path.exists(path_to_check):
            print(f"ERROR: VectorDB file {path_to_check} missing.")
            return None
    try:
        emb = BGEM3Embeddings(BGE_M3_MODEL_PATH)
        db_faiss_local = FAISS.load_local(VECTOR_DB_PATH, emb, allow_dangerous_deserialization=True)
        if db_faiss_local.index.ntotal == 0:
            print("ERROR: Vector store is empty.")
            return None
        print(f"SUCCESS: Vector DB loaded with {db_faiss_local.index.ntotal} items.")
        return db_faiss_local
    except Exception as e:
        print(f"ERROR: VectorDB load failed: {e}")
        return None

def get_status_code(status_text: str) -> float:
    # Convert status text to a numerical score
    if "CHẬM RÕ RỆT" in status_text.upper():
        return 0.0
    elif "CÓ NGUY CƠ CHẬM" in status_text.upper():
        return 0.5
    elif "PHÁT TRIỂN BÌNH THƯỜNG" in status_text.upper():
        return 1.0
    return -1.0

def get_asq_questionnaire_rules(title: Optional[str] = None, age_months: Optional[int] = None) -> dict:
    # Retrieve ASQ questionnaire rules based on title or age
    if title and os.path.isdir(ASQ_DATA_DIR):
        month_str = "".join(filter(str.isdigit, title.split("m")[0])) if title and "m" in title else ""
        if month_str:
            f_path = os.path.join(ASQ_DATA_DIR, f"{month_str}month.json")
            if os.path.exists(f_path):
                try:
                    with open(f_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading specific ASQ rules {f_path}: {e}")
    if age_months and os.path.isdir(ASQ_DATA_DIR):
        age_days = age_months * 30.44
        for fname in sorted(os.listdir(ASQ_DATA_DIR)):
            if fname.endswith(".json"):
                f_path = os.path.join(ASQ_DATA_DIR, fname)
                try:
                    with open(f_path, "r", encoding="utf-8") as f:
                        r_data = json.load(f)
                        age_info = r_data.get("age", {}).get("range_in_days", {})
                        min_d, max_d = age_info.get("min_days"), age_info.get("max_days")
                        if min_d is not None and max_d is not None and min_d <= age_days <= max_d:
                            return r_data
                except Exception as e_rule_file:
                    print(f"Warning: Could not parse or check ASQ rule file {f_path}: {e_rule_file}")
    if not default_asq_questionnaire_rules:
        print("WARNING: Requested ASQ rules but no specific or default rules are loaded.")
    return default_asq_questionnaire_rules

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # Create JWT access token
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_session(token: str = Depends(oauth2_scheme)) -> dict:
    # Validate and extract session information from JWT token
    cred_exc = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        session_id: Optional[str] = payload.get("sub")
        if session_id is None:
            raise cred_exc
        return {"session_id": session_id, "token_payload": payload}
    except JWTError:
        raise cred_exc
    except Exception:
        raise cred_exc

@contextmanager
def timer(description: str):
    # Context manager to measure execution time
    start = time.time()
    yield
    print(f"{description}: {(time.time() - start):.3f}s")

def get_memory_usage() -> float:
    # Get current memory usage in MB
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

def get_session_history(session_id: str) -> Any:
    # Retrieve chat history for a session (Redis or in-memory)
    if redis_client:
        return RedisChatMessageHistory(
            session_id=session_id,
            url=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_HISTORY}",
            ttl=SESSION_TTL_SECONDS
        )
    else:
        if not hasattr(app_lifespan.state, 'in_mem_hist'):
            app_lifespan.state.in_mem_hist = {}
        if session_id not in app_lifespan.state.in_mem_hist:
            app_lifespan.state.in_mem_hist[session_id] = InMemoryChatMessageHistory()
        return app_lifespan.state.in_mem_hist[session_id]

def apply_scoring_logic(section: str, answers: List[Answer], q_data: dict) -> List[Answer]:
    # Apply scoring logic for ASQ answers based on questionnaire rules
    s_data = q_data.get("question", {}).get(section, {})
    note = s_data.get("scoring_note")
    if not note:
        return answers
    ans_dict = {a.id: a for a in answers if isinstance(a, Answer)}
    cond = note.get("condition", {})
    act = note.get("action", {})
    if not cond or not act or "question_id" not in cond or "question_id" not in act:
        return answers
    cond_ans = ans_dict.get(cond["question_id"])
    if cond_ans and cond_ans.answer in cond.get("values", []) and act["question_id"] in ans_dict:
        ans_dict[act["question_id"]].answer = act.get("set_value")
    return list(ans_dict.values())

def calculate_score(answers: List[Answer]) -> float:
    # Calculate score based on answers
    m = {"Có": 10, "Thỉnh Thoảng": 5, "Chưa": 0}
    return sum(m.get(a.answer, 0) for a in answers if isinstance(a, Answer))

def determine_status(score: float, cutoff: float, monitor: float) -> str:
    # Determine status based on score, cutoff, and monitor values
    if cutoff == 0 and monitor == 0:
        return "Không áp dụng điểm chuẩn"
    if score < cutoff:
        return "CHẬM RÕ RỆT (Cần đánh giá chuyên sâu)"
    if score <= monitor:
        return "CÓ NGUY CƠ CHẬM (Cần theo dõi sát)"
    return "PHÁT TRIỂN BÌNH THƯỜNG"

def replace_image_placeholders(data: dict) -> dict:
    # Replace placeholder image filepaths in ASQ data
    t2p = {
        "2m Questionnaire": "image2_", "4m Questionnaire": "image4_", "6m Questionnaire": "image6_",
        "8m Questionnaire": "image8_", "9m Questionnaire": "image9_", "10m Questionnaire": "image10_",
        "12m Questionnaire": "image12_", "14m Questionnaire": "image14_", "16m Questionnaire": "image16_",
        "18m Questionnaire": "image18_", "20m Questionnaire": "image20_", "22m Questionnaire": "image22_",
        "24m Questionnaire": "image24_", "27m Questionnaire": "image27_", "30m Questionnaire": "image30_",
        "33m Questionnaire": "image33_", "36m Questionnaire": "image36_", "42m Questionnaire": "image42_",
        "48m Questionnaire": "image48_", "54m Questionnaire": "image54_", "60m Questionnaire": "image60_"
    }
    t = data.get("age", {}).get("title")
    p = t2p.get(t)
    if not p:
        return data
    for sv_key, sv_value in data.get("question", {}).items():
        if isinstance(sv_value, dict) and "questions" in sv_value:
            c = 1
            for qi in sv_value.get("questions", []):
                if isinstance(qi, dict) and qi.get("image_filepath") == "image_placeholder.png":
                    qi["image_filepath"] = f"{p}{c}.png"
                    c += 1
    return data

async def generate_llm_response_with_rag_for_asq(session_id: str, asq_data: ASQStoredResult, task_description: str, task_description_short: str) -> str:
    # Generate LLM response for ASQ with RAG (Retrieval-Augmented Generation)
    if not all([llm_global, retriever_global, ASQ_SOLUTION_PROMPT_GLOBAL]):
        raise HTTPException(status_code=503, detail="AI components for ASQ advice not ready.")
    
    # Prepare age details and areas of concern
    age_details = f"{asq_data.age_at_test_months} tháng tuổi" if asq_data.age_at_test_months is not None else "không rõ độ tuổi"
    areas_concern_list = [
        f"- Lĩnh vực {s.display_name}: {s.status} (điểm {s.total_score:.0f})"
        for s_key, s in asq_data.sections.items() if "CHẬM" in s.status.upper()
    ]
    asq_areas_str = "\n".join(areas_concern_list) if areas_concern_list else "Không có lĩnh vực nào được đánh giá là chậm hoặc có nguy cơ chậm rõ rệt từ kết quả điểm số."

    # Construct RAG query
    rag_query_parts = [
        f"gợi ý can thiệp và hoạt động cho trẻ {age_details} dựa trên kết quả ASQ sau: {asq_data.overall_summary}"
    ]
    if areas_concern_list:
        rag_query_parts.append(
            f"Đặc biệt tập trung vào các lĩnh vực: {', '.join(s.split(':')[0].replace('Lĩnh vực ','') for s in areas_concern_list).strip(', ')}."
        )
    rag_query = " ".join(rag_query_parts)

    # Retrieve relevant documents using RAG
    with timer(f"RAG for ASQ Task (session {session_id})"):
        rag_docs: List[Document] = retriever_global.invoke(rag_query)
    rag_context_str = "\n\n---\n\n".join([doc.page_content for doc in rag_docs]) if rag_docs else "Không tìm thấy thông tin chuyên ngành bổ sung từ tài liệu."

    # Truncate RAG context if too long
    max_rag_ctx_tokens = CTX_WINDOW // 3
    if not llm_global:
        raise HTTPException(status_code=503, detail="LLM component not ready.")
    current_rag_tokens = llm_global.get_num_tokens(rag_context_str)
    if current_rag_tokens > max_rag_ctx_tokens:
        ratio = max_rag_ctx_tokens / current_rag_tokens if current_rag_tokens > 0 else 0
        estimated_len = int(len(rag_context_str) * ratio)
        rag_context_str = rag_context_str[:estimated_len]
        print(f"Truncated RAG context for ASQ to approx. {llm_global.get_num_tokens(rag_context_str)} tokens.")

    # Generate LLM response
    final_prompt_for_llm = ASQ_SOLUTION_PROMPT_GLOBAL.format(
        age_details=age_details,
        asq_summary=asq_data.overall_summary,
        asq_areas_of_concern=asq_areas_str,
        task_description=task_description,
        rag_context=rag_context_str,
        task_description_short=task_description_short
    )
    with timer(f"LLM for ASQ Task '{task_description_short}'"):
        raw_response = llm_global.invoke(final_prompt_for_llm)
    
    # Clean up response
    cleaned_response = raw_response.strip()
    all_stop_tokens_for_asq_clean = STOP_TOKENS + ["<|im_start|>", "<|im_end|>"]
    for token_to_remove in all_stop_tokens_for_asq_clean:
        cleaned_response = cleaned_response.replace(token_to_remove, "")
    return re.sub(r"^\s*assistant:\s*", "", cleaned_response, flags=re.I).strip()

async def generate_llm_response_for_ola(session_id: str, asd_predict_data: OLAStoredResult) -> str:
    # Generate LLM response for OLA prediction with RAG
    if not all([llm_global, retriever_global, OLA_INITIAL_REMARK_PROMPT_GLOBAL]):
        return "Xin lỗi, hiện tôi chưa thể đưa ra nhận xét. Bạn có câu hỏi nào khác không ạ?"

    try:
        # Prepare OLA summary and input details
        ola_summary = "Có nguy cơ" if asd_predict_data.prediction_result.prediction == 1 else "Không có nguy cơ"
        prob_percent = asd_predict_data.prediction_result.probability * 100
        friendly_names = {
            "ChamNoi": "Chậm nói", "CungNhac": "Cứng nhắc", "CoLap": "Cô lập",
            "HanhViLapLai": "Hành vi lặp lại", "KyNangGiaoTiepSom": "Giao tiếp sớm",
            "ChoiLuanPhien": "Chơi luân phiên", "PhanUngTenGoi": "Phản ứng tên gọi",
            "DiNhonChan": "Đi nhón chân", "ChiTro": "Chỉ trỏ", "TiepXucMat": "Tiếp xúc mắt"
        }
        input_details_list = [f"{friendly_names.get(k, k)}: {v}" for k, v in asd_predict_data.input_data.model_dump().items()]
        input_details_str = ", ".join(input_details_list)

        # Construct RAG query
        rag_query = f"lời khuyên ban đầu cho phụ huynh có con với kết quả sàng lọc tự kỷ là {ola_summary}"
        
        # Retrieve relevant documents
        with timer(f"RAG for OLA Remark (session {session_id})"):
            rag_docs: List[Document] = retriever_global.invoke(rag_query)
        
        rag_context_str = "\n\n---\n\n".join([doc.page_content for doc in rag_docs]) if rag_docs else "Không có thông tin tham khảo bổ sung."

        # Generate LLM response
        final_prompt = OLA_INITIAL_REMARK_PROMPT_GLOBAL.format(
            ola_summary=ola_summary,
            ola_probability_percent=prob_percent,
            ola_input_details=input_details_str,
            rag_context=rag_context_str
        )
        
        with timer(f"LLM for OLA Remark"):
            raw_response = llm_global.invoke(final_prompt)
            
        # Clean up response
        cleaned_response = raw_response.strip()
        all_stop_tokens = STOP_TOKENS + ["<|im_start|>", "<|im_end|>"]
        for token in all_stop_tokens:
            cleaned_response = cleaned_response.replace(token, "")
        return re.sub(r"^\s*assistant:\s*", "", cleaned_response, flags=re.I).strip()

    except Exception as e:
        print(f"Error generating OLA remark for session {session_id}: {e}")
        traceback.print_exc()
        return "Cảm ơn bạn đã hoàn thành bài sàng lọc. Nếu có bất kỳ câu hỏi nào, xin vui lòng cho tôi biết."
    
# def has_vietnamese_diacritics(text: str) -> bool:
#     """Kiểm tra xem văn bản có chứa dấu tiếng Việt hay không."""
#     vietnamese_diacritics = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹ]', re.UNICODE)
#     return bool(vietnamese_diacritics.search(text))

# def normalize_question(text: str) -> str:
#     """Chuẩn hóa văn bản không dấu bằng underthesea."""
#     try:
#         print(f"Normalizing text: {text}")
#         print(text_normalize(text))
#         return text_normalize(text)
#     except Exception as e:
#         print(f"Error normalizing text: {e}")
#         return text

# def clarify_question(session_id: str, original_question: str) -> tuple[str, bool]:
#     """
#     Làm rõ câu hỏi không dấu hoặc không rõ ràng bằng mô hình Ollama.
#     Returns: (clarified_question, needs_clarification)
#     """
#     if has_vietnamese_diacritics(original_question):
#         return original_question, False

#     normalized_question = normalize_question(original_question)
    
#     try:
#         # Gọi Ollama để kiểm tra tính rõ ràng
#         prompt = f"""
# +        Bạn là trợ lý AI. Nhiệm vụ:  ➤ Kiểm tra độ rõ nghĩa của **CÂU HỎI** dưới đây ở khía cạnh lĩnh vực tâm lý nhi khoa.
# +        CÂU HỎI: {normalized_question}
# +        ➤ Nếu chưa rõ, TRẢ VỀ đúng chuỗi:  "KHÔNG RÕ – vui lòng làm rõ **CÂU HỎI**"
# +        ➤ Nếu rõ, TRẢ VỀ phiên bản đã chuẩn hoá (có dấu nếu cần).
#          """
#         response = ollama.chat(
#             model=OLLAMA_CLARIFICATION_MODEL,
#             messages=[{"role": "user", "content": prompt}],
#             options={"temperature": 0.3}
#         )
#         clarified_response = response["message"]["content"].strip()
        
#         print(f"Clarified question (session {session_id}): {clarified_response}")
#         if "không rõ" in clarified_response.lower() or "xác nhận" in clarified_response.lower():
#             return clarified_response, True
#         return normalized_question, False
#     except Exception as e:
#         print(f"Error in Ollama clarification (session {session_id}): {e}")
#         return normalized_question, False
# === API Endpoints ===
@app_lifespan.post("/token", response_model=TokenResponse, summary="Get Session Token")
async def get_session_token_route():
    # Generate a new session token
    session_id = str(uuid.uuid4())
    token = create_access_token(data={"sub": session_id})
    return {"access_token": token, "token_type": "bearer", "session_id": session_id}

@app_lifespan.get("/asq/form", response_class=JSONResponse, summary="Get ASQ-3 Form by Age")
async def get_asq_form_route(age_in_days: int = Query(..., ge=0)):
    # Retrieve ASQ form based on child's age in days
    if not os.path.isdir(ASQ_DATA_DIR):
        raise HTTPException(status_code=500, detail=f"ASQ dir missing: {ASQ_DATA_DIR}")
    matched_data = None
    for fname in os.listdir(ASQ_DATA_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(ASQ_DATA_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    r = d.get("age", {}).get("range_in_days", {})
                    min_d, max_d = r.get("min_days"), r.get("max_days")
                    if min_d is not None and max_d is not None and min_d <= age_in_days <= max_d:
                        matched_data = d
                        break
            except:
                pass
    if not matched_data:
        raise HTTPException(status_code=404, detail="No ASQ form for age.")
    return JSONResponse(content=replace_image_placeholders(matched_data))

@app_lifespan.post("/asq/result", response_class=JSONResponse, summary="Submit ASQ-3 Answers and Log to DB")
async def submit_asq_form_route(data: ASQSubmissionPayload, current_session: dict = Depends(get_current_session)):
    # Process and store ASQ-3 submission
    session_id = current_session["session_id"]
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB service is not available.")
    
    # Get questionnaire rules
    current_rules = get_asq_questionnaire_rules(data.questionnaire_title, data.age_at_test_months)
    if not current_rules or "question" not in current_rules:
        raise HTTPException(status_code=500, detail=f"ASQ rules missing for '{data.questionnaire_title or data.age_at_test_months}'.")

    current_utc_timestamp = datetime.now(timezone.utc)
    submission_document = {
        "sessionId": session_id,
        "submissionTimestamp": current_utc_timestamp,
        "questionnaireTitle": data.questionnaire_title or current_rules.get("age", {}).get("title", "Unknown Questionnaire"),
        "ageAtTestMonths": data.age_at_test_months,
        "childInformation": {},
        "parentInformation": {},
        "domainResults": {},
        "overallSummaryText": ""
    }

    # Handle child and parent information
    if data.child_information:
        submission_document["childInformation"] = data.child_information.model_dump()
        if data.child_information.birthDate:
            try:
                submission_document["childInformation"]["birthDate"] = datetime.fromisoformat(data.child_information.birthDate.replace("Z", "+00:00"))
            except:
                submission_document["childInformation"]["birthDate"] = None
        if data.child_information.resultDate:
            try:
                submission_document["childInformation"]["resultDate"] = datetime.fromisoformat(data.child_information.resultDate.replace("Z", "+00:00"))
            except:
                submission_document["childInformation"]["resultDate"] = None
    if data.parent_information:
        submission_document["parentInformation"] = data.parent_information.model_dump()

    try:
        # Clear chat history
        history_obj_to_clear = get_session_history(session_id)
        history_obj_to_clear.clear()
        print(f"Chat history for session {session_id} (DB {REDIS_DB_HISTORY}) cleared.")
    except Exception as e:
        print(f"Warning: Could not clear chat history: {e}")

    try:
        summary_parts = []
        result_for_redis = ASQStoredResult(
            session_id=session_id,
            age_at_test_months=data.age_at_test_months,
            questionnaire_title=submission_document["questionnaireTitle"],
            overall_summary="",
            sections={}
        )
        section_keys_mapping = {
            "communication": "Giao tiếp",
            "gross_motor": "Vận động thô",
            "fine_motor": "Vận động tinh",
            "problem_solving": "Giải quyết vấn đề",
            "personal_social": "Cá nhân xã hội"
        }

        # Process each section
        for sec_key in section_keys_mapping.keys():
            answers_raw = getattr(data, sec_key, None)
            if answers_raw:
                ans_objs = [a if isinstance(a, Answer) else Answer(**a.model_dump()) for a in answers_raw]
                proc_ans = apply_scoring_logic(sec_key, ans_objs, current_rules)
                score = calculate_score(proc_ans)
                sec_rules = current_rules.get("question", {}).get(sec_key, {})
                cutoff = sec_rules.get("cutoff", 0.0)
                monitor = sec_rules.get("monitor_cutoff", sec_rules.get("cutoff", 0.0) + 15.0)
                status_text = determine_status(score, cutoff, monitor)
                summary_parts.append(f"{section_keys_mapping.get(sec_key, sec_key)}: {status_text} ({score:.0f}đ).")
                submission_document["domainResults"][sec_key] = {
                    "score": score,
                    "status": status_text,
                    "cutoff": cutoff,
                    "monitor_cutoff": monitor
                }
                result_for_redis.sections[sec_key] = ASQSectionResultDetail(
                    display_name=section_keys_mapping.get(sec_key, sec_key),
                    total_score=score,
                    status=status_text,
                    cutoff=cutoff,
                    monitor=monitor,
                    answers_processed=[Answer(id=a.id, answer=a.answer) for a in proc_ans]
                )

        if not summary_parts:
            raise HTTPException(status_code=400, detail="No valid ASQ answers provided.")
        
        overall_summary = " ".join(summary_parts)
        result_for_redis.overall_summary = overall_summary
        submission_document["overallSummaryText"] = overall_summary

        # Save to MongoDB
        try:
            db.asq_submissions.insert_one(submission_document)
            print(f"ASQ submission for session {session_id} saved to MongoDB.")
        except pymongo.errors.PyMongoError as e_mongo:
            print(f"CRITICAL: Failed to save ASQ submission to MongoDB. Error: {e_mongo}")
            traceback.print_exc()

        # Cache in Redis
        if redis_client:
            ola_key = f"asq_data:{session_id}"
            
            if redis_client.exists(ola_key):
                redis_client.delete(ola_key)
                print(f"LOG: Deleted existing ASQ data in Redis for session {session_id}.")
                
            redis_client.set(
                f"asq_data:{session_id}",
                result_for_redis.model_dump_json(exclude_none=True),
                ex=SESSION_TTL_SECONDS
            )
            print(f"ASQ results for session {session_id} cached in Redis.")
        
        return JSONResponse(content=result_for_redis.model_dump(exclude_none=True))
    
    except Exception as e:
        print(f"ASQ Submit Processing Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app_lifespan.post("/chatbot/asq_initial_engagement", response_model=InitialEngagementResponse, summary="Get Initial Chatbot Remark & Solutions Post-ASQ (with RAG)")
async def chatbot_asq_initial_engagement_route(current_session: dict = Depends(get_current_session)):
    # Generate initial remark and solutions for ASQ results
    session_id = current_session["session_id"]
    if not redis_client:
        return InitialEngagementResponse(error="Dịch vụ Redis (ASQ) không khả dụng.")
    if not all([llm_global, retriever_global, ASQ_SOLUTION_PROMPT_GLOBAL]):
        return InitialEngagementResponse(error="Trợ lý AI (RAG components) chưa sẵn sàng.")
    
    asq_json_str = redis_client.get(f"asq_data:{session_id}")
    if not asq_json_str:
        return InitialEngagementResponse(error="Không tìm thấy kết quả ASQ-3 cho phiên này trong Redis.")
    
    try:
        asq_data_obj = ASQStoredResult(**json.loads(asq_json_str))
        is_clearly_delayed = any("CHẬM RÕ RỆT" in s.status.upper() for s in asq_data_obj.sections.values())
        task1_desc_base = "soạn lời chào thân thiện, nhận xét tổng quan ngắn gọn về kết quả ASQ-3 của trẻ."
        if is_clearly_delayed:
            task1_desc = f"{task1_desc_base} **Đặc biệt, vì có lĩnh vực 'CHẬM RÕ RỆT', hãy ngay lập tức và mạnh mẽ khuyên phụ huynh nên đưa trẻ đi gặp chuyên gia để được đánh giá chuyên sâu càng sớm càng tốt. Nhấn mạnh đây là bước quan trọng nhất.**"
        else:
            task1_desc = task1_desc_base
        task1_short = "lời chào và nhận xét tổng quan ban đầu"
        remark = await generate_llm_response_with_rag_for_asq(session_id, asq_data_obj, task1_desc, task1_short)
        
        task2_desc_base = "đưa ra gợi ý hoạt động và lời khuyên cụ thể, dễ thực hiện tại nhà cho từng lĩnh vực phát triển dựa trên kết quả ASQ-3."
        if is_clearly_delayed:
            task2_desc = f"{task2_desc_base} **ƯU TIÊN HÀNG ĐẦU: Lặp lại và nhấn mạnh khuyến nghị cần đưa trẻ đi đánh giá chuyên sâu ngay. Sau đó, nếu có đưa ra gợi ý hoạt động tại nhà cho lĩnh vực chậm, phải nêu rõ đây chỉ là hỗ trợ tạm thời, rất cơ bản và không thay thế được việc can thiệp của chuyên gia. Hạn chế các hoạt động phức tạp cho những lĩnh vực này.** Tập trung vào các lĩnh vực được đánh giá là 'CHẬM' hoặc 'CÓ NGUY CƠ CHẬM'. Nếu các lĩnh vực khác bình thường, có thể đưa ra lời khuyên chung để duy trì."
        else:
            task2_desc = f"{task2_desc_base} Tập trung vào các lĩnh vực được đánh giá là 'CHẬM' hoặc 'CÓ NGUY CƠ CHẬM'. Nếu bình thường, đưa ra lời khuyên chung để duy trì và phát triển."
        task2_short = "các giải pháp và hoạt động gợi ý chi tiết cải thiện cho từng lĩnh vực phát triển"
        solutions = await generate_llm_response_with_rag_for_asq(session_id, asq_data_obj, task2_desc, task2_short)
        
        if remark:
            history = get_session_history(session_id)
            history.add_ai_message(remark)
            print(f"Initial ASQ remark added to chat history (DB {REDIS_DB_HISTORY}) for session {session_id}")
        
        print(f"Generated initial engagement for session {session_id}")
        return InitialEngagementResponse(initial_remark=remark, asq_solutions=solutions)
    
    except Exception as e:
        print(f"Error in initial engagement for session {session_id}: {e}")
        traceback.print_exc()
        return InitialEngagementResponse(error=f"Lỗi tạo nhận xét ASQ: {str(e)}")

@app_lifespan.get("/chat/history", response_model=ChatHistoryResponse, summary="Get Chat History for Session")
async def get_chat_history_route(current_session: dict = Depends(get_current_session)):
    # Retrieve chat history for the session
    session_id = current_session["session_id"]
    try:
        hist_obj = get_session_history(session_id)
        raw_msgs = list(hist_obj.messages)
        recent_msgs = raw_msgs[-(MAX_HISTORY_TURNS * 2 + 10):] if raw_msgs else []
        client_hist: List[ChatMessageClient] = []
        for msg_obj in recent_msgs:
            sender_type, text_content = "unknown", ""
            if isinstance(msg_obj, HumanMessage):
                sender_type = "user"
                text_content = msg_obj.content
            elif isinstance(msg_obj, AIMessage):
                sender_type = "bot"
                text_content = msg_obj.content
            elif hasattr(msg_obj, 'type') and hasattr(msg_obj, 'content'):
                lc_type = str(getattr(msg_obj, 'type', '')).lower()
                sender_type = "user" if lc_type == "human" else ("bot" if lc_type == "ai" else lc_type)
                text_content = str(getattr(msg_obj, 'content', ''))
            if sender_type not in ["unknown", "system"] and text_content:
                client_hist.append(ChatMessageClient(sender=sender_type, text=text_content))
        
        db_used_for_history = f"Redis DB {REDIS_DB_HISTORY}" if redis_client else "In-Memory"
        print(f"Retrieved {len(client_hist)} history messages for session {session_id} from {db_used_for_history}.")
        return ChatHistoryResponse(history=client_hist)
    
    except Exception as e:
        print(f"Error retrieving history for session {session_id}: {e}")
        traceback.print_exc()
        return ChatHistoryResponse(history=[], error=f"Lỗi lấy lịch sử chat: {str(e)}")

@app_lifespan.post("/predict/ola", response_model=OLAPredictionResponse, summary="Predict using OLA Model, Save Result, and Get Initial Remark")
async def predict_ola_route(input_data: OLAPredictionInput, current_session: dict = Depends(get_current_session)):
    # Perform OLA prediction and generate initial remark
    if not all([scaler_global, pca_global, ola_model_global]):
        raise HTTPException(status_code=503, detail="OLA model components not ready.")
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB service is not available.")
    
    session_id = current_session["session_id"]
    print(f"\n--- OLA Prediction (session:{session_id}) ---")
    
    try:
        history_to_clear = get_session_history(session_id)
        history_to_clear.clear()
        print(f"LOG: Cleared existing chat history (DB {REDIS_DB_HISTORY}) for new OLA test.")
    except Exception as e_clear:
        print(f"WARNING: Could not clear chat history for session {session_id}. Error: {e_clear}")
        
    try:
        # Prepare input data for prediction
        input_dict = input_data.model_dump()
        print(f"Input data for OLA prediction: {input_dict}")
        input_df = pd.DataFrame([input_dict], columns=['ChamNoi', 'CoLap', 'ChoiChucNang', 'ChoiGiaVo', 'HanhViLapLai', 'KyNangGiaoTiepSom', 'ChoiLuanPhien', 'BatChuoc', 'PhanUngTenGoi', 'ChiTro', 'TiepXucMat'])
        input_scaled = scaler_global.transform(input_df)
        input_pca = pca_global.transform(input_scaled)
        prediction = ola_model_global.predict(input_pca)[0]
        prediction_proba = ola_model_global.predict_proba(input_pca)[0][1]
        prediction_result = {"prediction": int(prediction), "probability": float(prediction_proba)}

        current_utc_timestamp = datetime.now(timezone.utc)
        
        # Store prediction result
        ola_result_to_store = OLAStoredResult(
            session_id=session_id,
            prediction_timestamp=current_utc_timestamp,
            input_data=input_data,
            prediction_result=OLAPredictionResult(**prediction_result)
        )
        
        # Cache in Redis
        if redis_client:
            try:
                ola_key = f"asd_predict_data:{session_id}"
                if redis_client.exists(ola_key):
                    redis_client.delete(ola_key)
                    print(f"LOG: Deleted existing OLA data in Redis for session {session_id}.")
                    
                redis_client.set(
                    f"asd_predict_data:{session_id}",
                    ola_result_to_store.model_dump_json(),
                    ex=SESSION_TTL_SECONDS
                )
                print(f"ASD prediction result for session {session_id} cached in Redis.")
            except Exception as e_redis_ola:
                print(f"WARNING: Could not save OLA prediction to Redis. Error: {e_redis_ola}")

        # Save to MongoDB
        prediction_document = {
            "sessionId": session_id,
            "predictionTimestamp": current_utc_timestamp,
            "inputData": input_dict,
            "predictionResult": prediction_result
        }
        try:
            db.asd_predictions.insert_one(prediction_document)
            print(f"OLA prediction result for session {session_id} saved to MongoDB.")
        except pymongo.errors.PyMongoError as e_mongo:
            print(f"WARNING: Could not save OLA prediction to MongoDB. Error: {e_mongo}")
            
        # Generate initial remark
        initial_remark = await generate_llm_response_for_ola(session_id, ola_result_to_store)

        # Add remark to chat history
        if initial_remark:
            try:
                history = get_session_history(session_id)
                history.add_ai_message(initial_remark)
                print(f"Initial OLA remark added to chat history (DB {REDIS_DB_HISTORY}) for session {session_id}")
            except Exception as e_hist:
                print(f"Warning: Could not add OLA remark to chat history. Error: {e_hist}")
        
        return OLAPredictionResponse(
            prediction=prediction_result["prediction"],
            probability_class_1=prediction_result["probability"],
            initial_remark=initial_remark
        )

    except Exception as e:
        print(f"OLA Prediction Error (session {session_id}): {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý dự đoán OLA: {str(e)}")

@app_lifespan.post("/chat/history/clear", response_model=ClearHistoryResponse, summary="Clear Chat History & ASQ Data for Session")
async def clear_chat_history_route(current_session: dict = Depends(get_current_session), clear_asq: bool = Query(True)):
    # Clear chat history and optionally ASQ data
    session_id = current_session["session_id"]
    try:
        hist_obj = get_session_history(session_id)
        hist_obj.clear()
        db_hist_info = f"Redis DB {REDIS_DB_HISTORY}" if redis_client else "In-Memory"
        print(f"Chat history for session {session_id} ({db_hist_info}) cleared.")
        asq_cleared = False
        if clear_asq:
            if redis_client:
                key_asq = f"asq_data:{session_id}"
                del_count = redis_client.delete(key_asq)
                asq_cleared = del_count > 0
                print(f"ASQ data for session {session_id} (DB {REDIS_DB_ASQ}) deleted: {asq_cleared}")
            else:
                print(f"ASQ data not cleared for session {session_id} as Redis (DB {REDIS_DB_ASQ}) is unavailable.")
        return ClearHistoryResponse(message="History and related data cleared.", cleared_asq_too=asq_cleared)
    
    except Exception as e:
        print(f"Error clearing history/ASQ data for session {session_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")

@app_lifespan.post("/ask", response_class=JSONResponse, summary="Ask the Chatbot a Question")
async def ask_bot_route(request_data: ChatQuestionRequest, current_session: dict = Depends(get_current_session)):
    # Handle user question and generate chatbot response
    session_id = current_session["session_id"]
    original_msg = request_data.msg.strip()
    
    if not all([llm_global, retriever_global, QA_PROMPT_GLOBAL]):
        raise HTTPException(status_code=503, detail="Chatbot core components not ready.")
    if not original_msg:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    print(f"\n--- Ask (session:{session_id}): {original_msg} ---")
    
    try:
        # Check if the question needs clarification
        # clarified_msg, needs_clarification = clarify_question(session_id, original_msg)
        # if needs_clarification:
        #     history = get_session_history(session_id)
        #     history.add_user_message(original_msg)
        #     history.add_ai_message(clarified_msg)
        #     return JSONResponse(content={"reply": clarified_msg})
        
        # Initialize chat history
        chat_history_store = get_session_history(session_id)
        memory = ConversationBufferWindowMemory(
            chat_memory=chat_history_store,
            memory_key="chat_history",
            k=MAX_HISTORY_TURNS,
            return_messages=True,
        )

        # Build session context from ASQ and OLA data
        session_context_str = "Không có thông tin từ bài test nào được ghi nhận cho phiên này."
        context_parts = []
        
        if redis_client:
            # Retrieve ASQ context
            asq_json_str = redis_client.get(f"asq_data:{session_id}")
            if asq_json_str:
                try:
                    asq_data_obj = ASQStoredResult(**json.loads(asq_json_str))
                    summary = asq_data_obj.overall_summary
                    age = asq_data_obj.age_at_test_months
                    age_str = f"{age} tháng tuổi" if age is not None else "của trẻ"
                    asq_context = f"Kết quả ASQ-3 của trẻ {age_str}: {summary}."
                    context_parts.append(asq_context)
                    print(f"INFO: Found ASQ context for session {session_id}")
                except Exception as e:
                    print(f"WARNING: Could not parse ASQ context. Error: {e}")

            # Retrieve OLA context
            ola_json_str = redis_client.get(f"asd_predict_data:{session_id}")
            if ola_json_str:
                try:
                    ola_data = OLAStoredResult(**json.loads(ola_json_str))
                    pred_summary = "Có nguy cơ" if ola_data.prediction_result.prediction == 1 else "Không có nguy cơ"
                    prob_percent = ola_data.prediction_result.probability * 100
                    friendly_names = {
                        "ChamNoi": "Chậm nói", "CoLap": "Cô lập", "ChoiChucNang": "Chơi chức năng",
                        "ChoiGiaVo": "Chơi giả vờ", "HanhViLapLai": "Hành vi lặp lại", "KyNangGiaoTiepSom": "Giao tiếp sớm",
                        "ChoiLuanPhien": "Chơi luân phiên","BatChuoc": "Bắt Chước", "PhanUngTenGoi": "Phản ứng tên gọi",
                        "ChiTro": "Chỉ trỏ", "TiepXucMat": "Tiếp xúc mắt"
                    }
                    input_details_list = [f"{friendly_names.get(k, k)}: {v}" for k, v in ola_data.input_data.model_dump().items()]
                    input_details_str = ", ".join(input_details_list)
                    ola_context = (
                        f"Kết quả sàng lọc nguy cơ tự kỷ: {pred_summary} với xác suất {prob_percent:.1f}%. "
                        f"Điểm số chi tiết: {input_details_str}."
                    )
                    context_parts.append(ola_context)
                    print(f"INFO: Found OLA/ASD context for session {session_id}")
                except Exception as e:
                    print(f"WARNING: Could not parse OLA/ASD context. Error: {e}")
        
        if context_parts:
            session_context_str = "\n".join(context_parts)
            
        # Initialize QA chain with RAG
        final_qa_prompt = QA_PROMPT_GLOBAL.partial(
            current_date=current_date_global,
            session_context=session_context_str
        )
        
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm_global,
            retriever=retriever_global,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": final_qa_prompt},
            return_source_documents=False,
        )

        # Generate response
        with timer("ConversationalRetrievalChain Invoke"):
            response_data = qa_chain.invoke({"question": original_msg})
        
        resp_text = response_data.get("answer", "")
        cleaned_text = resp_text.strip()

        return JSONResponse(content={"reply": cleaned_text})

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Ask Error (session {session_id}): {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý yêu cầu chat: {str(e)}")

# === Main Entry Point ===
if __name__ == "__main__":
    import uvicorn
    # Print available API endpoints
    print(f"\n--- API Endpoints Available ---")
    print(f"  POST /token             - Get a session token.")
    print(f"  GET  /asq/form?age_in_days={{age}} - Get ASQ form.")
    print(f"  POST /asq/result           - Submit ASQ answers (Requires Auth Token).")
    print(f"  POST /chatbot/asq_initial_engagement - Get initial ASQ advice (Requires Auth Token).")
    print(f"  POST /ask                  - Ask chatbot a question (Requires Auth Token).")
    print(f"  GET  /chat/history        - Get chat history (Requires Auth Token).")
    print(f"  POST /chat/history/clear   - Clear chat history (Requires Auth Token).")
    print(f"  POST /predict/ola         - Predict using OLA model (Requires Auth Token).")
    print(f"  POST /feedback/submit     - Submit user feedback (No Auth Required).")
    print(f"\nINFO: FastAPI server attempting to start on http://0.0.0.0:8000")
    # Run FastAPI server
    uvicorn.run(app_lifespan, host="0.0.0.0", port=8000)