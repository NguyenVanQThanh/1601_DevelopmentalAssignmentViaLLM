import { useState } from "react";
import "./App.css";
import Header from "./components/Header/Header";
import Footer from "./components/Footer/Footer";
import TitleBox from "./components/Title_box/TitleBox";
import FormWrapper from "./page/test-asq/components/Form/FormWrapper";
import FormASQTest from "./page/test-asq/components/Form/FormASQTest";
import FormParentInfo from "./page/test-asq/components/Form/FormParentInfo";
import ResultPage from "./page/test-asq/ResultPage";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ChatbotPage from "./page/chatbot/ChatbotPage";

import { provinces } from "./dataweb/provinces";
import { hospitals } from "./dataweb/hospitals";
import { results } from "./dataweb/results";
import { doctors } from "./dataweb/doctors";


function App() {
  const [showExtraFields, setShowExtraFields] = useState(false);
  const [step, setStep] = useState(1);
  const [childInfo, setChildInfo] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [parentInfo, setParentInfo] = useState(null);

  const handleChildInfoChange = (fieldName, value) => {
    setChildInfo((prev) => {
      const updated = { ...prev, [fieldName]: value };

      if (fieldName === "birthDate") {
        const birth = new Date(value);
        const today = new Date();
        birth.setHours(0, 0, 0, 0);
        today.setHours(0, 0, 0, 0);

        const ageInDays = Math.floor((today - birth) / (1000 * 60 * 60 * 24));
        updated.childAgeInDays = ageInDays;

        console.log(`Trẻ có số ngày tuổi: ${ageInDays} ngày`);
      }

      if (fieldName === "pre-result" && value === "Không") {
        const fieldsToClear = [
          "result",
          "resultDate",
          "hospital",
          "doctor",
          "pre-test",
        ];
        fieldsToClear.forEach((key) => delete updated[key]);
        console.log("Cleared extra diagnosis fields due to 'Không' selection");
      }

      return updated;
    });

    if (fieldName === "pre-result") {
      console.log("User selected 'pre-result':", value);
      setShowExtraFields(value === "Có");
    }
  };

  const handleParentInfoChange = (fieldName, value) => {
    setParentInfo((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
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

  const extraFields = [
    {
      type: "select",
      name: "result",
      label: "Kết quả chuẩn đoán cụ thể:",
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
  const [age, setAge] = useState(null); // sẽ chứa object như { title: "6m Questionnaire", ... }


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
                      // onSubmit={(data) => {
                      //   console.log("Child info submitted:", data);
                      //   setChildInfo(data);
                      //   setStep(2);
                      // }}
                      onSubmit={async (data) => {
                        console.log("Child info submitted:", data);
                        setChildInfo(data);
                      
                        const ageInDays = data.childAgeInDays;
                      
                        if (ageInDays) {
                          try {
                            const res = await fetch(`http://127.0.0.1:8000/form?age_in_days=${ageInDays}`);
                            const result = await res.json();
                            setAge(result.age); // 👈 Lưu age từ backend vào state
                            console.log("Fetched age info:", result.age);
                          } catch (error) {
                            console.error("Error fetching age:", error);
                          }
                        }
                      
                        setStep(2);
                      }}
                      

                    />
                  </>
                )}

                {step === 2 && (
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
                      console.log("ASQ test submitted:", dto);
                      setTestResult(dto);
                      setStep(3);
                    }}
                    defaultValues={{
                      ...testResult,
                      age: {
                        childAgeInDays: childInfo?.childAgeInDays || null,
                      },
                    }}
                  />
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
                        console.log("Parent info submitted:", parentInfo);
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
                      subtitle={`( ${age.title} )`}
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
