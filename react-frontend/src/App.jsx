import { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import Header from "./components/Header/Header";
import Footer from "./components/Footer/Footer";
import TitleBox from "./components/Title_box/TitleBox";
import FormWrapper from "./page/test-asq/components/Form/FormWrapper";
import FormASQTest from "./page/test-asq/components/Form/FormASQTest";
import FormParentInfo from "./page/test-asq/components/Form/FormParentInfo";
import ResultPage from "./page/test-asq/ResultPage";
import ChatbotPage from "./page/chatbot/ChatbotPage";
import Predict1 from './page/predict/Predict1';
import Predict2 from "./page/predict/Predict2";
import Predict3 from "./page/predict/Predict3";
import FeedbackButton from "./components/Feedback/FeedbackButton.jsx";

import { provinces } from "./dataweb/provinces";
import { hospitals } from "./dataweb/hospitals";
import { results as diagnosisResults } from "./dataweb/results";
import { doctors } from "./dataweb/doctors";
function App() {
  const [showExtraFields, setShowExtraFields] = useState(false);
  const [step, setStep] = useState(1);

  const [childInfo, setChildInfo] = useState(null);
  const [asqUserAnswers, setAsqUserAnswers] = useState(null);
  const [parentInfo, setParentInfo] = useState(null);

  const [ageInfo, setAgeInfo] = useState(null);
  const [asqQuestionnaireData, setAsqQuestionnaireData] = useState(null);
  const [processedAsqResults, setProcessedAsqResults] = useState(null);
  const [llmAsqSolutions, setLlmAsqSolutions] = useState(null);

  const [sessionId, setSessionId] = useState(() => localStorage.getItem('sessionId') || null);
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('accessToken') || null);
  const [initialChatbotMessage, setInitialChatbotMessage] = useState(null);
  const [initialMessageFetchedOrUsed, setInitialMessageFetchedOrUsed] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  // Helper function to add ngrok skip header and Authorization
  const fetchWithNgrokHeaders = useCallback(async (url, options = {}) => {
    const headers = {
      ...options.headers,
      'ngrok-skip-browser-warning': 'true', // Or any other value like "69420"
    };
    if (accessToken && options.method !== 'GET' && options.method !== 'HEAD') { // Typically add Auth for POST, PUT, DELETE etc.
        // For /token endpoint, we don't send Authorization header yet
        if (!url.endsWith("/token")) {
             headers['Authorization'] = `Bearer ${accessToken}`;
        }
    }
    // For GET requests, Authorization might also be needed if the endpoint is protected
    // Adjust this condition based on which GET endpoints need auth
    if (accessToken && (options.method === 'GET' || options.method === 'HEAD') && url.includes("/chat/history")) { // Example: /chat/history needs auth
        headers['Authorization'] = `Bearer ${accessToken}`;
    }


    return fetch(url, { ...options, headers });
  }, [accessToken]); // accessToken is a dependency


  const fetchToken = useCallback(async () => {
    if (!localStorage.getItem('accessToken')) {
      try {
        // Use fetchWithNgrokHeaders for /token as well, though it won't add Authorization for this specific call
        const response = await fetchWithNgrokHeaders(`${API_BASE_URL}/token`, { method: 'POST' });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Lỗi khi lấy token và phân tích lỗi' }));
          throw new Error(errorData.detail || 'Lỗi khi lấy token phiên làm việc');
        }
        const data = await response.json();
        setAccessToken(data.access_token);
        setSessionId(data.session_id);
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('sessionId', data.session_id);
        console.log("Token và ID phiên mới đã được lấy và lưu trữ:", data.session_id);
      } catch (error) {
        console.error("Lỗi khi lấy token phiên:", error);
        alert(`Không thể khởi tạo phiên làm việc: ${error.message}. Vui lòng làm mới trang.`);
      }
    } else {
      if (!accessToken) setAccessToken(localStorage.getItem('accessToken'));
      if (!sessionId) setSessionId(localStorage.getItem('sessionId'));
       console.log("Token và ID phiên được tải từ localStorage:", localStorage.getItem('sessionId'));
    }
  }, [accessToken, sessionId, API_BASE_URL, fetchWithNgrokHeaders]);

  useEffect(() => {
    fetchToken();
  }, [fetchToken]);

  const resetASQProcess = () => {
    setChildInfo(null); setAsqUserAnswers(null); setParentInfo(null);
    setAgeInfo(null); setAsqQuestionnaireData(null);
    setProcessedAsqResults(null); setLlmAsqSolutions(null);
    setInitialChatbotMessage(null); setInitialMessageFetchedOrUsed(false);
    setShowExtraFields(false); setStep(1);
  };

  const handleChildInfoChange = (fieldName, value) => {
    setChildInfo((prev) => {
      const updated = { ...prev, [fieldName]: value };
      if (fieldName === "birthDate") {
        const birth = new Date(value); const today = new Date();
        if (isNaN(birth.getTime()) || value === '') { updated.childAgeInDays = null; if (value !== '') console.warn("Ngày sinh không hợp lệ");}
        else { birth.setHours(0,0,0,0); today.setHours(0,0,0,0); const ageInDays = Math.floor((today - birth) / (1000 * 60 * 60 * 24)); updated.childAgeInDays = ageInDays >= 0 ? ageInDays : null; console.log(`Số ngày tuổi của trẻ: ${updated.childAgeInDays}`); }
      }
      if (fieldName === "pre-result" && value === "Không") { const fieldsToClear = ["result", "resultDate", "hospital", "doctor", "pre-test"]; fieldsToClear.forEach((key) => { delete updated[key]; });}
      return updated;
    });
    if (fieldName === "pre-result") setShowExtraFields(value === "Có");
  };

  const handleChildInfoSubmit = async (data) => {
    setChildInfo(data);
    setAsqUserAnswers(null); setAgeInfo(null); setAsqQuestionnaireData(null);
    setProcessedAsqResults(null); setLlmAsqSolutions(null);
    setInitialChatbotMessage(null); setInitialMessageFetchedOrUsed(false);

    const ageInDays = data.childAgeInDays;
    if (ageInDays === undefined || ageInDays === null || ageInDays < 0) { alert("Vui lòng nhập ngày sinh hợp lệ của trẻ."); return; }
    try {
      const apiUrl = `${API_BASE_URL}/asq/form?age_in_days=${ageInDays}`;
      // Use fetchWithNgrokHeaders. GET requests generally don't have 'Content-Type' or 'Authorization' unless specifically required.
      // The helper will add 'ngrok-skip-browser-warning'.
      const res = await fetchWithNgrokHeaders(apiUrl, { method: 'GET' });
      console.log("Response from /asq/form:", res);
      if (!res.ok) { const errData = await res.json().catch(()=>{ return {detail: "Lỗi không xác định từ server khi parse lỗi."}}); throw new Error(errData?.detail || `Lỗi HTTP: ${res.status}`);}
      const questionnaireData = await res.json();
      setAsqQuestionnaireData(questionnaireData); setAgeInfo(questionnaireData.age); setStep(2);
    } catch (error) { console.error("Lỗi khi tải form ASQ:", error); alert(`Lỗi tải form ASQ: ${error.message}.`); }
  };

  const handleASQTestSubmit = (userAnswers) => { setAsqUserAnswers(userAnswers); setStep(3); };

  const fetchInitialChatbotEngagement = useCallback(async () => {
    if (sessionId && accessToken && !initialMessageFetchedOrUsed) {
      try {
        const response = await fetchWithNgrokHeaders(`${API_BASE_URL}/chatbot/asq_initial_engagement`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }, // Authorization will be added by fetchWithNgrokHeaders
        });
        if (!response.ok) { const errData = await response.json().catch(()=>{}); console.error("Lỗi khi lấy nhận xét ban đầu:", errData?.detail || `HTTP error: ${response.status}`);}
        else {
            const data = await response.json();
            if (data.error) console.error("Lỗi từ backend (nhận xét ban đầu):", data.error);
            else { setInitialChatbotMessage(data.initial_remark || null); setLlmAsqSolutions(data.asq_solutions || null); console.log("Dữ liệu nhận xét và giải pháp ban đầu từ LLM:", data); }
        }
      } catch (error) { console.error("Lỗi mạng/phân tích khi lấy nhận xét ban đầu:", error);
      } finally { setInitialMessageFetchedOrUsed(true); }
    }
  }, [sessionId, accessToken, initialMessageFetchedOrUsed, API_BASE_URL, fetchWithNgrokHeaders]);

  const handleParentInfoSubmit = async (parentData) => {
    setParentInfo(parentData);
    if (childInfo && asqUserAnswers && parentData && sessionId && accessToken && asqQuestionnaireData) {
      const payload = {
        age_at_test_months: Math.floor((childInfo.childAgeInDays || 0) / 30.44),
        questionnaire_title: asqQuestionnaireData.age?.title,
        ...asqUserAnswers,
      };
      try {
        const res = await fetchWithNgrokHeaders(`${API_BASE_URL}/asq/result`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }, // Authorization will be added by fetchWithNgrokHeaders
          body: JSON.stringify(payload),
        });
        if (!res.ok) { const errData = await res.json().catch(()=>{}); throw new Error(errData?.detail || `Lỗi HTTP: ${res.status}`);}
        const results = await res.json();
        setProcessedAsqResults(results);
        await fetchInitialChatbotEngagement();
        setStep(4);
      } catch (error) { console.error("Lỗi khi gửi kết quả ASQ:", error); alert(`Lỗi xử lý kết quả ASQ: ${error.message}.`);}
    } else { alert("Thiếu thông tin để xử lý kết quả ASQ. Vui lòng kiểm tra lại các bước và phiên làm việc.");}
  };
  
  const formFields = [
    { id: "ff1", type: "text", name: "fullName", label: "Họ và tên trẻ:", onChange: handleChildInfoChange, required: true },
    { id: "ff2", type: "date", name: "birthDate", label: "Ngày sinh của trẻ:", onChange: handleChildInfoChange, required: true },
    { id: "ff3", type: "select", name: "location", label: "Tỉnh/Thành phố hiện tại:", options: provinces, onChange: handleChildInfoChange },
    { id: "ff4", type: "radio", name: "gender", label: "Giới tính của trẻ:", options: ["Nam", "Nữ", "Khác"], onChange: handleChildInfoChange },
    { id: "ff5", type: "radio", name: "pre-birth", label: "Trẻ có sinh non không (sinh trước 37 tuần)?", options: ["Không", "Có"], onChange: handleChildInfoChange },
    { id: "ff6", type: "radio", name: "pre-result", label: "Trẻ đã có kết quả chẩn đoán trước đó về các rối loạn phát triển (ví dụ: tự kỷ, chậm phát triển, tăng động giảm chú ý,...):", options: ["Không", "Có"], onChange: handleChildInfoChange },
  ];
  const extraFields = [
    { id: "ef1", type: "select", name: "result", label: "Kết quả chẩn đoán cụ thể (nếu có):", options: diagnosisResults, onChange: handleChildInfoChange },
    { id: "ef2", type: "date", name: "resultDate", label: "Ngày chẩn đoán (nếu có):", onChange: handleChildInfoChange },
    { id: "ef3", type: "select", name: "hospital", label: "Nơi chẩn đoán (nếu có):", options: hospitals, onChange: handleChildInfoChange },
    { id: "ef4", type: "select", name: "doctor", label: "Người chẩn đoán (nếu có):", options: doctors, onChange: handleChildInfoChange },
    { id: "ef5", type: "radio", name: "pre-test", label: "Trẻ đã được sàng lọc bằng ASQ-3 hoặc M-CHAT-R/F trước đây chưa?", options: ["Chưa", "Rồi"], onChange: handleChildInfoChange },
  ];

  return (
    <div className="container-page">
      <Header />
      <Routes>
        <Route path="/" element={<Navigate to="/guest/asq3-test" />} />
        <Route path="/guest/asq3-test" element={
            <main><section className="container-content">
              {step === 1 && (<><TitleBox title="BƯỚC 1: THÔNG TIN CỦA TRẺ" /><FormWrapper fields={showExtraFields ? [...formFields, ...extraFields] : formFields} defaultValues={childInfo || {}} onSubmit={handleChildInfoSubmit} buttonText="Tiếp tục" /></>)}
              {step === 2 && asqQuestionnaireData && (<FormASQTest key={`asq-form-${asqQuestionnaireData.age?.title||'d'}`} questionnaireData={asqQuestionnaireData} onBack={(s) => { setAsqUserAnswers(s); setStep(1); }} onSubmit={handleASQTestSubmit} defaultValues={asqUserAnswers||{}} />)}
              {step === 3 && (<><TitleBox title="BƯỚC 3: THÔNG TIN PHỤ HUYNH/NGƯỜI CHĂM SÓC" onBack={() => setStep(2)} /><FormParentInfo defaultValues={parentInfo||{}} onChange={(f,v)=>setParentInfo(p=>({...p,[f]:v}))} onBack={()=>setStep(2)} onSubmit={handleParentInfoSubmit} /></>)}
              {step === 4 && processedAsqResults && childInfo && parentInfo && ageInfo && (<><TitleBox title="KẾT QUẢ SÀNG LỌC PHÁT TRIỂN ASQ-3" subtitle={`(Bộ câu hỏi ${ageInfo.title||processedAsqResults.questionnaire_title})`} /><ResultPage childInfo={childInfo} parentInfo={parentInfo} processedAsqResults={processedAsqResults} llmGeneratedSolutions={llmAsqSolutions} onRestartTest={resetASQProcess} sessionId={sessionId} accessToken={accessToken} /></>)} {/* Truyền sessionId và accessToken cho ResultPage nếu nó cần gọi API */}
            </section></main>
          } />
        <Route path="/guest/chatbot" element={<ChatbotPage initialMessage={initialChatbotMessage} sessionId={sessionId} accessToken={accessToken} onInitialMessageShown={() => { setInitialChatbotMessage(null); }} />} />
        <Route path="/guest/predict" element={<Predict1/>} />
        <Route path="/guest/predict/step2" element={<Predict2 />} />
        <Route path="/guest/predict/step3" element={<Predict3 />} />

      </Routes>
      <div className="container-footer"><Footer /></div>
      <FeedbackButton />
    </div>
  );
}
export default App;