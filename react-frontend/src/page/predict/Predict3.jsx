import "./Predict3.css";
import Button from "../test-asq/components/Button/Button";
import TitleBox from "../../components/Title_box/TitleBox";
import FormWrapper from "../test-asq/components/Form/FormWrapper";
import React, {useState, useEffect} from "react";
import { useNavigate, useLocation } from "react-router-dom";

function Predict3({sessionId, accessToken}) {
  const navigate = useNavigate();
  const location = useLocation();
  const formData = location.state || {};

  console.log("Dữ liệu nhận từ Predict1&2:", formData);
  const [predictionResult, setPredictionResult] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPrediction = async () => {
      try {
        // Kiểm tra accessToken
        if (!accessToken) {
          throw new Error("Không tìm thấy token xác thực.");
        }

        // Ánh xạ các câu trả lời từ formData thành đặc trưng cho API
        const answerMapping = {
          "Có": 1.0,
          "Thỉnh Thoảng": 0.5,
          "Không": 0.0,
          "Tốt": 1.0,
          "Khá": 0.5,
          "Kém": 0.0
        };

        const olaInput = {
          ChamNoi: answerMapping[formData.q1] || 0.0,
          CungNhac: answerMapping[formData.q2] || 0.0,
          CoLap: answerMapping[formData.q3] || 0.0,
          HanhViLapLai: answerMapping[formData.q4] || 0.0,
          KyNangGiaoTiepSom: answerMapping[formData.q5] || 0.0,
          ChoiLuanPhien: answerMapping[formData.q6] || 0.0,
          PhanUngTenGoi: answerMapping[formData.q7] || 0.0,
          DiNhonChan: answerMapping[formData.q8] || 0.0,
          ChiTro: answerMapping[formData.q9] || 0.0,
          TiepXucMat: answerMapping[formData.q10] || 0.0,
        };

        // Lấy URL API từ .env
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        const response = await fetch(`${API_BASE_URL}/predict/ola`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify(olaInput),
        });

        if (!response.ok) {
          throw new Error("Lỗi khi gọi API dự đoán: " + response.statusText);
        }

        const result = await response.json();
        console.log("Kết quả từ API:", result);

        // Xử lý kết quả dự đoán
        const prediction = result.prediction;
        const probability = result.probability_class_1;
        let displayResult = "";
        if (prediction === 0) {
          displayResult = `Kết quả dự đoán cho thấy trẻ bình thường, không đáng lo ngại về Tự Kỷ (xác suất nguy cơ: ${(probability * 100).toFixed(2)}%).`;
        } else {
          displayResult = `Kết quả cho thấy trẻ có thể có nguy cơ mắc Tự Kỷ (xác suất nguy cơ: ${(probability * 100).toFixed(2)}%).`;
        }

        setPredictionResult(displayResult);
        setIsLoading(false);
      } catch (err) {
        console.error("Lỗi:", err);
        setError("Không thể lấy kết quả dự đoán. Vui lòng thử lại sau.");
        setIsLoading(false);
      }
    };

    fetchPrediction();
  }, [formData, accessToken]);

  // Định nghĩa fields cho FormWrapper
  const fields = [
    {
      name: "fullName",
      label: "Họ và tên trẻ:",
      type: "text",
      readOnly: true,
    },
    {
      name: "result",
      label: "Kết quả dự đoán Tự kỷ:",
      type: "text",
      readOnly: true,
      note:
        "Khuyến khích PH chuyển sang Trò Chuyện để giải đáp thắc mắc của mình và đưa trẻ đến phòng khám Tâm lý Nhi sớm nhất giúp trẻ được chuẩn đoán chính xác và có giải pháp thích hợp. Các thông tin trên mang tính chất thực nghiệm và tham khảo",
    },
  ];

  const handleSubmit = (data) => {
    console.log("Dữ liệu gửi từ Predict3:", data);
    navigate("/guest/chatbot", {
      state: { ...data, predictionResult, sessionId, accessToken }, // Truyền dữ liệu sang ChatbotPage
    });
  };

  return (
    <div className="predict3-container">
      <TitleBox
        title="KẾT QUẢ DỰ ĐOÁN TỰ KỶ TRẺ DƯỚI 8 TUỔI"
        subtitle="(Bộ câu hỏi thực nghiệm - Lưu hành nội bộ)"
      />
      {isLoading ? (
        <div>Đang tải kết quả dự đoán...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : (
        <FormWrapper
          fields={fields}
          defaultValues={{
            fullName: formData.fullName || "Không xác định",
            result: predictionResult,
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
      )}
    </div>
  );
}

export default Predict3;