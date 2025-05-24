import logging
import json
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# XỬ LÝ PHÂN LỚP TUỔI CHO BỘ CÂU HỎI

# Đọc file JSON chứa câu hỏi
with open("data/18month.json", "r", encoding="utf-8") as f:
    asq_data = json.load(f)

# Thêm middleware CORS để cho phép frontend truy cập API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL của frontend React sửa port lại Thanh 5174, Hảo 5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Định nghĩa mô hình Pydantic để nhận câu trả lời từ front-end
class Answer(BaseModel):
    id: int
    answer: str

class SectionAnswers(BaseModel):
    communication: Optional[List[Answer]] = None
    gross_motor: Optional[List[Answer]] = None
    fine_motor: Optional[List[Answer]] = None
    problem_solving: Optional[List[Answer]] = None
    personal_social: Optional[List[Answer]] = None

# Hàm áp dụng logic tính điểm dựa trên scoring_note
def apply_scoring_logic(section: str, answers: List[Answer]) -> List[Answer]:
    section_data = asq_data["question"].get(section, {})
    scoring_note = section_data.get("scoring_note", None)
    if not scoring_note:
        return answers

    # Kiểm tra xem answers có phải là danh sách hợp lệ không
    if not isinstance(answers, list):
        raise HTTPException(status_code=400, detail=f"Answers for section {section} must be a list")

    # Chuyển answers thành dictionary để dễ chỉnh sửa
    answer_dict = {answer.id: answer for answer in answers}

    # Kiểm tra điều kiện trong scoring_note
    condition = scoring_note["condition"]
    action = scoring_note["action"]

    # Lấy câu trả lời của câu hỏi trong điều kiện
    condition_answer = answer_dict.get(condition["question_id"], None)
    condition_answer_value = condition_answer.answer if condition_answer else None

    # Nếu điều kiện thỏa mãn, thực hiện hành động
    if condition_answer_value in condition["values"]:
        target_question_id = action["question_id"]
        if target_question_id in answer_dict:
            answer_dict[target_question_id].answer = action["set_value"]

    # Chuyển lại thành danh sách
    return list(answer_dict.values())

# Hàm tính điểm cho một lĩnh vực
def calculate_score(answers: List[Answer]) -> float:
    score_mapping = {"Có": 10, "Thỉnh Thoảng": 5, "Chưa": 0}
    return sum(score_mapping.get(answer.answer, 0) for answer in answers)

# Hàm xác định trạng thái dựa trên điểm
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
        "60m Questionnaire": "image60_",
        "BỘ CÂU HỎI 4 THÁNG TUỔI": "image4_",
    }

    title = data.get("age", {}).get("title")
    logger.debug(f"🔍 Đang xử lý bộ: {title}")

    if not title or title not in title_to_prefix:
        logger.warning("⛔️ Không khớp với bộ nào, bỏ qua.")
        return data

    prefix = title_to_prefix[title]
    counter = 1

    for section_key, section in data["question"].items():
        for question in section.get("questions", []):
            if question.get("image_filepath") in (None, "image_placeholder.png"):
                new_name = f"{prefix}{counter}.png"
                logger.debug(f"✅ Gán {new_name} cho ID {question['id']} trong mục {section_key}")
                question["image_filepath"] = new_name
                counter += 1

    return data


@app.get("/form")
async def get_form(age_in_days: int = Query(..., description="Số ngày tuổi của trẻ")):
    data_dir = "data"
    matched_file = None

    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
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

    # ✅ Thay thế ảnh placeholder thành tên ảnh thực
    logger.debug("🔍 Đang thay thế ảnh placeholder...")
    matched_file = replace_image_placeholders(matched_file)

    # Trả về cho frontend
    logger.debug("✅ Đã thay thế ảnh thành công, trả về dữ liệu cho frontend.")
    return matched_file


# 2. Endpoint để nhận câu trả lời và trả về kết quả
@app.post("/form/result")
async def submit_form(data: SectionAnswers):
    try:
        result = {}
        # Xử lý từng lĩnh vực
        for section in ["communication", "gross_motor", "fine_motor", "problem_solving", "personal_social"]:
            answers = getattr(data, section, None)
            if answers:
                # Áp dụng logic tính điểm nếu có scoring_note
                updated_answers = apply_scoring_logic(section, answers)
                # Tính điểm
                total_score = calculate_score(updated_answers)
                # Lấy cutoff và max từ section trong question
                section_data = asq_data["question"][section]
                cutoff = section_data["cutoff"]
                max_score = section_data["max"]
                # Xác định trạng thái
                status = determine_status(total_score, cutoff, max_score)
                # Chuyển updated_answers thành danh sách dictionary để trả về
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
        logger.error(f"Lỗi trong việc xử lý câu trả lời: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Tự động chạy ứng dụng khi chạy file
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
