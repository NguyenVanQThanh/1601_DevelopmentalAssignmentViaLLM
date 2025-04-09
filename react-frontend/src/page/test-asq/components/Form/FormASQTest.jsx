import Button from "../Button/Button";
import "./FormASQTest.css";
import React, { useState, useEffect } from "react";
import TitleBox from "../../../../components/Title_box/TitleBox";

function FormASQTest({ onBack, onSubmit, defaultValues = {} }) {
  const defaultAnswers = defaultValues.answers || {};

  const [answers, setAnswers] = useState(defaultAnswers);
  const [viewMode, setViewMode] = useState(defaultValues.viewMode || "all");
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [completedSection, setCompletedSection] = useState(
    defaultValues.completedSection || []
  );
  const [age, setAge] = useState(defaultValues.age || null);
  const [testSections, setTestSections] = useState([]); // State để lưu dữ liệu fetch từ API
  const [loading, setLoading] = useState(true); // State để xử lý trạng thái loading
  const [error, setError] = useState(null); // State để xử lý lỗi
  const [result, setResult] = useState(null); // State để lưu kết quả từ backend

  // Fetch dữ liệu từ endpoint /form khi component được mount
  useEffect(() => {
    const fetchFormData = async () => {
      try {
        setLoading(true);
        const response = await fetch("http://127.0.0.1:8000/form");
        console.log("Response từ API /form:", response);
        if (!response.ok) {
          throw new Error("Failed to fetch form data");
        }
        const data = await response.json();
        console.log("Dữ liệu từ API /form sau khi parse:", data);

        // Định nghĩa title cho từng section
        const titleMapping = {
          communication: "A. GIAO TIẾP",
          gross_motor: "B. VẬN ĐỘNG THÔ",
          fine_motor: "C. VẬN ĐỘNG TINH",
          problem_solving: "D. GIẢI QUYẾT VẤN ĐỀ",
          personal_social: "E. CÁ NHÂN XÃ HỘI",
        };

        // Lấy các key từ data.question (communication, gross_motor, ...)
        const apiKeys = Object.keys(data.question);

        // Chuyển đổi dữ liệu từ API thành định dạng testSections
        const sections = apiKeys.map((key) => ({
          apiKey: key, // Lưu apiKey để sử dụng trực tiếp
          title: titleMapping[key],
          content: data.question[key],
        }));
        setTestSections(sections);
        console.log("Test Sections:", sections); // Log testSections để kiểm tra

        setAge(data.age); // Lưu thông tin tuổi từ API
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchFormData();
  }, []);

  useEffect(() => {
    setAnswers(defaultValues.answers || {});
    setCompletedSection(defaultValues.completedSection || []);
    setViewMode(defaultValues.viewMode || "all");
  }, [defaultValues]);

  const handleChange = (name, value) => {
    setAnswers((prev) => {
      const updatedAnswers = { ...prev, [name]: value };
      console.log(`Radio button clicked - Question: ${name}, Answer: ${value}`);
      console.log("Current answers state:", updatedAnswers);
      return updatedAnswers;
    });
  };

  const handleNextStep = () => {
    const current = testSections[currentSectionIndex];
    const sectionKey = current.apiKey; // Sử dụng apiKey trực tiếp
    const isValid = current.content.questions.every((q) => {
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
      handleCompleteSubmit();
    }
  };

  const renderQuestion = (q, idx, sectionApiKey) => {
    const questionName = `${sectionApiKey}_q${q.id}`; // Sử dụng apiKey trực tiếp
    console.log(`Rendering question: ${questionName}`); // Log để kiểm tra câu hỏi được render
    return (
      <div className="question-box" key={questionName}>
        <div className="question-label">
          <strong>Câu {idx + 1}:</strong> {q.text}
          {q.note && (
            <p className="question-note">
              <em>{q.note}</em>
            </p>
          )}
        </div>
        <div className="radio-group">
          {q.options.map((optRaw) => {
            const opt = optRaw.trim();
            return (
              <label key={opt} className="radio-option">
                <input
                  type="radio"
                  name={questionName}
                  value={opt}
                  checked={answers[questionName] === opt}
                  onChange={() => handleChange(questionName, opt)}
                  disabled={result !== null} // Vô hiệu hóa nếu đã có kết quả
                />
                {opt}
              </label>
            );
          })}
        </div>
      </div>
    );
  };

  const handleCompleteSubmit = async () => {
    const allQuestions = testSections.flatMap((section) =>
      section.content.questions.map((q) => ({
        name: `${section.apiKey}_q${q.id}`,
      }))
    );
    const isValid = allQuestions.every((q) => {
      const answer = answers[q.name];
      return answer && ["Có", "Thỉnh Thoảng", "Chưa"].includes(answer);
    });

    if (!isValid) {
      alert("Vui lòng trả lời tất cả các câu hỏi trước khi hoàn tất.");
      return;
    }

    // Tạo formattedData với các key lấy từ apiKey
    const formattedData = {};
    testSections.forEach((section) => {
      formattedData[section.apiKey] = [];
    });

    console.log("Answers trước khi tạo formattedData:", answers); // Log answers để kiểm tra

    for (const [key, value] of Object.entries(answers)) {
      // Log key để kiểm tra
      console.log(`Processing key: ${key}`);

      // Split key bằng "_q"
      const parts = key.split("_q");
      console.log(`Split result for key ${key}:`, parts);

      if (parts.length !== 2) {
        console.log(`Invalid key format: ${key}`);
        continue;
      }

      const sectionKey = parts[0];
      const questionIdPart = parts[1];
      const questionId = parseInt(questionIdPart, 10);

      console.log(
        `Processing answer - Key: ${key}, SectionKey: ${sectionKey}, QuestionIdPart: ${questionIdPart}, QuestionId: ${questionId}`
      ); // Log chi tiết quá trình xử lý

      if (formattedData[sectionKey] && !isNaN(questionId)) {
        formattedData[sectionKey].push({
          id: questionId,
          answer: value,
        });
      } else {
        console.log(
          `Skipping answer - SectionKey: ${sectionKey}, QuestionId: ${questionId}`
        ); // Log nếu bỏ qua câu trả lời
      }
    }

    // Kiểm tra xem có dữ liệu hợp lệ không
    const hasValidData = Object.values(formattedData).some(
      (section) => section.length > 0
    );
    if (!hasValidData) {
      setError("Không có dữ liệu hợp lệ để gửi. Vui lòng kiểm tra lại.");
      return;
    }

    // In dữ liệu gửi đi để debug
    console.log("Formatted Data gửi đi:", formattedData);

    // Gửi request tới endpoint /form/result
    try {
      const response = await fetch("http://127.0.0.1:8000/form/result", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formattedData),
      });

      console.log("Response từ API /form/result:", response);
      if (!response.ok) {
        const errorData = await response.json();
        console.log("Response lỗi từ backend:", errorData);
        throw new Error(`Failed to submit form: ${errorData.detail}`);
      }

      const resultData = await response.json();
      console.log("Result Data từ API /form/result:", resultData); // Log kết quả từ API
      setResult(resultData); // Lưu kết quả từ backend
      console.log("Result state sau khi set:", resultData); // Log state sau khi set

      // Gửi kết quả qua onSubmit dưới dạng resultTest
      onSubmit({
        resultTest: resultData,
      });
    } catch (err) {
      console.error("Lỗi khi gửi request tới /form/result:", err); // Log lỗi nếu có
      setError(err.message);
    }
  };

  const handleBack = () => {
    if (viewMode === "step" && currentSectionIndex > 0) {
      setCurrentSectionIndex((prev) => prev - 1);
    } else {
      onBack({
        answers,
        viewMode,
        age,
        completedSection,
        comment: "Dữ liệu nhận xét sẽ render từ BE",
      });
    }
  };

  if (loading) {
    return <div>Đang tải dữ liệu...</div>;
  }

  if (error) {
    return <div>Lỗi: {error}</div>;
  }

  return (
    <div>
      <form className="form-questions" onSubmit={(e) => e.preventDefault()}>
        <TitleBox
          title={`LÀM BÀI SÀNG LỌC ĐÁNH GIÁ PHÁT TRIỂN THEO ĐỘ TUỔI ASQ-3`}
          subtitle={`(${age?.title || "Bộ câu hỏi"})`}
          onBack={handleBack}
        />
        <div className="instruction-box">
          <p>
            <strong>Hướng dẫn làm bài:</strong>
          </p>
          <ul>
            <li>
              <span className="text-blue">CÓ</span>: Trẻ thực hiện thường xuyên
            </li>
            <li>
              <span className="text-blue">THỈNH THOẢNG</span>: Trẻ đôi khi làm
              được
            </li>
            <li>
              <span className="text-blue">CHƯA</span>: Trẻ chưa thực hiện được
            </li>
          </ul>
          <p>Hãy để trẻ thử từng hoạt động trước khi đánh dấu.</p>
        </div>

        {/* Chế độ làm bài */}
        <div className="view-mode-wrapper">
          <label>Chế độ làm bài:</label>
          <select
            value={viewMode}
            onChange={(e) => {
              setViewMode(e.target.value);
              setCurrentSectionIndex(0);
            }}
            disabled={result !== null} // Vô hiệu hóa nếu đã có kết quả
          >
            <option value="all">Toàn bộ bài</option>
            <option value="step">Từng phần</option>
          </select>
        </div>

        {/* Hiển thị nội dung câu hỏi */}
        {viewMode === "all" && (
          <>
            {testSections.map((section) => (
              <div className="question-section" key={section.apiKey}>
                <h3>{section.title}</h3>
                {section.content.questions.map((q, qIdx) =>
                  renderQuestion(q, qIdx, section.apiKey)
                )}
              </div>
            ))}
          </>
        )}

        {viewMode === "step" && (
          <div className="question-section">
            <h3>{testSections[currentSectionIndex].title}</h3>
            {testSections[currentSectionIndex].content.questions.map((q, qIdx) =>
              renderQuestion(q, qIdx, testSections[currentSectionIndex].apiKey)
            )}
          </div>
        )}

        {/* Nút điều hướng */}
        {!result && (
          <div className="container-button">
            <Button type="button" onClick={handleBack}>
              {viewMode === "step" && currentSectionIndex > 0
                ? "QUAY VỀ PHẦN TRƯỚC"
                : "QUAY LẠI"}
            </Button>
            {viewMode === "all" ? (
              <Button type="button" onClick={handleCompleteSubmit}>
                HOÀN TẤT
              </Button>
            ) : (
              <Button type="button" onClick={handleNextStep}>
                {currentSectionIndex < testSections.length - 1
                  ? "TIẾP TỤC"
                  : "HOÀN TẤT"}
              </Button>
            )}
          </div>
        )}
      </form>
    </div>
  );
}

export default FormASQTest;