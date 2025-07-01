import React, { useRef } from "react";
import "./ResultPage.css";
import Button from "./components/Button/Button";
import { Link, useNavigate } from "react-router-dom";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

const formatDate = (dateStr) => {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return "N/A";
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const domainDisplayMapping = {
  communication: "GIAO TIẾP",
  gross_motor: "VẬN ĐỘNG THÔ",
  fine_motor: "VẬN ĐỘNG TINH",
  problem_solving: "GIẢI QUYẾT VẤN ĐỀ",
  personal_social: "CÁ NHÂN XÃ HỘI",
};
// Function Name: getDotColorForStatus
// Functionality: Returns a specific color based on the developmental status string.
// Input: status (string) - The developmental status string.
// Output: string - The hex color code for the dot.
const getDotColorForStatus = (status) => {
  if (status.includes("CHẬM RÕ RỆT")) {
    return "#757575"; 
  } else if (status.includes("CÓ NGUY CƠ CHẬM")) {
    return "#FFB74D"; 
  } else if (status.includes("BÌNH THƯỜNG")) {
    return "#81C784"; 
  }
  return "#004aad"; 
};

const DevelopmentSummary = ({ sectionsResult }) => {
  if (!sectionsResult || Object.keys(sectionsResult).length === 0) {
    return <p>Không có dữ liệu nhận xét chi tiết.</p>;
  }
  const statusGroups = {
    "PHÁT TRIỂN BÌNH THƯỜNG": [],
    "CÓ NGUY CƠ CHẬM (Cần theo dõi sát)": [],
    "CHẬM RÕ RỆT (Cần đánh giá chuyên sâu)": [],
    "KHÁC": []
  };
  Object.values(sectionsResult).forEach((section) => {
    (statusGroups[section.status] || statusGroups["KHÁC"]).push(section.display_name);
  });
  const normalK = "PHÁT TRIỂN BÌNH THƯỜNG", riskK="CÓ NGUY CƠ CHẬM (Cần theo dõi sát)", delayK="CHẬM RÕ RỆT (Cần đánh giá chuyên sâu)";

  return (
    <div className="development-summary">
      {statusGroups[normalK]?.length > 0 && (<p>Trẻ có trạng thái phát triển <b>BÌNH THƯỜNG</b> ở các lĩnh vực: <b>{statusGroups[normalK].join(", ")}</b>. Điểm số của trẻ trong các lĩnh vực này nằm trong vùng màu <b>XANH LÁ</b>, cho thấy sự phát triển phù hợp với lứa tuổi. Phụ huynh nên tiếp tục tạo điều kiện và khuyến khích trẻ phát huy các kỹ năng này. Nếu có bất kỳ thắc mắc nào, bạn có thể trao đổi thêm với <b>CHATBOT</b> để có thêm gợi ý hoạt động.</p>)}
      {statusGroups[riskK]?.length > 0 && (<p>Trẻ có trạng thái <b>CÓ NGUY CƠ CHẬM</b> ở các lĩnh vực: <b>{statusGroups[riskK].join(", ")}</b>. Điểm số của trẻ trong các lĩnh vực này nằm trong vùng màu <b>CAM</b>. Điều này gợi ý rằng một số kỹ năng của trẻ có thể chưa thành thục hoặc trẻ thực hiện chưa thường xuyên. Phụ huynh nên chú ý theo dõi sát hơn, cung cấp thêm các hoạt động kích thích phù hợp cho các lĩnh vực này và có thể làm lại bài sàng lọc sau một thời gian. Nếu lo lắng, việc tham khảo ý kiến của bác sĩ hoặc chuyên gia phát triển trẻ em là rất cần thiết.</p>)}
      {statusGroups[delayK]?.length > 0 && (<p>Trẻ có trạng thái <b>CHẬM RÕ RỆT</b> ở các lĩnh vực: <b>{statusGroups[delayK].join(", ")}</b>. Điểm số của trẻ trong các lĩnh vực này nằm trong vùng màu <b>XÁM</b>. Điều này cho thấy trẻ có thể đang gặp khó khăn đáng kể so với các bạn cùng tuổi. Phụ huynh nên sớm đưa trẻ đến gặp bác sĩ nhi khoa hoặc các chuyên gia phát triển trẻ em để được đánh giá chuyên sâu, chẩn đoán chính xác và có kế hoạch can thiệp sớm phù hợp.</p>)}
      {statusGroups["KHÁC"]?.length > 0 && (<p>Lưu ý: Có một số lĩnh vực với trạng thái <b>{statusGroups["KHÁC"].join(", ")}</b>. Vui lòng tham khảo ý kiến chuyên gia.</p>)}
    </div>
  );
};

function ResultPage({ childInfo, parentInfo, processedAsqResults, llmGeneratedSolutions, onRestartTest }) {
  const resultRef = useRef();
  const navigate = useNavigate();

  if (!processedAsqResults) {
    return <div className="result-page-loading"><p>Đang tải kết quả, vui lòng chờ...</p></div>;
  }

  const { sections = {}, overall_summary, questionnaire_title, age_at_test_months } = processedAsqResults;

  const lstScores = Object.entries(sections).map(([key, data]) => ({
    field: data.display_name || domainDisplayMapping[key] || key.toUpperCase(),
    score: data.total_score, cutoff: data.cutoff, monitor: data.monitor, status: data.status,
  }));

  const handleDownloadPDF = async () => {
    const elementToCapture = resultRef.current; if (!elementToCapture) return;
    const pdfHeader = elementToCapture.querySelector(".pdf-only-header");
    if (pdfHeader) pdfHeader.style.display = "block";
    await new Promise((resolve) => setTimeout(resolve, 100));
    try {
      const canvas = await html2canvas(elementToCapture, { scale: 2, useCORS: true, logging: false });
      const imgData = canvas.toDataURL("image/png", 1.0);
      const pdf = new jsPDF({ orientation: "p", unit: "mm", format: "a4" });
      const imgProps = pdf.getImageProperties(imgData);
      const pdfWidth = pdf.internal.pageSize.getWidth(); const pdfPageHeight = pdf.internal.pageSize.getHeight();
      const imgHeight = (imgProps.height * pdfWidth) / imgProps.width;
      let heightLeft = imgHeight; let position = 0;
      pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight); heightLeft -= pdfPageHeight;
      while (heightLeft > 0) { position -= pdfPageHeight; pdf.addPage(); pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight); heightLeft -= pdfPageHeight; }
      pdf.save(`ASQ3_KetQua_${childInfo?.fullName?.replace(/\s+/g, '_')||'Tre'}_${new Date().toISOString().slice(0,10)}.pdf`);
    } catch (error) { console.error("Lỗi tạo PDF:", error); alert("Lỗi khi tạo file PDF.");
    } finally { if (pdfHeader) pdfHeader.style.display = "none"; }
  };
  
  const handleRestart = () => { if(onRestartTest) onRestartTest(); navigate('/guest/asq3-test'); }

  return (
    <div className="result-page">
      <div className="print-pdf" ref={resultRef}>
        <div className="pdf-only-header" style={{display:"none", textAlign:'center', marginBottom:'20px'}}>
          <h2 className="pdf-title">KẾT QUẢ SÀNG LỌC PHÁT TRIỂN ASQ-3</h2>
          {questionnaire_title && <p className="pdf-subtitle">(Bộ câu hỏi: {questionnaire_title})</p>}
          <p className="pdf-time">Thời gian xuất: {new Date().toLocaleString('vi-VN')}</p>
        </div>
        <section className="section result-section"><h3 className="chapter">1. THÔNG TIN CHUNG</h3><div className="info-grid">
            <div><strong>Họ tên trẻ:</strong> {childInfo?.fullName||'N/A'}</div><div><strong>Ngày sinh:</strong> {formatDate(childInfo?.birthDate)}</div>
            <div><strong>Tuổi (test):</strong> {age_at_test_months!==undefined?`${age_at_test_months} tháng`:'N/A'}</div><div><strong>Giới tính:</strong> {childInfo?.gender||'N/A'}</div>
            <div><strong>SĐT liên hệ:</strong> {parentInfo?.phone||'N/A'}</div><div><strong>Địa chỉ:</strong> {parentInfo?.address||'N/A'}</div>
            <div><strong>Nơi sàng lọc:</strong> {parentInfo?.place||'N/A'}</div><div><strong>Ngày thực hiện:</strong> {new Date().toLocaleDateString('vi-VN')}</div>
        </div></section>
        <section className="section result-section"><h3 className="chapter">2. GIẢI THÍCH KẾT QUẢ</h3>
            <p>ASQ-3 là công cụ sàng lọc sự phát triển của trẻ. Kết quả giúp đánh giá kỹ năng của trẻ so với mốc phát triển theo độ tuổi.</p>
            <div className="legend">
                <p className="legend-item legend-gray"><span className="color-box gray"></span>Vùng XÁM: Chậm phát triển rõ rệt. Cần đánh giá chuyên sâu.</p>
                <p className="legend-item legend-orange"><span className="color-box orange"></span>Vùng CAM: Có nguy cơ chậm. Cần theo dõi, kích thích, có thể đánh giá lại.</p>
                <p className="legend-item legend-green"><span className="color-box green"></span>Vùng XANH LÁ: Phát triển bình thường. Tiếp tục khuyến khích trẻ.</p>
            </div>
        </section>
        <section className="section result-section"><h3 className="chapter">3. ĐIỂM SÀNG LỌC CỦA TRẺ</h3>
            <p><em>Tóm tắt từ hệ thống: {overall_summary}</em></p>
            <table className="score-table">
                <thead><tr><th>Lĩnh vực</th><th>Ngưỡng "Chậm" </th><th>Ngưỡng "Theo dõi" </th><th>Điểm</th><th style={{width:'200px'}}>Trạng thái</th><th style={{width:"250px"}}>Thang điểm (0-60)</th></tr></thead>
                <tbody>{lstScores.map(({field,score,cutoff,monitor,status},idx)=>{
                    const scorePercent = Math.min(Math.max((score/60)*100,0),100); 
                    const cutoffPercent = Math.round((cutoff/60)*100); 
                    const monitorPercent = Math.round((monitor/60)*100);
                    
                    const dotColor = getDotColorForStatus(status);

                    let trackBackground; 
                    if(monitorPercent > cutoffPercent) {
                        trackBackground=`linear-gradient(to right, #BDBDBD ${cutoffPercent}%, #FFB74D ${cutoffPercent}%, #FFB74D ${monitorPercent}%, #81C784 ${monitorPercent}%, #81C784 100%)`;
                    } else { 
                        trackBackground=`linear-gradient(to right, #BDBDBD ${monitorPercent}%, #81C784 ${monitorPercent}%, #81C784 100%)`;
                    }
                    return(
                        <tr key={idx}>
                            <td>{field}</td>
                            <td>{`< ${cutoff.toFixed(0)}`}</td>
                            <td>{`${cutoff.toFixed(0)} - ${monitor.toFixed(0)}`}</td>
                            <td><b>{score.toFixed(0)}</b></td>
                            <td style={{
                                fontWeight: status !== "PHÁT TRIỂN BÌNH THƯỜNG" ? "bold" : "normal",
                                color: dotColor 
                            }}>
                                {status}
                            </td>
                            <td>
                                <div className="slider-container">
                                    <div className="slider-track" style={{background: trackBackground}}>
                                        {[0,10,20,30,40,50,60].map(v=>(<span key={v} className="slider-marker" style={{left:`${(v/60)*100}%`}}>{v}</span>))}
                                    </div>
                                    <div 
                                        className="slider-dot" 
                                        style={{ 
                                            left: `${scorePercent}%`,
                                            backgroundColor: dotColor 
                                        }} 
                                        title={`Điểm: ${score.toFixed(0)}`}
                                    />
                                </div>
                            </td>
                        </tr>
                    );
                })}</tbody>
            </table>
        </section>
        <section className="section result-section"><h3 className="chapter">4. NHẬN XÉT CHUNG</h3><DevelopmentSummary sectionsResult={sections}/></section>
        <section className="section result-section"><h3 className="chapter">5. GỢI Ý VÀ ĐỀ XUẤT TỪ TRỢ LÝ AI</h3>
            {llmGeneratedSolutions ? (<div className="llm-solutions" style={{whiteSpace:"pre-line"}}>{llmGeneratedSolutions.split('\n').map((l,i)=>(<p key={i}>{l}</p>))}</div>) : (<p>Đang tải gợi ý từ trợ lý AI hoặc chưa có gợi ý chi tiết. Bạn có thể trò chuyện với trợ lý để được tư vấn thêm.</p>)}
            <p style={{marginTop:'20px',fontStyle:'italic',fontSize:'0.9em'}}>Lưu ý quan trọng: Kết quả ASQ-3 là công cụ sàng lọc ban đầu, không phải là chẩn đoán y tế. Nếu có bất kỳ lo ngại nào, phụ huynh nên đưa trẻ đến gặp bác sĩ hoặc chuyên gia để được đánh giá và tư vấn cụ thể.</p>
        </section>
      </div>
      <div className="result-buttons">
        <Button onClick={handleDownloadPDF}>Tải kết quả (PDF)</Button>
        <Button onClick={handleRestart} variant="outlined">Làm lại bài Test</Button>
        <Link to="/guest/chatbot"><Button variant="secondary">Trò chuyện với Trợ lý AI</Button></Link>
      </div>
    </div>
  );
}
export default ResultPage;