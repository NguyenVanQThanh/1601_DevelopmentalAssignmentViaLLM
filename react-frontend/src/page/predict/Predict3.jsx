import "./Predict3.css";
import Button from "../test-asq/components/Button/Button";
import TitleBox from "../../components/Title_box/TitleBox";
import FormWrapper from "../test-asq/components/Form/FormWrapper";
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";

function Predict3() {
  const navigate = useNavigate();
  const location = useLocation();
  const formData = location.state || {};

  console.log("Dữ liệu nhận từ Predict1&2:", formData);

  // Kết quả mặc định
  const defaultResult =
    "Kết quả dự đoán cho thấy trẻ bình thường, không đáng lo ngại về Tự Kỷ\\n Kết quả cho thấy trẻ có thể có nguy cơ mắc Tự Kỷ";

  const fields = [
    {
      name: "fullName",
      label: "Họ và tên trẻ:",
      type: "text",
      readOnly: true
    },
    {
      name: "result",
      label: "Kết quả dự đoán Tự kỷ:",
      type: "text",
      readOnly: true,
      note:
        "Khuyến khích PH chuyển sang Trò Chuyện để giải đáp thắc mắc của mình và đưa trẻ đến phòng khám Tâm lý Nhi sớm nhất giúp trẻ được chuẩn đoán chính xác và có giải pháp thích hợp. Các thông tin trên mang tính chất thực nghiệm và tham khảo"
    }
  ];

  const handleSubmit = (data) => {
    console.log("Dữ liệu gửi từ Predict:", data);
    navigate("/guest/chatbot", { state: data });
  };

  return (
    <div className="predict3-container">
      <TitleBox
        title="KẾT QUẢ DỰ ĐOÁN TỰ KỶ TRẺ DƯỚI 8 TUỔI"
        subtitle="(Bộ câu hỏi thực nghiệm - Lưu hành nội bộ)"
      />
      <FormWrapper
        fields={fields}
        defaultValues={{
          fullName: formData.fullName || "Không xác định",
          result: defaultResult
        }}
        onSubmit={handleSubmit}
        renderButtons={({ onSubmit }) => (
          <div className="form-button-wrapper">
            <Button className="button-next" onClick={onSubmit}>
              Trò chuyện cùng AI
            </Button>
          </div>
        )}
      />
    </div>
  );
}

export default Predict3;
