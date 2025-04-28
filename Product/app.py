import os
import traceback
import re
import json
from typing import List, Optional, Any

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from huggingface_hub import hf_hub_download

from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from langchain_core.documents import Document
from llama_cpp import Llama

from custom_embeddings import BGEM3Embeddings

# ==== CẤU HÌNH CHATBOT ==============================================================
LLM_MODEL_NAME     = "vilm/vinallama-2.7b-chat"
LLM_GGUF_FILENAME  = "merge_vistral_q5_k_m.gguf"
LLM_GGUF_PATH      = f"./models/{LLM_GGUF_FILENAME}"

BGE_M3_MODEL_PATH  = "./models/bge-m3"
VECTOR_DB_PATH     = "vectorstores/db_faiss"
HISTORY_FILE_PATH  = "conversation_history.json"

MAX_HISTORY_TURNS  = 3
MAX_NEW_TOKENS     = 1024
N_BATCH            = 64
STOP_TOKENS        = ["[/INST]", "<|im_end|>"]
PROMPT_LENGTH_BUFFER = 50

# ==== CẤU HÌNH ASQ-3 ==============================================================
ASQ_DATA_DIR = "../ASQ3API/data"
ASQ_JSON_FILE = os.path.join(ASQ_DATA_DIR, "18month.json")

# Đọc file JSON chứa câu hỏi ASQ-3
if os.path.exists(ASQ_JSON_FILE):
    with open(ASQ_JSON_FILE, "r", encoding="utf-8") as f:
        asq_data = json.load(f)
else:
    asq_data = {}
    print(f"Warning: {ASQ_JSON_FILE} not found. ASQ-3 endpoints may not work correctly.")

# ==== FASTAPI APP ===========================================================
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== CHATBOT: WRAPPER GGUF ==========================================================
class GGUFLLM(BaseLLM):
    _model: Llama

    def __init__(self, model: Llama):
        super().__init__()
        self._model = model

    def context_window(self) -> int:
        n_ctx_attr = getattr(self._model, "n_ctx")
        return n_ctx_attr() if callable(n_ctx_attr) else n_ctx_attr

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        **kwargs: Any
    ) -> LLMResult:
        stop = stop or STOP_TOKENS
        gens: List[Generation] = []
        for prompt in prompts:
            out = self._model(
                prompt,
                max_tokens=MAX_NEW_TOKENS,
                temperature=kwargs.get("temperature", 0.3),
                top_k=kwargs.get("top_k", 30),
                top_p=kwargs.get("top_p", 0.85),
                repeat_penalty=kwargs.get("repeat_penalty", 1.2),
                stop=stop,
            )
            generated_text = out["choices"][0]["text"]
            if generated_text.strip().lower().startswith("[/inst]"):
                generated_text = generated_text.strip()[len("[/INST]"):].strip()
            if generated_text.strip().lower().startswith("trả lời:"):
                generated_text = generated_text.strip()[len("trả lời:"):].strip()
            gens.append(Generation(text=generated_text))
        return LLMResult(generations=[gens])

    @property
    def _llm_type(self) -> str:
        return "gguf_llm"

    def get_num_tokens(self, text: str) -> int:
        if not isinstance(text, str):
            return 0
        try:
            return len(self._model.tokenize(text.encode("utf-8")))
        except Exception:
            return 9999999

# ==== CHATBOT: LOAD LLM ==============================================================
def load_llm() -> GGUFLLM:
    try:
        if not os.path.exists(LLM_GGUF_PATH):
            os.makedirs(os.path.dirname(LLM_GGUF_PATH), exist_ok=True)
            hf_hub_download(
                repo_id=LLM_MODEL_NAME,
                filename=LLM_GGUF_FILENAME,
                local_dir=os.path.dirname(LLM_GGUF_PATH),
                local_dir_use_symlinks=False
            )
        model = Llama(
            model_path=LLM_GGUF_PATH,
            n_ctx=4096,
            n_threads=os.cpu_count() - 1,
            n_gpu_layers=0,
            n_batch=N_BATCH,
        )
        print(f"n_ctx from model: {getattr(model, 'n_ctx')}")
        return GGUFLLM(model)
    except Exception as e:
        print(f"Error loading LLM: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to load LLM model.")

# ==== CHATBOT: LOAD VECTOR DB ========================================================
def load_vector_db() -> FAISS:
    for f in ("index.faiss", "index.pkl"):
        if not os.path.exists(f"{VECTOR_DB_PATH}/{f}"):
            raise HTTPException(
                status_code=500,
                detail=f"Vector store file {f} missing in {VECTOR_DB_PATH}. Please create FAISS index."
            )
    embeddings = BGEM3Embeddings(BGE_M3_MODEL_PATH)
    db = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
    if db.index.ntotal == 0:
        raise HTTPException(
            status_code=500,
            detail="Vector store is empty. Please populate FAISS index."
        )
    return db

# ==== CHATBOT: KHỞI TẠO ===========================================================
llm: Optional[GGUFLLM] = None
vector_db: Optional[FAISS] = None
retriever: Any = None
history: Optional[FileChatMessageHistory] = None
qa_chain: Any = None

print("Init chatbot components …")
try:
    llm = load_llm()
    vector_db = load_vector_db()
    retriever = vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 3,
            "fetch_k": 10,
            "lambda_mult": 0.5,
            "score_threshold": 0.4
        },
        return_documents=True,
    )

    def init_chat_history(history_file_path: str) -> FileChatMessageHistory:
        dir_path = os.path.dirname(history_file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        if os.path.exists(history_file_path):
            try:
                os.remove(history_file_path)
                print(f"Đã xóa {history_file_path} để khởi động sạch.")
            except OSError as err:
                print(f"Lỗi xóa history: {err}")
        with open(history_file_path, 'w', encoding='utf-8') as f:
            f.write('[]')
        return FileChatMessageHistory(file_path=history_file_path)

    history = init_chat_history(HISTORY_FILE_PATH)

    def format_chat_history(msgs: List[AIMessage | HumanMessage], max_turns: int = MAX_HISTORY_TURNS) -> str:
        recent = msgs[-max_turns * 2:] if msgs else []
        lines = []
        for i in range(0, len(recent), 2):
            if i + 1 < len(recent):
                human_msg = recent[i].content if isinstance(recent[i], HumanMessage) else ""
                ai_msg = recent[i + 1].content if isinstance(recent[i + 1], AIMessage) else ""
                lines.append(f"Người dùng: {human_msg}")
                lines.append(f"Trợ lý AI: {ai_msg}")
        return "\n".join(lines) if lines else "Chưa có lịch sử hội thoại trước đó."

    template = """<|im_start|>system
    Bạn là trợ lý AI chuyên về sức khỏe và tâm thần nhi khoa, cung cấp thông tin chính xác, dễ hiểu cho phụ huynh dựa trên Context và lịch sử hội thoại. Tuân thủ các quy tắc:

    1. Chỉ dùng thông tin từ Context, không bịa đặt.
    2. Tập trung vào câu hỏi ({question}). Nếu có độ tuổi cụ thể, chỉ dùng thông tin liên quan; nếu không, trả lời: "Tài liệu không có thông tin về [chủ đề] cho trẻ [X] tháng/tuổi."
    3. Diễn đạt tự nhiên, không trích dẫn nguyên văn.
    4. Định dạng rõ ràng: dùng gạch đầu dòng (-) hoặc số (1., 2.), câu đầy đủ, đúng ngữ pháp.
    5. Ngôn ngữ đơn giản, giọng điệu thân thiện, hỗ trợ.
    6. Dùng lịch sử ({chat_history}) để hiểu ngữ cảnh, nhưng chỉ trả lời câu hỏi hiện tại.
    7. Nếu không có thông tin, trả lời: "Không tìm thấy thông tin phù hợp về [chủ đề]."
    8. Kết thúc bằng: "Lưu ý: Thông tin từ AI, không thay thế tư vấn y tế. Phụ huynh nên tham khảo bác sĩ nhi khoa."

    **Context**: {context}
    **Lịch sử hội thoại**: {chat_history}

    <|im_end|>
    <|im_start|>user
    {question}<|im_end|>
    <|im_start|>assistant
    """

    QA_PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "context", "question"])
    qa_chain = create_stuff_documents_chain(llm, QA_PROMPT)
except Exception as e:
    print(f"Failed to initialize chatbot components: {e}")
    traceback.print_exc()
    raise HTTPException(status_code=500, detail="Failed to initialize chatbot components.")

# ==== ASQ-3: MÔ HÌNH PYDANTIC ===========================================================
class Answer(BaseModel):
    id: int
    answer: str

class SectionAnswers(BaseModel):
    communication: Optional[List[Answer]] = None
    gross_motor: Optional[List[Answer]] = None
    fine_motor: Optional[List[Answer]] = None
    problem_solving: Optional[List[Answer]] = None
    personal_social: Optional[List[Answer]] = None

# ==== ASQ-3: HÀM XỬ LÝ ===========================================================
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
    condition_answer = answer_dict.get(condition["question_id"], None)
    condition_answer_value = condition_answer.answer if condition_answer else None

    if condition_answer_value in condition["values"]:
        target_question_id = action["question_id"]
        if target_question_id in answer_dict:
            answer_dict[target_question_id].answer = action["set_value"]

    return list(answer_dict.values())

def calculate_score(answers: List[Answer]) -> float:
    score_mapping = {"Có": 10, "Thỉnh Thoảng": 5, "Chưa": 0}
    return sum(score_mapping.get(answer.answer, 0) for answer in answers)

def determine_status(total_score: float, cutoff: float, max_score: float) -> str:
    if total_score <= cutoff:
        return "CHẬM RÕ RỆT"
    elif cutoff < total_score <= max_score:
        return "CHẬM"
    else:
        return "BÌNH THƯỜNG"

def replace_image_placeholders(data):
    title_to_prefix = {
        "2m Questionnaire": "image2_",
        "4m Questionnaire": "image4_",
        "6m Questionnaire": "image6_",
        "8m Questionnaire": "image8_",
        "9m Questionnaire": "image9_",
        "12m Questionnaire": "image12_",
        "14m Questionnaire": "image14_",
        "18m Questionnaire": "image18_",
        "20m Questionnaire": "image20_",
        "22m Questionnaire": "image22_",
        "24m Questionnaire": "image24_",
        "27m Questionnaire": "image27_",
        "30m Questionnaire": "image30_",
        "33m Questionnaire": "image33_",
        "36m Questionnaire": "image36_",
        "42m Questionnaire": "image42_",
        "48m Questionnaire": "image48_",
        "60m Questionnaire": "image60_"
    }

    title = data.get("age", {}).get("title")
    print("🔍 Đang xử lý bộ:", title)

    if not title or title not in title_to_prefix:
        print("⛔️ Không khớp với bộ nào, bỏ qua.")
        return data

    prefix = title_to_prefix[title]
    counter = 1

    for section_key, section in data.get("question", {}).items():
        for question in section.get("questions", []):
            if question.get("image_filepath") == "image_placeholder.png":
                new_name = f"{prefix}{counter}.png"
                print(f"✅ Gán {new_name} cho ID {question['id']}")
                question["image_filepath"] = new_name
                counter += 1

    return data

# ==== ROUTES ===============================================================
class Question(BaseModel):
    msg: str

@app.post("/ask", response_class=JSONResponse)
async def ask_bot(question: Question):
    if not qa_chain:
        raise HTTPException(status_code=500, detail="Chatbot components not initialized.")
    
    msg = question.msg
    if not msg.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")

    print(f"\n--- Nhận câu hỏi mới (POST): {msg} ---")

    try:
        # 1. Retrieval
        print("Bắt đầu tìm kiếm tài liệu...")
        docs: List[Document] = retriever.invoke(msg)
        print(f"Tìm thấy {len(docs)} tài liệu liên quan.")

        # 2. Cắt bớt Context nếu quá dài
        ctx_str_parts = []
        max_context_tokens = 2000
        current_tokens = 0
        for doc in docs:
            content = doc.page_content
            content_tokens = llm.get_num_tokens(content)
            if current_tokens + content_tokens <= max_context_tokens:
                ctx_str_parts.append(content)
                current_tokens += content_tokens
            else:
                remaining_tokens = max_context_tokens - current_tokens
                if remaining_tokens > 50:
                    truncated_content = content[:int(len(content) * (remaining_tokens / content_tokens))]
                    ctx_str_parts.append(truncated_content)
                break

        ctx_str = "\n\n---\n\n".join(ctx_str_parts)
        print("Nội dung Context được chọn:")
        for i, part in enumerate(ctx_str_parts):
            content_preview = part[:200].replace('\n', ' ') + "..."
            print(f"  Chunk {i+1}: {content_preview}")

        # 3. Lấy lịch sử hội thoại
        chat_hist_msgs = history.messages if history else []
        chat_hist_str = format_chat_history(chat_hist_msgs, MAX_HISTORY_TURNS)
        print("Lịch sử hội thoại sử dụng cho prompt:")
        print(chat_hist_str if chat_hist_str != "Chưa có lịch sử hội thoại." else "[Không có]")

        # 4. Kiểm tra độ dài Prompt
        estimated_prompt = QA_PROMPT.format(chat_history=chat_hist_str, context=ctx_str, question=msg)
        prompt_tokens = llm.get_num_tokens(estimated_prompt)
        print(f"Ước lượng token của prompt đầu vào: {prompt_tokens}")

        ctx_window = llm.context_window()
        input_limit = ctx_window - MAX_NEW_TOKENS - PROMPT_LENGTH_BUFFER
        if prompt_tokens > input_limit:
            print(f"CẢNH BÁO: Prompt quá dài ({prompt_tokens} tokens), giới hạn {input_limit} tokens.")
            raise HTTPException(
                status_code=413,
                detail=f"Yêu cầu của bạn và ngữ cảnh quá dài ({prompt_tokens} tokens). Giới hạn là {input_limit}. Vui lòng thử lại với câu hỏi ngắn hơn."
            )

        # 5. Gọi LLM Chain
        print("Bắt đầu gọi LLM Chain...")
        response_data = qa_chain.invoke({
            "chat_history": chat_hist_str,
            "context": docs,
            "question": msg
        })

        if isinstance(response_data, str):
            resp_text = response_data
        else:
            print(f"Định dạng response không mong đợi: {type(response_data)}")
            resp_text = str(response_data)

        print("--- Phản hồi thô từ LLM ---")
        print(resp_text)
        print("--------------------------")

        # 6. Xử lý hậu kỳ
        print("Bắt đầu xử lý hậu kỳ...")
        resp_text = resp_text.strip()

        patterns_to_remove = [
            r"<\|im_start\|>.*?<\|im_end\|>",
            r"<\|im_end\|>",
            r"#+\s*-+\s*#*",
            r"trả lời:",
            r"\s*assistant:",
        ]

        for pattern in patterns_to_remove:
            resp_text = re.sub(pattern, "", resp_text, flags=re.IGNORECASE | re.DOTALL)

        if "<|im_start|>user" in resp_text:
            resp_text = resp_text.split("<|im_start|>user")[0].strip()

        lines = resp_text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if stripped_line.startswith(("* ", "• ", "+ ")):
                stripped_line = "- " + stripped_line[2:].strip()
            if stripped_line.startswith("- ") and len(stripped_line) > 2:
                stripped_line = "- " + stripped_line[2].upper() + stripped_line[3:]
            elif not cleaned_lines and len(stripped_line) > 0 and not stripped_line.startswith("-"):
                stripped_line = stripped_line[0].upper() + stripped_line[1:]
            cleaned_lines.append(stripped_line)

        resp_text_cleaned = "\n".join(cleaned_lines)

        disclaimer = "Lưu ý: Thông tin từ AI, không thay thế tư vấn y tế. Phụ huynh nên tham khảo bác sĩ nhi khoa."
        possible_old_disclaimers = ["Đây là ý kiến của AI, hãy tham khảo thêm ý kiến từ chuyên gia"]
        for old_disc in possible_old_disclaimers:
            resp_text_cleaned = resp_text_cleaned.replace(old_disc, "").strip()

        if disclaimer not in resp_text_cleaned:
            if resp_text_cleaned and not resp_text_cleaned.endswith("\n"):
                resp_text_cleaned += "\n\n"
            elif resp_text_cleaned and not resp_text_cleaned.endswith("\n\n"):
                resp_text_cleaned += "\n"
            resp_text_cleaned += disclaimer

        print("--- Phản hồi sau xử lý ---")
        print(resp_text_cleaned)
        print("-------------------------")

        final_resp_tokens = llm.get_num_tokens(resp_text_cleaned)
        print(f"Số token của câu trả lời cuối cùng: {final_resp_tokens}")

        # 7. Lưu lịch sử
        if history:
            try:
                clean_msg = re.sub(r"<\|im_start\|>.*?<\|im_end\|>|<\|im_end\|>|#+-+#*", "", msg, flags=re.IGNORECASE | re.DOTALL).strip()
                clean_resp = re.sub(r"<\|im_start\|>.*?<\|im_end\|>|<\|im_end\|>|#+-+#*", "", resp_text_cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
                
                history.add_user_message(clean_msg)
                history.add_ai_message(clean_resp)

                max_messages = MAX_HISTORY_TURNS * 2
                if len(history.messages) > max_messages:
                    history.messages = history.messages[-max_messages:]
            except Exception as hist_err:
                print(f"Lỗi khi cập nhật file history: {hist_err}")

        return {"reply": resp_text_cleaned}

    except HTTPException as http_exc:
        print(f"HTTP Exception: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Lỗi không mong muốn xảy ra: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Đã xảy ra lỗi máy chủ trong quá trình xử lý yêu cầu. Vui lòng thử lại sau.")

@app.get("/form")
async def get_form(age_in_days: int = Query(..., description="Số ngày tuổi của trẻ")):
    if not asq_data:
        raise HTTPException(status_code=500, detail="ASQ-3 data not loaded. Please check ASQ_JSON_FILE.")

    matched_file = None
    for filename in os.listdir(ASQ_DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ASQ_DATA_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                try:
                    min_days = data["age"]["range_in_days"]["min_days"]
                    max_days = data["age"]["range_in_days"]["max_days"]
                    if min_days <= age_in_days <= max_days:
                        matched_file = data
                        break
                except KeyError:
                    continue

    if not matched_file:
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ câu hỏi phù hợp với độ tuổi.")

    matched_file = replace_image_placeholders(matched_file)
    return matched_file

@app.post("/form/result")
async def submit_form(data: SectionAnswers):
    if not asq_data:
        raise HTTPException(status_code=500, detail="ASQ-3 data not loaded. Please check ASQ_JSON_FILE.")

    try:
        result = {}
        for section in ["communication", "gross_motor", "fine_motor", "problem_solving", "personal_social"]:
            answers = getattr(data, section, None)
            if answers:
                updated_answers = apply_scoring_logic(section, answers)
                total_score = calculate_score(updated_answers)
                section_data = asq_data.get("question", {}).get(section, {})
                cutoff = section_data.get("cutoff", 0)
                max_score = section_data.get("max", 60)
                status = determine_status(total_score, cutoff, max_score)
                updated_answers_dict = [answer.dict() for answer in updated_answers]
                result[section] = {
                    "updated_answers": updated_answers_dict,
                    "total_score": total_score,
                    "cutoff": cutoff,
                    "max": max_score,
                    "status": status
                }

        if not result:
            raise HTTPException(status_code=400, detail="No valid answers provided for any section")

        return result
    except Exception as e:
        print(f"Error processing ASQ-3 form: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

# ==== RUN ===================================================================
if __name__ == "__main__":
    import uvicorn
    os.makedirs("./models", exist_ok=True)
    os.makedirs(ASQ_DATA_DIR, exist_ok=True)
    os.makedirs("./static", exist_ok=True)
    os.makedirs("./templates", exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=8000) 