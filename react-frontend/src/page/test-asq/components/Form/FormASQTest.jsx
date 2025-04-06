import React, { useState } from 'react';
import Button from '../Button/Button';
import './FormASQTest.css';

function FormASQTest({ onBack, onSubmit }) {
  const [answers, setAnswers] = useState({});
  const [viewMode, setViewMode] = useState("all"); // 'all' | 'step'
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);

  const testSections = [
    {
      id: 'A',
      title: 'A. GIAO TIẾP',
      description: 'Hãy chắc chắn thử những hoạt động này cho trẻ',
      questions: [
        { name: 'a_q1', label: 'Trẻ có biết gọi ba mẹ không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'a_q2', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'a_q3', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'a_q4', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'a_q5', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'a_q6', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
      ],
    },
    {
      id: 'B',
      title: 'B. VẬN ĐỘNG THÔ',
      description: 'Hãy thử cho trẻ thực hiện các hoạt động sau',
      questions: [
        { name: 'b_q1', label: 'Trẻ có biết gọi ba mẹ không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'b_q2', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'b_q3', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'b_q4', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'b_q5', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        { name: 'b_q6', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
      ],
    },
    {
        id: 'C',
        title: 'C. VẬN ĐỘNG TINH',
        description: 'Hãy chắc chắn thử những hoạt động này cho trẻ',
        questions: [
            { name: 'c_q1', label: 'Trẻ có biết gọi ba mẹ không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'c_q2', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'c_q3', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'c_q4', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'c_q5', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'c_q6', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        ],
      },
      {
        id: 'D',
        title: 'D. GIẢI QUYẾT VẤN ĐỀ',
        description: 'Hãy chắc chắn thử những hoạt động này cho trẻ',
        questions: [
            { name: 'd_q1', label: 'Trẻ có biết gọi ba mẹ không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'd_q2', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'd_q3', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'd_q4', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'd_q5', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'd_q6', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        ],
      },
      {
        id: 'E',
        title: 'E. CÁ NHÂN XÃ HỘI',
        description: 'Hãy chắc chắn thử những hoạt động này cho trẻ',
        questions: [
            { name: 'e_q1', label: 'Trẻ có biết gọi ba mẹ không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'e_q2', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'e_q3', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'e_q4', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'e_q5', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'e_q6', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        ],
      },
      {
        id: 'F',
        title: 'F. CÂU HỎI CHUNG',
        description: 'Hãy chắc chắn thử những hoạt động này cho trẻ',
        questions: [
            { name: 'f_q1', label: 'Trẻ có biết gọi ba mẹ không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'f_q2', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'f_q3', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'f_q4', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'f_q5', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
            { name: 'f_q6', label: 'Trẻ có phản ứng với âm thanh không?', options: ['CÓ', 'THỈNH THOẢNG', 'CHƯA'] },
        ],
      }
  ];

  const handleChange = (name, value) => {
    setAnswers(prev => ({ ...prev, [name]: value }));
  };

  const handleNextStep = () => {
    const current = testSections[currentSectionIndex];
    const isValid = current.questions.every(q => answers[q.name]);
    if (!isValid) {
      alert("Vui lòng trả lời tất cả câu hỏi trong phần này.");
      return;
    }

    if (currentSectionIndex < testSections.length - 1) {
      setCurrentSectionIndex(prev => prev + 1);
    } else {
      onSubmit({
        answers,
        viewMode,
        completedSection: testSections[currentSectionIndex]?.id
      });
    }
  };

  const renderQuestion = (q, idx) => (
    <div className="question-box" key={q.name}>
      <div className="question-label">
        <strong>Câu {idx + 1}:</strong> {q.label}
      </div>
      <div className="radio-group">
        {q.options.map(opt => (
          <label key={opt} className="radio-option">
            <input
              type="radio"
              name={q.name}
              value={opt}
              checked={answers[q.name] === opt}
              onChange={() => handleChange(q.name, opt)}
            />
            {opt}
          </label>
        ))}
      </div>
    </div>
  );
  const handleCompleteSubmit = () => {
    const allQuestions = testSections.flatMap(section => section.questions);
    const isValid = allQuestions.every(q => answers[q.name]);
  
    if (!isValid) {
      alert("Vui lòng trả lời tất cả các câu hỏi trước khi hoàn tất.");
      return;
    }
  
    // ✅ Tính điểm theo từng lĩnh vực
    const getScore = (value) => {
      if (value === "CÓ") return 10;
      if (value === "THỈNH THOẢNG") return 5;
      return 0;
    };
  
    const lstScores = testSections.slice(0, 5).map(section => {
      const total = section.questions.reduce((sum, q) => {
        const val = answers[q.name];
        return sum + getScore(val);
      }, 0);
      return {
        field: section.title.replace(/^.*?\.\s*/, ""), // ví dụ: "A. GIAO TIẾP" => "GIAO TIẾP"
        score: total
      };
    });
  
    // ✅ Tính tuổi tạm thời (giả định), ví dụ dùng age = 20 (sau này BE tính)
    const age = 20;
  
    // ✅ Gửi về DTO
    onSubmit({
      answers,
      viewMode,
      completedSection: viewMode === "step" ? testSections[currentSectionIndex]?.id : 'ALL',
      age,
      lstScores,
      comment: "Dữ liệu nhận xét sẽ render từ BE"
    });
  };
  


  return (
    <form className="form-questions" onSubmit={(e) => e.preventDefault()}>
      <div className="instruction-box">
        <p><strong>Hướng dẫn làm bài:</strong></p>
        <ul>
          <li><span className="text-blue">CÓ</span>: Trẻ thực hiện thường xuyên</li>
          <li><span className="text-blue">THỈNH THOẢNG</span>: Trẻ đôi khi làm được</li>
          <li><span className="text-blue">CHƯA</span>: Trẻ chưa thực hiện được</li>
        </ul>
        <p>Hãy để trẻ thử từng hoạt động trước khi đánh dấu.</p>
      </div>

      {/* ✅ Chế độ làm bài */}
      <div className="view-mode-wrapper">
        <label>Chế độ làm bài:</label>
        <select
          value={viewMode}
          onChange={(e) => {
            setViewMode(e.target.value);
            setCurrentSectionIndex(0); // Reset về đầu
          }}
        >
          <option value="all">Toàn bộ bài</option>
          <option value="step">Từng phần</option>
        </select>
      </div>

      {/* ✅ Hiển thị nội dung câu hỏi */}
      {viewMode === "all" && (
  <>
    {testSections.map((section, idx) => {
      return (
        <div className="question-section" key={section.id}>
          <h3>{section.title}</h3>
          <p>{section.description}</p>
          {section.questions.map((q, qIdx) => renderQuestion(q, qIdx))}
        </div>
      );
    })}
  </>
)}




      {viewMode === "step" && (
        <div className="question-section">
          <h3>{testSections[currentSectionIndex].title}</h3>
          <p>{testSections[currentSectionIndex].description}</p>
          {testSections[currentSectionIndex].questions.map((q, qIdx) => renderQuestion(q, qIdx))}
        </div>
      )}

      {/* ✅ Nút điều hướng */}
      <div className="container-button">
        <Button type="button" onClick={onBack}>QUAY LẠI</Button>
        {viewMode === "all" ? (
          <Button type="button" onClick={handleCompleteSubmit}>HOÀN TẤT</Button>
        ) : (
          <Button type="button" onClick={handleNextStep}>
            {currentSectionIndex < testSections.length - 1 ? "TIẾP TỤC" : "HOÀN TẤT"}
          </Button>
        )}
      </div>
    </form>
  );
}

export default FormASQTest;