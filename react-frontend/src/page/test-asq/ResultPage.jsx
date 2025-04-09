import './ResultPage.css';
import Button from './components/Button/Button';
import { useRef } from 'react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

function ResultPage({ childInfo, parentInfo, testResult }) {
  const resultRef = useRef();
  console.log(testResult);
  // Chuyển đổi testResult (resultTest) thành lstScores
  const lstScores = testResult
  ? Object.entries(testResult.resultTest).map(([section, data]) => {
    const sectionMapping = {
      communication: "GIAO TIẾP",
      gross_motor: "VẬN ĐỘNG THÔ",
      fine_motor: "VẬN ĐỘNG TINH",
      problem_solving: "GIẢI QUYẾT VẤN ĐỀ",
      personal_social: "CÁ NHÂN XÃ HỘI",
    };
    return {
      field: sectionMapping[section] || section.toUpperCase(),
      score: data.total_score,
      cutoff: data.cutoff,
      max: data.max,
      status: data.status,
    };
  })
  : [];
  console.log(lstScores);

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const [year, month, day] = dateStr.split('-');
    return `${day}/${month}/${year}`;
  };

  const handleDownloadPDF = async () => {
    const element = resultRef.current;
    const pdfHeader = element.querySelector('.pdf-only-header');

    // Tạm thời hiển thị tiêu đề
    pdfHeader.style.display = 'block';

    // Đợi một chút để DOM cập nhật (html2canvas cần render đúng)
    await new Promise(resolve => setTimeout(resolve, 200));

    // Tạo canvas từ DOM đã hiển thị
    const canvas = await html2canvas(element, { scale: 2 });
    const imgData = canvas.toDataURL('image/png');

    const pdf = new jsPDF('p', 'mm', 'a4');
    const imgProps = pdf.getImageProperties(imgData);
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;

    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save('ASQ3_KetQua.pdf');

    // Ẩn lại tiêu đề
    pdfHeader.style.display = 'none';
  };

  return (
    <div className="result-page">
      <div className="print-pdf" ref={resultRef}>
        <div className="pdf-only-header">
          <h2 className="pdf-title">Kết quả bài sàng lọc đánh giá phát triển theo độ tuổi ASQ-3</h2>
          <p className="pdf-time">Thời gian: {new Date().toLocaleString()}</p>
        </div>

        {/* 1. THÔNG TIN TRẺ */}
        <section className="section">
          <h3 className="chapter">1. THÔNG TIN CHUNG</h3>
          <div className="info-grid">
            <div><strong>Họ và tên trẻ:</strong> {childInfo.fullName}</div>
            <div><strong>Ngày sinh:</strong> {formatDate(childInfo.birthDate)}</div>
            <div><strong>SĐT liên hệ:</strong> {parentInfo.phone}</div>
            <div><strong>Nơi sàng lọc:</strong> {parentInfo.place}</div>
            <div><strong>Ngày thực hiện:</strong> {new Date().toLocaleDateString()}</div>
          </div>
        </section>

        {/* 2. GIẢI THÍCH */}
        <section className="section">
          <h3 className="chapter">2. GIẢI THÍCH VỀ SÀNG LỌC ASQ-3</h3>
          <p>ASQ-3 là bộ sàng lọc chuẩn dành cho cha mẹ/ người chăm sóc để tự điền nhằm sàng lọc sự phát triển của trẻ nhỏ...</p>
          <div className="legend">
            <p className="lv1">- Vùng điểm thể hiện trẻ đang gặp khó khăn - CHẬM PHÁT TRIỂN</p>
            <p className="lv2">- Vùng điểm thể hiện trẻ cần được theo dõi thêm và làm sàng lọc lại do một số kỹ năng chưa thành thục - CẦN THEO DÕI </p>
            <p className="lv3">- Vùng điểm thể hiện trẻ có sự phát triển bình thường - BÌNH THƯỜNG</p>
          </div>
        </section>

        {/* 3. ĐIỂM */}
        <section className="section">
          <h3 className="chapter">3. ĐIỂM CỦA TRẺ SAU KHI SÀNG LỌC</h3>
          <table className="score-table">
            <thead>
              <tr>
                <th>Lĩnh vực</th>
                <th>Ngưỡng điểm</th>
                <th>Điểm tối đa</th>
                <th>Điểm của trẻ</th>
                <th>Thang chuẩn 0 - 60</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {Array.isArray(lstScores) && lstScores.length > 0 ? (
                lstScores.map(({ field, score, cutoff, max, status }, idx) => {
                  const leftPercent = Math.min(Math.max((score / 60) * 100, 0), 100);
                  return (
                    <tr key={idx}>
                      <td>{field}</td>
                      <td>{cutoff}</td>
                      <td>{max}</td>
                      <td>{`${score}`}</td>
                      <td>
                        <div className="slider-container">
                          <div className="slider-track"></div>
                          <div
                            className="slider-dot"
                            style={{ left: `${leftPercent}%` }}
                            title={`Điểm: ${score}`}
                          />
                        </div>
                        <div style={{ marginTop: 4, textAlign: 'center' }}>{score}</div>
                      </td>
                      <td>{status}</td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="6">Không có dữ liệu điểm sàng lọc</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        {/* 4 + 5 */}
        <section className="section">
          <h3 className="chapter">4. KẾT QUẢ DỰ ĐOÁN MỨC ĐỘ PHÁT TRIỂN CỦA TRẺ</h3>
          <p>..............</p>
          <h3 className="chapter">5. ĐỀ XUẤT GIẢI PHÁP</h3>
          <p>..............</p>
        </section>
      </div>

      <div className="result-buttons">
        <Button onClick={handleDownloadPDF}>Tải kết quả</Button>
        <Button>Xem kết quả qua email</Button>
      </div>
    </div>
  );
}

export default ResultPage;