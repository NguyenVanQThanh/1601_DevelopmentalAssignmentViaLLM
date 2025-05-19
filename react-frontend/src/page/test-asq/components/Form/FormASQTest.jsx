// FormASQTest.jsx
import React, { useState, useEffect } from "react";
import TitleBox from "../../../../components/Title_box/TitleBox"; // Điều chỉnh đường dẫn nếu cần
import Button from "../Button/Button"; // Đảm bảo import Button
import "./FormASQTest.css"; // Đảm bảo file CSS này tồn tại

// Import images (giữ nguyên logic của bạn)
const imageModules = import.meta.glob(
  "../../../../assets/images/*.{png,jpg,jpeg,svg}",
  { eager: true }
);
const images = {};
for (const path in imageModules) {
  const fileName = path.split("/").pop();
  images[fileName] = imageModules[path].default;
}

// Thêm childAgeInDaysProp nếu bạn vẫn cần nó ở đây
function FormASQTest({ onBack, onSubmit, defaultValues = {}, questionnaireData, childAgeInDaysProp }) { 
  const defaultAnswers = defaultValues.answers || defaultValues || {}; // defaultValues có thể là asqUserAnswers trực tiếp

  const [answers, setAnswers] = useState(defaultAnswers);
  const [viewMode, setViewMode] = useState("all"); // Mặc định hoặc lấy từ defaultValues nếu có
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  // const [completedSection, setCompletedSection] = useState(defaultValues?.completedSection || []); // Có thể không cần thiết nếu xử lý đơn giản hơn
  
  const [ageInfo, setAgeInfo] = useState(null); // Thông tin tuổi từ questionnaireData
  const [testSections, setTestSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // const [result, setResult] = useState(null); // State này có vẻ không được dùng để kiểm soát UI trong form này

  useEffect(() => {
    setLoading(true); // Bắt đầu loading
    setError(null);
    if (questionnaireData && questionnaireData.question && questionnaireData.age) {
      setAgeInfo(questionnaireData.age);

      const titleMapping = {
        communication: "A. GIAO TIẾP",
        gross_motor: "B. VẬN ĐỘNG THÔ",
        fine_motor: "C. VẬN ĐỘNG TINH",
        problem_solving: "D. GIẢI QUYẾT VẤN ĐỀ",
        personal_social: "E. CÁ NHÂN XÃ HỘI",
      };

      const apiKeys = Object.keys(questionnaireData.question);
      const sections = apiKeys.map((key) => ({
        apiKey: key,
        title: titleMapping[key] || key.replace(/_/g, ' ').toUpperCase(), // Xử lý title mặc định tốt hơn
        content: questionnaireData.question[key],
      }));

      setTestSections(sections);
      setLoading(false);
    } else {
      setError("Không có dữ liệu bộ câu hỏi ASQ hợp lệ để hiển thị.");
      setLoading(false);
    }
  }, [questionnaireData]); // Phụ thuộc vào questionnaireData

  const handleChange = (name, value) => {
    setAnswers((prev) => ({ ...prev, [name]: value }));
  };

  const handleNextStep = () => {
    if (viewMode !== "step" || currentSectionIndex >= testSections.length) return;

    const currentSection = testSections[currentSectionIndex];
    const sectionKey = currentSection.apiKey;
    const isValid = currentSection.content.questions.every((q) => {
      const answer = answers[`${sectionKey}_q${q.id}`];
      return answer && ["Có", "Thỉnh Thoảng", "Chưa"].includes(answer);
    });

    if (!isValid) {
      alert("Vui lòng trả lời tất cả câu hỏi trong phần này.");
      return;
    }

    if (currentSectionIndex < testSections.length - 1) {
      setCurrentSectionIndex((prev) => prev + 1);
    } else {
      handleCompleteSubmit(); // Gọi submit khi ở section cuối cùng
    }
  };

  const renderQuestion = (q, idx, sectionApiKey) => {
    const questionName = `${sectionApiKey}_q${q.id}`;
    return (
      <div className="question-box" key={questionName}>
        <div className="question-content">
          <div className="question-text">
            <div className="question-label"><strong>Câu {idx + 1}:</strong> {q.text}
              {q.note && (<p className="question-note"><em>({q.note})</em></p>)}
            </div>
            <div className="radio-group">
              {q.options.map((optRaw) => {
                const opt = optRaw.trim();
                return (
                  <label key={opt} className="radio-option">
                    <input type="radio" name={questionName} value={opt}
                      checked={answers[questionName] === opt}
                      onChange={() => handleChange(questionName, opt)}
                    /> {opt}
                  </label>
                );
              })}
            </div>
          </div>
          {q.image_filepath && images[q.image_filepath] && (
            <div className="question-image"><img src={images[q.image_filepath]} alt={`Ảnh minh họa cho câu ${q.id}`} /></div>
          )}
        </div>
      </div>
    );
  };

  const handleCompleteSubmit = () => {
    // Kiểm tra tất cả câu hỏi trong tất cả sections nếu viewMode là 'all'
    // hoặc tất cả câu hỏi trong section hiện tại nếu viewMode là 'step' và đã ở section cuối
    const allQuestionsInSection = testSections.flatMap((section) =>
        section.content.questions.map((q) => ({
            name: `${section.apiKey}_q${q.id}`,
        }))
    );

    const allAnswered = allQuestionsInSection.every((q) => {
        const answer = answers[q.name];
        return answer && ["Có", "Thỉnh Thoảng", "Chưa"].includes(answer);
    });

    if (!allAnswered) {
      alert("Vui lòng trả lời tất cả các câu hỏi trong bài test trước khi hoàn tất.");
      return;
    }

    // Tạo đối tượng DTO để gửi lên App.jsx
    // DTO này sẽ có dạng { communication: [{id:1, answer:"Có"}, ...], gross_motor: [...], ... }
    const submissionDTO = {};
    testSections.forEach(section => {
        submissionDTO[section.apiKey] = section.content.questions.map(q => ({
            id: q.id,
            answer: answers[`${section.apiKey}_q${q.id}`] || "Chưa" // Mặc định là "Chưa" nếu không có câu trả lời (dù đã validate ở trên)
        }));
    });

    console.log("Submitting ASQ answers DTO:", submissionDTO);
    onSubmit(submissionDTO); // Gửi DTO này lên App.jsx
  };

  const handleBack = () => {
    if (viewMode === "step" && currentSectionIndex > 0) {
      setCurrentSectionIndex((prev) => prev - 1);
    } else {
      // Tạo snapshot của các câu trả lời hiện tại để truyền về App.jsx
      const snapshotAnswers = { ...answers };
      onBack(snapshotAnswers); // Truyền chỉ các câu trả lời về
    }
  };


  if (loading) return <div>Đang tải bộ câu hỏi ASQ...</div>;
  if (error) return <div>Lỗi: {error}</div>;
  if (!testSections || testSections.length === 0) return <div>Không có câu hỏi nào để hiển thị.</div>;

  return (
    <div> {/* Bọc bởi một div cha */}
      <form className="form-questions" onSubmit={(e) => e.preventDefault()}>
        <TitleBox
          title={`BƯỚC 2: LÀM BÀI SÀNG LỌC ASQ-3`}
          subtitle={`( ${ageInfo?.title || "Bộ câu hỏi theo độ tuổi"} )`}
          // Nút back chỉ có tác dụng khi không phải là section đầu tiên ở chế độ step, hoặc luôn có ở chế độ all
          showBackButton={viewMode === "all" || currentSectionIndex > 0}
          onBack={handleBack}
        />
        <div className="instruction-box">
          <p><strong>Hướng dẫn làm bài:</strong></p>
          <ul>
            <li><span className="text-blue">CÓ</span>: Trẻ thực hiện được hoạt động này một cách độc lập và thường xuyên.</li>
            <li><span className="text-blue">THỈNH THOẢNG</span>: Trẻ đang tập làm hoặc thỉnh thoảng mới làm được hoạt động này.</li>
            <li><span className="text-blue">CHƯA</span>: Trẻ chưa thực hiện được hoạt động này.</li>
          </ul>
          <p>Hãy cho trẻ thử từng hoạt động trước khi bạn đánh dấu vào ô trả lời.</p>
        </div>

        <div className="view-mode-wrapper">
          <label htmlFor="viewModeSelect">Chế độ làm bài:</label>
          <select
            id="viewModeSelect"
            value={viewMode}
            onChange={(e) => { setViewMode(e.target.value); setCurrentSectionIndex(0); }}
          >
            <option value="all">Toàn bộ bài</option>
            <option value="step">Từng phần</option>
          </select>
        </div>

        {viewMode === "all" && testSections.map((section) => (
          <div className="question-section" key={section.apiKey}>
            <h3>{section.title}</h3>
            {section.content.questions.map((q, qIdx) => renderQuestion(q, qIdx, section.apiKey))}
          </div>
        ))}

        {viewMode === "step" && testSections.length > 0 && currentSectionIndex < testSections.length && (
          <div className="question-section">
            <h3>{testSections[currentSectionIndex].title}</h3>
            {testSections[currentSectionIndex].content.questions.map((q, qIdx) =>
              renderQuestion(q, qIdx, testSections[currentSectionIndex].apiKey)
            )}
          </div>
        )}

        <div className="container-button">
          <Button type="button" onClick={handleBack} variant="outlined">
            {viewMode === "step" && currentSectionIndex > 0 ? "PHẦN TRƯỚC" : "QUAY LẠI"}
          </Button>
          {viewMode === "all" ? (
            <Button type="button" onClick={handleCompleteSubmit}>HOÀN TẤT BÀI TEST</Button>
          ) : (
            <Button type="button" onClick={handleNextStep}>
              {currentSectionIndex < testSections.length - 1 ? "PHẦN TIẾP THEO" : "HOÀN TẤT BÀI TEST"}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

export default FormASQTest;