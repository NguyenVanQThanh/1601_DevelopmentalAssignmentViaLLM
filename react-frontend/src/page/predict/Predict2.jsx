import "./Predict2.css";
import Button from "../test-asq/components/Button/Button";
import TitleBox from "../../components/Title_box/TitleBox";
import FormWrapper from "../test-asq/components/Form/FormWrapper";
import { useLocation } from "react-router-dom";
import React from "react";
import questions from "./QuestionPredict.json";
import { useNavigate } from "react-router-dom";

function Predict2() {
  const navigate = useNavigate();

  const location = useLocation();
  const formData = location.state;

  console.log("Dữ liệu nhận từ Predict1:", formData);

  const handleSubmit = (answers) => {
  console.log("Câu trả lời từ Predict2:", answers);

  const mergedData = {
    ...formData, 
    ...answers  
  };

  console.log("Dữ liệu gửi sang Predict3:", mergedData);
  navigate("/guest/predict/step3", { state: mergedData });
};

  const fields = questions.map((q) => ({
    name: `q${q.id}`,
    label: (
      <span>
        <strong className="qbold">Câu hỏi {q.id}:</strong>
        <div className="question-text">
          {q.question.split("\\n").map((line, idx) => (
            <React.Fragment key={idx}>
              {line}
              <br />
            </React.Fragment>
          ))}
        </div>
      </span>
    ),
    type: "select",
    options: q.options,
    note: q.note || undefined,
  }));

  return (
    <div className="predict2-container">
      <TitleBox
        title="DỰ ĐOÁN TỰ KỶ TRẺ DƯỚI 8 TUỔI"
        subtitle="(Bộ câu hỏi thực nghiệm - Lưu hành nội bộ)"
      />
      <div className="question-wrapper">
        <FormWrapper
          fields={fields}
          defaultValues={Object.fromEntries(fields.map(f => [f.name, ""]))}
          onSubmit={handleSubmit}
          renderButtons={({ onSubmit }) => (
            <div className="form-button-wrapper">
              <Button className="button-next" onClick={onSubmit}>
                GỬI KẾT QUẢ
              </Button>
            </div>
          )}
        />
      </div>
    </div>
  );
}

export default Predict2;
