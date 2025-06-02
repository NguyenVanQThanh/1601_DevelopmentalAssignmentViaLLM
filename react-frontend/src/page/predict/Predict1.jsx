import "./Predict1.css";
import Button from "../test-asq/components/Button/Button";
import TitleBox from "../../components/Title_box/TitleBox";
import FormWrapper from "../test-asq/components/Form/FormWrapper";
import { useNavigate } from "react-router-dom";

function Predict1({sessionId, accessToken}) {
  const navigate = useNavigate();
  
  const fields = [
    {
      name: "fullName",
      label: "Họ và tên trẻ:",
      type: "text",
    },
    {
      name: "phone",
      label: "SĐT:",
      type: "text",
    },
    {
      name: "birthDatePredict",
      label: "Ngày sinh:",
      type: "date",
    },
    {
      name: "location",
      label: "Nơi ở:",
      type: "select",
      options: [
        "Hồ Chí Minh",
        "Bình Dương",
        "Đồng Nai",
        "Long An",
        "Sóc Trăng",
        "Bạc Liêu",
        "Cà Mau",
        "Hà Nội",
        "Đà Nẵng",
        "Khác",
      ],
    },
    {
      name: "gender",
      label: "Giới tính:",
      type: "select",
      options: ["Nam", "Nữ"],
    },
    {
      name: "medicalHistory",
      label: "Tiền sử y khoa:",
      type: "select",
      options: ["Không", "Tiền sử thai kỳ", "Tiền sử sinh", "Tiền sử sau sinh"],
      note: "(Tiền sử y khoa liên quan đến phát triển thần kinh ở trẻ)"
    },
    {
      name: "reason",
      label: "Lý do cần dự đoán Tự kỷ:",
      type: "select",
      options: ["Chậm nói", "Tăng động", "Dấu hiệu Tự kỷ", "Khác"],
    },
  ];

  const handleSubmit = (formData) => {
  console.log("Dữ liệu gửi từ Predict1:", formData);
  navigate("/guest/predict/step2", { state: formData }); 
};
  return (
    <div className="predict-container">
      <TitleBox
        title="TRỢ DỰ ĐOÁN TỰ KỶ TRẺ DƯỚI 8 TUỔI"
        subtitle="(Bộ câu hỏi thực nghiệm - Lưu hành nội bộ)"
      />
      <div className="field-wrapper">
        <FormWrapper
          fields={fields}
          defaultValues={{
            fullName: "",
            phone: "",
            birthDatePredict: "",
            location: "",
            gender: "",
            medicalHistory: "",
            reason: "",
          }}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
}

export default Predict1;
