import { useState } from "react";
import "./App.css";
import "./styles/page_asq.css";
import "./styles/page_chatbot.css";
import Header from "./components/Header/Header";
import Footer from "./components/Footer/Footer";
import TitleBox from "./components/Title_box/TitleBox";
import FormWrapper from "./page/test-asq/components/Form/FormWrapper";
import FormASQTest from "./page/test-asq/components/Form/FormASQTest";
import FormParentInfo from "./page/test-asq/components/Form/FormParentInfo";
import ResultPage from "./page/test-asq/ResultPage";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ChatbotPage from "./page/chatbot/ChatbotPage";
import { Navigate } from "react-router-dom";

function App() {
  const provinces = [
    // Ưu tiên
    "TP. Hồ Chí Minh",
    "Bình Dương",
    "Đồng Nai",
    "Long An",
    "Tây Ninh",
    "Bà Rịa - Vũng Tàu",
    "Hà Nội",

    "An Giang",
    "Bạc Liêu",
    "Bắc Giang",
    "Bắc Kạn",
    "Bắc Ninh",
    "Bến Tre",
    "Bình Định",
    "Bình Phước",
    "Bình Thuận",
    "Cà Mau",
    "Cao Bằng",
    "Cần Thơ",
    "Đà Nẵng",
    "Đắk Lắk",
    "Đắk Nông",
    "Điện Biên",
    "Đồng Tháp",
    "Gia Lai",
    "Hà Giang",
    "Hà Nam",
    "Hà Tĩnh",
    "Hải Dương",
    "Hải Phòng",
    "Hậu Giang",
    "Hòa Bình",
    "Hưng Yên",
    "Khánh Hòa",
    "Kiên Giang",
    "Kon Tum",
    "Lai Châu",
    "Lạng Sơn",
    "Lào Cai",
    "Lâm Đồng",
    "Nam Định",
    "Nghệ An",
    "Ninh Bình",
    "Ninh Thuận",
    "Phú Thọ",
    "Phú Yên",
    "Quảng Bình",
    "Quảng Nam",
    "Quảng Ngãi",
    "Quảng Ninh",
    "Quảng Trị",
    "Sóc Trăng",
    "Sơn La",
    "Thái Bình",
    "Thái Nguyên",
    "Thanh Hóa",
    "Thừa Thiên Huế",
    "Tiền Giang",
    "Trà Vinh",
    "Tuyên Quang",
    "Vĩnh Long",
    "Vĩnh Phúc",
    "Yên Bái",
  ];
  const [showExtraFields, setShowExtraFields] = useState(false);

  const handleChildInfoChange = (fieldName, value) => {
    setChildInfo((prev) => ({
      ...prev,
      [fieldName]: value,
    }));

    if (fieldName === "pre-result") {
      setShowExtraFields(value === "Có");
    }
  };

  const formFields = [
    {
      type: "text",
      name: "fullName",
      label: "Họ và tên:",
      onChange: handleChildInfoChange,
    },
    {
      type: "date",
      name: "birthDate",
      label: "Ngày sinh:",
      onChange: handleChildInfoChange,
    },
    {
      type: "select",
      name: "location",
      label: "Địa chỉ hiện tại:",
      options: provinces,
      onChange: handleChildInfoChange,
    },
    {
      type: "radio",
      name: "gender",
      label: "Giới tính:",
      options: ["Nam", "Nữ"],
      onChange: handleChildInfoChange,
    },
    {
      type: "radio",
      name: "pre-birth",
      label: "Trẻ sinh non:",
      options: ["Không", "Có"],
      onChange: handleChildInfoChange,
    },
    {
      type: "radio",
      name: "pre-result",
      label: "Kết quả chuẩn đoán:",
      options: ["Không", "Có"],
      onChange: handleChildInfoChange,
    },
  ];

  const results = ["Rối loạn Phổ tự kỷ", "Chậm nói", "Chậm phát triển trí tuệ"];
  const hospitals = [
    "BV Nhi Đồng 1 - HCM",
    "BV Nhi Đồng 2 - HCM",
    "BV Nhi Trung Ương - HCM",
    "BV Đại học Y - HCM",
    "BV Tỉnh",
    "PK Tâm lý Nhi đồng",
    "Trung tâm Can thiệp",
    "PK Khác",
  ];
  const doctors = [
    "BS Chuyên khoa Tâm lý Nhi",
    "Bác sĩ Chuyên khoa khác",
    "Giáo viên Giáo dục",
    "Giáo viên Giáo dục Đặc biệt",
    "Khác",
  ];

  const extraFields = [
    {
      type: "select",
      name: "result",
      label: "Kết quả chuẩn đoán:",
      options: results,
      onChange: handleChildInfoChange,
    },
    {
      type: "date",
      name: "resultDate",
      label: "Ngày chuẩn đoán:",
      onChange: handleChildInfoChange,
    },
    {
      type: "select",
      name: "hospital",
      label: "Nơi chuẩn đoán:",
      options: hospitals,
      onChange: handleChildInfoChange,
    },
    {
      type: "select",
      name: "doctor",
      label: "Người chẩn đoán:",
      options: doctors,
      onChange: handleChildInfoChange,
    },
    {
      type: "radio",
      name: "pre-test",
      label: "Trẻ đã được sàng lọc trước đó với ASQ-3/M-CHAT-R:",
      options: ["Không", "Có"],
      onChange: handleChildInfoChange,
    },
  ];

  const [step, setStep] = useState(1);

  const [childInfo, setChildInfo] = useState(null);

  const [testResult, setTestResult] = useState(null);

  const [parentInfo, setParentInfo] = useState(null);

  const handleParentInfoChange = (fieldName, value) => {
    setParentInfo((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  return (
    <div className="container-page">
      <Header />
      <Routes>
        <Route path="/" element={<Navigate to="/guest/asq3-test" />} />
        <Route
          path="/guest/asq3-test"
          element={
            <main>
              <section className="container-content">
                {/* 👉 BƯỚC 1: Nhập thông tin trẻ */}
                {step === 1 && (
                  <>
                    <TitleBox title="THÔNG TIN TRẺ EM" />
                    <FormWrapper
                      fields={
                        showExtraFields
                          ? [...formFields, ...extraFields]
                          : formFields
                      }
                      defaultValues={childInfo || {}}
                      onSubmit={(data) => {
                        console.log("Bước 1:", data);
                        setChildInfo(data);
                        setStep(2);
                      }}
                    />
                  </>
                )}

                {/* 👉 BƯỚC 2: Làm bài test */}
                {step === 2 && (
                  <>
                    <FormASQTest
                      key={
                        step +
                        (testResult
                          ? Object.keys(testResult.answers || {}).length
                          : 0)
                      }
                      onBack={(snapshot) => {
                        setTestResult(snapshot); 
                        setStep(1); 
                      }}
                      onSubmit={(dto) => {
                        setTestResult(dto);
                        setStep(3); 
                      }}
                      defaultValues={testResult || {}}
                    />
                  </>
                )}

                {step === 3 && (
                  <>
                    <TitleBox
                      title="THÔNG TIN PHỤ HUYNH"
                      onBack={() => setStep(2)}
                    />
                    <FormParentInfo
                      defaultValues={parentInfo || {}}
                      onChange={handleParentInfoChange}
                      onBack={() => setStep(2)}
                      onSubmit={(parentInfo) => {
                        console.log("Thông tin phụ huynh:", parentInfo);
                        console.log("Kết quả bài test:", testResult);
                        setParentInfo(parentInfo); 
                        setStep(4); 
                      }}
                    />
                  </>
                )}
                {step === 4 && testResult && childInfo && parentInfo && (
                  <>
                    <TitleBox
                      title="Kết quả bài sàng lọc đánh giá phát triển theo độ tuổi ASQ-3"
                      subtitle="(Bộ câu hỏi 20 tháng tuổi)"
                    />
                    <ResultPage
                      childInfo={childInfo}
                      parentInfo={parentInfo}
                      testResult={testResult}
                    />
                  </>
                )}
              </section>
            </main>
          }
        />
        <Route path="/guest/chatbot" element={<ChatbotPage />} />
      </Routes>

      <div className="container-footer">
        <Footer />
      </div>
    </div>
  );
}

export default App;
