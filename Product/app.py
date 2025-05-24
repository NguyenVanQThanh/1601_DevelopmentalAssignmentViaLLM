import os
import traceback
import re
import json
import time
import psutil
from typing import List, Optional, Any
from contextlib import contextmanager

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_community.llms import Ollama

from custom_embeddings import BGEM3Embeddings

# ==== CHATBOT CONFIGURATION =====================================================
# Name of the model in Ollama
LLM_MODEL_NAME     = "vistral-assistant"
# Path to the BGE-M3 embedding model
BGE_M3_MODEL_PATH  = "./models/bge-m3"
# Path to the FAISS vector database
VECTOR_DB_PATH     = "vectorstores/db_faiss_test"
# Path to the conversation history JSON file
HISTORY_FILE_PATH  = "conversation_history.json"
# Context window size of the Ollama model (must match Ollama's Modelfile num_ctx)
CTX_WINDOW = 8192
# Maximum new tokens the LLM will generate
MAX_NEW_TOKENS     = 2048
# Safety buffer for prompt length calculations
PROMPT_LENGTH_BUFFER = 50
# Stop tokens for the LLM generation
STOP_TOKENS        = ["[/INST]", "<|im_end|>", "</s>"]
# Maximum number of conversation turns to include in the history
MAX_HISTORY_TURNS  = 3

# ==== ASQ-3 CONFIGURATION =======================================================
# Directory containing ASQ-3 JSON data files
ASQ_DATA_DIR = "./ASQ3API/data"
# Specific ASQ-3 JSON file to load by default (e.g., for 18 months)
ASQ_JSON_FILE = os.path.join(ASQ_DATA_DIR, "18month.json")

if os.path.exists(ASQ_JSON_FILE):
    with open(ASQ_JSON_FILE, "r", encoding="utf-8") as f:
        asq_data = json.load(f)
else:
    asq_data = {}
    print(f"Warning: Default ASQ file {ASQ_JSON_FILE} not found. ASQ-3 endpoints might require a specific file or may not work correctly with default data.")

# ==== FASTAPI APP INITIALIZATION ===============================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== UTILITY FUNCTIONS ========================================================
# Function Name: timer
# Input: description (str) - A description of the timed operation.
# Functionality: A context manager to measure the execution time of a code block.
# Returns: None (prints the elapsed time).
@contextmanager
def timer(description: str):
    start = time.time()
    yield
    elapsed_time = time.time() - start
    print(f"{description}: {elapsed_time:.3f} seconds")

# Function Name: get_memory_usage
# Input: None
# Functionality: Gets the current RSS (Resident Set Size) memory usage of the process.
# Returns: float - Memory usage in MB.
def get_memory_usage() -> float:
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024

# ==== CHATBOT COMPONENTS LOADING ==============================================

# Function Name: load_llm
# Input: None
# Functionality: Initializes and returns the Ollama LLM wrapper.
# Returns: Ollama - An instance of the Langchain Ollama LLM.
def load_llm() -> Ollama:
    try:
        print(f"Initializing model '{LLM_MODEL_NAME}' from Ollama...")
        llm = Ollama(
            model=LLM_MODEL_NAME,
            temperature=0.5,
            stop=STOP_TOKENS,
        )
        try:
            llm.invoke("Hello")
            print(f"Model '{LLM_MODEL_NAME}' from Ollama is ready.")
        except Exception as e:
            print(f"Error invoking Ollama model test: {e}")
            print(f"Ensure model '{LLM_MODEL_NAME}' is created/pulled in Ollama and Ollama server is running.")
            raise HTTPException(status_code=500, detail=f"Failed to connect or use model {LLM_MODEL_NAME} from Ollama.")
        print(f"Memory after initializing Ollama wrapper: {get_memory_usage():.2f} MB")
        return llm
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error loading LLM from Ollama: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to load LLM model from Ollama.")

# Function Name: load_vector_db
# Input: None
# Functionality: Loads the FAISS vector database from local files.
# Returns: FAISS - An instance of the FAISS vector store.
def load_vector_db() -> FAISS:
    print(f"Loading Vector DB from: {VECTOR_DB_PATH}")
    for f in ("index.faiss", "index.pkl"):
        if not os.path.exists(f"{VECTOR_DB_PATH}/{f}"):
            print(f"ERROR: Vector DB file {f} not found in {VECTOR_DB_PATH}.")
            raise HTTPException(
                status_code=500,
                detail=f"Vector store file {f} missing in {VECTOR_DB_PATH}. Please create FAISS index."
            )
    try:
        embeddings = BGEM3Embeddings(BGE_M3_MODEL_PATH)
        db = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
        if db.index.ntotal == 0:
            print("ERROR: Vector store is empty.")
            raise HTTPException(
                status_code=500,
                detail="Vector store is empty. Please populate FAISS index."
            )
        print(f"Vector DB loaded successfully. Items: {db.index.ntotal}")
        print(f"Memory after loading Vector DB: {get_memory_usage():.2f} MB")
        return db
    except Exception as e:
        print(f"Error loading Vector DB: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to load Vector DB.")

# Global chatbot components
llm: Optional[Ollama] = None
vector_db: Optional[FAISS] = None
retriever: Any = None
history: Optional[FileChatMessageHistory] = None
qa_chain: Any = None

print("Initializing chatbot components…")
try:
    llm = load_llm()
    vector_db = load_vector_db()
    retriever = vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 3,
            "score_threshold": 0.4
        },
    )

    # Function Name: init_chat_history
    # Input: history_file_path (str) - Path to the chat history file.
    # Functionality: Initializes or clears the chat history file.
    # Returns: FileChatMessageHistory - An instance of FileChatMessageHistory.
    def init_chat_history(history_file_path: str) -> FileChatMessageHistory:
        dir_path = os.path.dirname(history_file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        if os.path.exists(history_file_path):
            try:
                os.remove(history_file_path)
                print(f"Deleted {history_file_path} for a clean start.")
            except OSError as err:
                print(f"Error deleting history file: {err}")
        with open(history_file_path, 'w', encoding='utf-8') as f:
            f.write('[]')
        return FileChatMessageHistory(file_path=history_file_path)

    history = init_chat_history(HISTORY_FILE_PATH)

    # Function Name: format_chat_history
    # Input: msgs (List[AIMessage | HumanMessage]) - List of chat messages.
    # Input: max_turns (int) - Maximum number of conversation turns to format.
    # Functionality: Formats the chat history into a string.
    # Returns: str - The formatted chat history string.
    def format_chat_history(msgs: List[AIMessage | HumanMessage], max_turns: int = MAX_HISTORY_TURNS) -> str:
        recent = msgs[-max_turns * 2:] if msgs else []
        lines = []
        for i in range(0, len(recent), 2):
            if i + 1 < len(recent):
                human_msg_obj = recent[i]
                ai_msg_obj = recent[i+1]
                human_msg_content = human_msg_obj.content if isinstance(human_msg_obj, HumanMessage) else str(human_msg_obj)
                ai_msg_content = ai_msg_obj.content if isinstance(ai_msg_obj, AIMessage) else str(ai_msg_obj)
                lines.append(f"Người dùng: {human_msg_content}")
                lines.append(f"Trợ lý AI: {ai_msg_content}")
        return "\n".join(lines) if lines else "Chưa có lịch sử hội thoại trước đó."

    template = """<|im_start|>system
Bạn là trợ lý AI chuyên về sức khỏe và tâm thần nhi khoa. Mục tiêu của bạn là cung cấp thông tin chính xác, dễ hiểu và hữu ích cho phụ huynh. Hãy tuân thủ các hướng dẫn sau:

1.  **Ưu tiên Context:** Lấy thông tin từ phần **Context** được cung cấp làm nguồn chính để trả lời câu hỏi.
2.  **Bổ sung từ kiến thức của bạn:** Nếu Context không có thông tin, không đầy đủ, hoặc bạn cảm thấy kiến thức đã được huấn luyện (fine-tuned) của mình có thể làm rõ hơn hoặc bổ sung giá trị cho câu trả lời, hãy sử dụng nó. Thông tin bổ sung phải liên quan trực tiếp đến câu hỏi và lĩnh vực chuyên môn của bạn.
3.  **Chính xác và không bịa đặt:** Dù thông tin lấy từ Context hay từ kiến thức của bạn, nó phải chính xác và dựa trên cơ sở khoa học. Tuyệt đối không bịa đặt thông tin.
4.  **Tập trung vào câu hỏi:** Luôn trả lời trực tiếp vào câu hỏi ({question}).
5.  **Khi không có thông tin:** Nếu cả Context và kiến thức đã huấn luyện của bạn đều không có thông tin để trả lời câu hỏi, hãy thông báo một cách lịch sự, ví dụ: "Tôi rất tiếc, hiện tại tôi không có đủ thông tin về chủ đề này từ cả tài liệu được cung cấp lẫn kiến thức của mình."
6.  **Diễn đạt:** Tự nhiên, không trích dẫn nguyên văn từ Context trừ khi đó là một định nghĩa quan trọng hoặc trích dẫn ngắn cần thiết.
7.  **Định dạng:** Rõ ràng, dùng gạch đầu dòng (-) hoặc số (1., 2.) nếu phù hợp, câu đầy đủ, đúng ngữ pháp.
8.  **Giọng điệu:** Ngôn ngữ đơn giản, thân thiện, cảm thông và hỗ trợ.
9.  **Lịch sử hội thoại:** Sử dụng lịch sử ({chat_history}) để hiểu ngữ cảnh các câu hỏi trước đó, nhưng câu trả lời của bạn phải tập trung vào câu hỏi hiện tại.
10. **Luôn kết thúc câu trả lời bằng:** "Lưu ý: Thông tin từ AI chỉ mang tính tham khảo, không thay thế cho chẩn đoán hoặc tư vấn y tế từ bác sĩ chuyên khoa. Phụ huynh nên đưa trẻ đến gặp bác sĩ nhi khoa để được kiểm tra và tư vấn cụ thể."

**Context**:
{context}

**Lịch sử hội thoại**:
{chat_history}
<|im_end|>
<|im_start|>user
{question}<|im_end|>
<|im_start|>assistant
"""
    QA_PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "context", "question"])
    qa_chain = create_stuff_documents_chain(llm, QA_PROMPT)
    print("Chatbot components initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize chatbot components: {e}")
    traceback.print_exc()

# ==== ASQ-3 COMPONENTS =======================================================
class Answer(BaseModel):
    id: int
    answer: str

class SectionAnswers(BaseModel):
    communication: Optional[List[Answer]] = None
    gross_motor: Optional[List[Answer]] = None
    fine_motor: Optional[List[Answer]] = None
    problem_solving: Optional[List[Answer]] = None
    personal_social: Optional[List[Answer]] = None

# Function Name: apply_scoring_logic
# Input: section (str) - The ASQ-3 section name.
# Input: answers (List[Answer]) - A list of answers for the section.
# Functionality: Applies specific scoring logic based on conditional answers within a section.
# Returns: List[Answer] - The updated list of answers after applying logic.
def apply_scoring_logic(section: str, answers: List[Answer]) -> List[Answer]:
    section_data = asq_data.get("question", {}).get(section, {})
    scoring_note = section_data.get("scoring_note", None)
    if not scoring_note:
        return answers
    if not isinstance(answers, list):
        raise HTTPException(status_code=400, detail=f"Answers for section {section} must be a list")
    answer_dict = {answer.id: answer for answer in answers}
    condition = scoring_note["condition"]
    action = scoring_note["action"]
    condition_answer_obj = answer_dict.get(condition["question_id"], None)
    condition_answer_value = condition_answer_obj.answer if condition_answer_obj else None
    if condition_answer_value in condition["values"]:
        target_question_id = action["question_id"]
        if target_question_id in answer_dict:
            answer_dict[target_question_id].answer = action["set_value"]
    return list(answer_dict.values())

# Function Name: calculate_score
# Input: answers (List[Answer]) - A list of answers.
# Functionality: Calculates the total score for a list of answers based on a predefined mapping.
# Returns: float - The total calculated score.
def calculate_score(answers: List[Answer]) -> float:
    score_mapping = {"Có": 10, "Thỉnh Thoảng": 5, "Chưa": 0}
    return sum(score_mapping.get(answer.answer, 0) for answer in answers)

# Function Name: determine_status
# Input: total_score (float) - The total score for a section.
# Input: cutoff (float) - The cutoff score for "clear delay".
# Input: monitor_threshold (float) - The threshold for "at risk / monitoring zone".
# Functionality: Determines the developmental status based on the total score and thresholds.
# Returns: str - The determined status string.
def determine_status(total_score: float, cutoff: float, monitor_threshold: float) -> str:
    if total_score < cutoff:
        return "CHẬM RÕ RỆT (Cần đánh giá chuyên sâu)"
    elif total_score <= monitor_threshold:
        return "CÓ NGUY CƠ CHẬM (Cần theo dõi sát và có thể cần đánh giá thêm)"
    else:
        return "PHÁT TRIỂN BÌNH THƯỜNG"

# Function Name: replace_image_placeholders
# Input: data (dict) - The ASQ questionnaire data.
# Functionality: Replaces generic image placeholders with specific image filenames based on the questionnaire title.
# Returns: dict - The questionnaire data with updated image filepaths.
def replace_image_placeholders(data: dict) -> dict:
    title_to_prefix = {
        "2m Questionnaire": "image2_", "4m Questionnaire": "image4_", "6m Questionnaire": "image6_",
        "8m Questionnaire": "image8_", "9m Questionnaire": "image9_", "10m Questionnaire": "image10_",
        "12m Questionnaire": "image12_", "14m Questionnaire": "image14_", "16m Questionnaire": "image16_",
        "18m Questionnaire": "image18_", "20m Questionnaire": "image20_", "22m Questionnaire": "image22_",
        "24m Questionnaire": "image24_", "27m Questionnaire": "image27_", "30m Questionnaire": "image30_",
        "33m Questionnaire": "image33_", "36m Questionnaire": "image36_", "42m Questionnaire": "image42_",
        "48m Questionnaire": "image48_", "54m Questionnaire": "image54_", "60m Questionnaire": "image60_"
    }
    title = data.get("age", {}).get("title")
    print(f"Processing questionnaire set: {title}")
    if not title or title not in title_to_prefix:
        print(f"No prefix mapping for title '{title}', skipping image replacement.")
        return data
    prefix = title_to_prefix[title]
    for section_key, section_value in data.get("question", {}).items():
        if isinstance(section_value, dict) and "questions" in section_value:
            current_section_image_counter = 1
            for question_item in section_value.get("questions", []):
                if isinstance(question_item, dict) and question_item.get("image_filepath") == "image_placeholder.png":
                    new_image_name = f"{prefix}{current_section_image_counter}.png"
                    question_item["image_filepath"] = new_image_name
                    current_section_image_counter += 1
    return data

# ==== API ROUTES ===============================================================
class Question(BaseModel):
    msg: str

@app.post("/ask", response_class=JSONResponse)
async def ask_bot(question_model: Question):
    if not qa_chain or not llm or not retriever or not history:
        print("ERROR: One or more chatbot components are not initialized.")
        raise HTTPException(status_code=500, detail="Chatbot components not initialized properly.")

    msg = question_model.msg
    if not msg.strip():
        raise HTTPException(status_code=400, detail="Please enter a question.")

    print(f"\n--- New question received (POST): {msg} ---")
    try:
        print("Retrieving documents...")
        with timer("Document Retrieval"):
            docs: List[Document] = retriever.invoke(msg)
        print(f"Found {len(docs)} relevant document(s).")

        print("Processing context...")
        with timer("Context Processing"):
            placeholder_prompt = QA_PROMPT.format(chat_history="h", context="c", question="q")
            base_prompt_tokens = llm.get_num_tokens(placeholder_prompt) - \
                                 llm.get_num_tokens("h") - llm.get_num_tokens("c") - llm.get_num_tokens("q")
            msg_tokens = llm.get_num_tokens(msg)
            chat_hist_str = format_chat_history(history.messages, MAX_HISTORY_TURNS)
            hist_tokens = llm.get_num_tokens(chat_hist_str)
            available_for_context = CTX_WINDOW - MAX_NEW_TOKENS - PROMPT_LENGTH_BUFFER - base_prompt_tokens - msg_tokens - hist_tokens
            max_context_tokens = max(100, available_for_context)
            print(f"Token budget: BasePrompt={base_prompt_tokens}, Msg={msg_tokens}, Hist={hist_tokens}. Available for Context: {available_for_context} (target: {max_context_tokens})")

            current_tokens = 0
            ctx_docs_for_chain = []
            for doc_idx, doc in enumerate(docs):
                content = doc.page_content
                content_tokens = llm.get_num_tokens(content)
                if current_tokens + content_tokens <= max_context_tokens:
                    ctx_docs_for_chain.append(doc)
                    current_tokens += content_tokens
                else:
                    remaining_tokens = max_context_tokens - current_tokens
                    if remaining_tokens > PROMPT_LENGTH_BUFFER // 2:
                        estimated_char_len = int(len(content) * (remaining_tokens / content_tokens)) if content_tokens > 0 else 0
                        truncated_content = content[:estimated_char_len]
                        truncated_tokens = llm.get_num_tokens(truncated_content)
                        while truncated_tokens > remaining_tokens and len(truncated_content) > 10:
                            chars_to_remove = max(1, int(len(truncated_content) * 0.05))
                            truncated_content = truncated_content[:-chars_to_remove]
                            truncated_tokens = llm.get_num_tokens(truncated_content)
                        if truncated_tokens > 0 and truncated_tokens <= remaining_tokens:
                             ctx_docs_for_chain.append(Document(page_content=truncated_content, metadata=doc.metadata))
                             current_tokens += truncated_tokens
                    break
            print(f"Using {len(ctx_docs_for_chain)} document chunks for context. Total context tokens: {current_tokens}")

        print(f"Chat history for prompt:\n{chat_hist_str if chat_hist_str != 'Chưa có lịch sử hội thoại trước đó.' else '[No history]'}")

        final_context_str_for_check = "\n\n---\n\n".join([d.page_content for d in ctx_docs_for_chain])
        estimated_prompt = QA_PROMPT.format(chat_history=chat_hist_str, context=final_context_str_for_check, question=msg)
        prompt_tokens = llm.get_num_tokens(estimated_prompt)
        print(f"Estimated final prompt tokens: {prompt_tokens}")

        input_limit = CTX_WINDOW - MAX_NEW_TOKENS - PROMPT_LENGTH_BUFFER
        if prompt_tokens > input_limit:
            print(f"WARNING: Prompt too long ({prompt_tokens} tokens), limit is {input_limit} tokens.")
            raise HTTPException(
                status_code=413,
                detail=f"Your request and context are too long ({prompt_tokens} tokens). Limit is {input_limit}. Please try a shorter question."
            )

        print("Invoking LLM chain...")
        with timer("LLM Chain Invocation"):
            response_data = qa_chain.invoke({
                "chat_history": chat_hist_str,
                "context": ctx_docs_for_chain,
                "question": msg
            })
        resp_text = str(response_data) if not isinstance(response_data, str) else response_data
        print(f"Raw LLM response:\n{resp_text}")

        print("Post-processing response...")
        resp_text_cleaned = resp_text.strip()
        patterns_to_remove = [
            r"<\|im_start\|>system.*?<\|im_end\|>", r"<\|im_start\|>user.*?<\|im_end\|>",
            r"<\|im_end\|>", r"^\s*<\|im_start\|>assistant\s*", r"^\s*assistant:\s*",
            r"^\s*trả lời:\s*", r"\[/INST\]",
        ]
        for pattern in patterns_to_remove:
            resp_text_cleaned = re.sub(pattern, "", resp_text_cleaned, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE).strip()
        resp_text_cleaned = re.sub(r"^\s*[-#*=_]{2,}\s*$", "", resp_text_cleaned, flags=re.MULTILINE)
        resp_text_cleaned = re.sub(r"(\s*#\s*){3,}|(#){3,}|(\s*-\s*){3,}", " ", resp_text_cleaned)
        resp_text_cleaned = re.sub(r"\s{2,}", " ", resp_text_cleaned).strip()

        lines = resp_text_cleaned.split('\n')
        cleaned_lines = []
        first_real_line = True
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line or set(stripped_line) <= {"#", "-", "*", "_", "="}:
                continue
            if stripped_line.startswith(("* ", "• ", "+ ")):
                stripped_line = "- " + stripped_line[2:].strip()
            if stripped_line.startswith("- ") and len(stripped_line) > 2:
                char_after_bullet = stripped_line[2]
                if 'a' <= char_after_bullet.lower() <= 'z':
                    stripped_line = "- " + char_after_bullet.upper() + stripped_line[3:]
            elif first_real_line and len(stripped_line) > 0 and not stripped_line.startswith("-"):
                first_char = stripped_line[0]
                if 'a' <= first_char.lower() <= 'z':
                    stripped_line = first_char.upper() + stripped_line[1:]
                first_real_line = False
            cleaned_lines.append(stripped_line)
        resp_text_cleaned = "\n".join(cleaned_lines)

        disclaimer_text = "Lưu ý: Thông tin từ AI chỉ mang tính tham khảo, không thay thế cho chẩn đoán hoặc tư vấn y tế từ bác sĩ chuyên khoa. Phụ huynh nên đưa trẻ đến gặp bác sĩ nhi khoa để được kiểm tra và tư vấn cụ thể."
        resp_text_cleaned = resp_text_cleaned.replace(disclaimer_text, "").strip()
        if resp_text_cleaned:
            if not resp_text_cleaned.endswith(("\n", "\n\n")): resp_text_cleaned += "\n\n"
            elif not resp_text_cleaned.endswith("\n\n"): resp_text_cleaned += "\n"
            resp_text_cleaned += disclaimer_text
        else:
            resp_text_cleaned = "Xin lỗi, tôi không thể đưa ra phản hồi vào lúc này.\n\n" + disclaimer_text

        print(f"Processed response:\n{resp_text_cleaned}")
        final_resp_tokens = llm.get_num_tokens(resp_text_cleaned)
        print(f"Final response tokens: {final_resp_tokens}")

        if history:
            try:
                history.add_user_message(HumanMessage(content=msg))
                history.add_ai_message(AIMessage(content=resp_text_cleaned))
                max_messages = MAX_HISTORY_TURNS * 2
                if len(history.messages) > max_messages:
                    history.messages = history.messages[-max_messages:]
            except Exception as hist_err:
                print(f"Error updating history file: {hist_err}")
                traceback.print_exc()
        return JSONResponse(content={"reply": resp_text_cleaned})
    except HTTPException as http_exc:
        print(f"HTTP Exception in /ask: {http_exc.status_code} - {http_exc.detail}")
        return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})
    except ValueError as ve:
        print(f"Value Error in /ask: {ve}")
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"detail": str(ve)})
    except Exception as e:
        print(f"Unexpected error in /ask: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})

@app.get("/form")
async def get_form(age_in_days: int = Query(..., description="Child's age in days")):
    if not asq_data and not os.path.exists(ASQ_JSON_FILE):
        raise HTTPException(status_code=500, detail="ASQ-3 data directory or default file not configured or found.")

    matched_questionnaire_data = None
    print(f"Attempting to find questionnaire for age: {age_in_days} days in directory: {ASQ_DATA_DIR}")
    if not os.path.isdir(ASQ_DATA_DIR):
        raise HTTPException(status_code=500, detail=f"ASQ data directory not found: {ASQ_DATA_DIR}")

    for filename in os.listdir(ASQ_DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ASQ_DATA_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if ("age" in data and isinstance(data["age"], dict) and
                    "range_in_days" in data["age"] and isinstance(data["age"]["range_in_days"], dict) and
                    "min_days" in data["age"]["range_in_days"] and "max_days" in data["age"]["range_in_days"]):
                    min_days = data["age"]["range_in_days"]["min_days"]
                    max_days = data["age"]["range_in_days"]["max_days"]
                    if min_days <= age_in_days <= max_days:
                        matched_questionnaire_data = data
                        print(f"Found matching questionnaire: '{data.get('age',{}).get('title', 'N/A')}'")
                        break
            except Exception as e_file:
                print(f"Error processing file {filepath}: {e_file}")
    if not matched_questionnaire_data:
        raise HTTPException(status_code=404, detail="No suitable questionnaire found for the child's age.")
    processed_data = replace_image_placeholders(matched_questionnaire_data)
    return JSONResponse(content=processed_data)

@app.post("/form/result")
async def submit_form(data: SectionAnswers):
    current_questionnaire_rules = asq_data
    if not current_questionnaire_rules:
         raise HTTPException(status_code=500, detail="Default ASQ-3 data (e.g., 18month.json) not loaded.")
    try:
        result_summary = {}
        for section_name in ["communication", "gross_motor", "fine_motor", "problem_solving", "personal_social"]:
            submitted_answers = getattr(data, section_name, None)
            if submitted_answers:
                processed_answers_for_scoring = apply_scoring_logic(section_name, submitted_answers)
                total_score = calculate_score(processed_answers_for_scoring)
                section_rules = current_questionnaire_rules.get("question", {}).get(section_name, {})
                cutoff_score = section_rules.get("cutoff", 0)
                monitor_score = section_rules.get("monitor_cutoff", cutoff_score + 15)
                status = determine_status(total_score, cutoff_score, monitor_score)
                answers_as_dict = [ans.dict() for ans in processed_answers_for_scoring]
                result_summary[section_name] = {
                    "submitted_answers": [ans.dict() for ans in submitted_answers],
                    "processed_answers_for_scoring": answers_as_dict,
                    "total_score": total_score,
                    "cutoff_score": cutoff_score,
                    "monitor_score": monitor_score,
                    "status": status
                }
        if not result_summary:
            raise HTTPException(status_code=400, detail="No valid answers provided.")
        return JSONResponse(content=result_summary)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error processing ASQ-3 form result: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error processing ASQ-3 results: {str(e)}")

# ==== APPLICATION RUN ==========================================================
if __name__ == "__main__":
    import uvicorn
    print("Ensuring necessary directories exist...")
    os.makedirs("./models", exist_ok=True)
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    if ASQ_DATA_DIR and not os.path.exists(ASQ_DATA_DIR):
         os.makedirs(ASQ_DATA_DIR, exist_ok=True)

    print("Checking Ollama server connection...")
    if llm:
        print("Ollama connection seems OK (LLM wrapper initialized).")
    else:
        print("WARNING: LLM wrapper not initialized. Ollama server might not be running or model may not exist.")
        print(f"Ensure model '{LLM_MODEL_NAME}' is created in Ollama (e.g., `ollama create {LLM_MODEL_NAME} -f YourModelfile`)")
        print("And Ollama server is running (usually `ollama serve` or runs in background).")

    print(f"Starting FastAPI server, listening on all available interfaces...")
    uvicorn.run(app, host="0.0.0.0", port=8000)