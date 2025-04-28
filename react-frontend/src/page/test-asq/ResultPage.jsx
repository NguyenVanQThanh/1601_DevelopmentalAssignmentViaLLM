import "./ResultPage.css";
import Button from "./components/Button/Button";
import { useRef } from "react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

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
    if (!dateStr) return "";
    const [year, month, day] = dateStr.split("-");
    return `${day}/${month}/${year}`;
  };

  const handleDownloadPDF = async () => {
    const element = resultRef.current;
    const pdfHeader = element.querySelector(".pdf-only-header");

    // Tạm thời hiển thị tiêu đề
    pdfHeader.style.display = "block";

    // Đợi một chút để DOM cập nhật (html2canvas cần render đúng)
    await new Promise((resolve) => setTimeout(resolve, 200));

    // Tạo canvas từ DOM đã hiển thị
    const canvas = await html2canvas(element, { scale: 2 });
    const imgData = canvas.toDataURL("image/png");

    const pdf = new jsPDF("p", "mm", "a4");
    const imgProps = pdf.getImageProperties(imgData);
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;

    pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
    pdf.save("ASQ3_KetQua.pdf");

    // Ẩn lại tiêu đề
    pdfHeader.style.display = "none";
  };

  const domainMapping = {
    communication: "GIAO TIẾP",
    gross_motor: "VẬN ĐỘNG THÔ",
    fine_motor: "VẬN ĐỘNG TINH",
    problem_solving: "GIẢI QUYẾT VẤN ĐỀ",
    personal_social: "CÁ NHÂN XÃ HỘI",
  };

  const convertResultToArray = (resultTest) => {
    return Object.entries(resultTest).map(([key, value]) => ({
      domainName: domainMapping[key] || key,
      status: value.status.toUpperCase(),
    }));
  };
  const groupByStatus = (results) => {
    const grouped = {
      "BÌNH THƯỜNG": [],
      CHẬM: [],
      "CHẬM RÕ RỆT": [],
    };

    results.forEach(({ domainName, status }) => {
      if (grouped[status]) {
        grouped[status].push(domainName);
      }
    });

    return grouped;
  };

  const DevelopmentSummary = ({ resultTest }) => {
    const rawResults = convertResultToArray(resultTest);
    const statusGroups = groupByStatus(rawResults);

    return (
      <div>
        {statusGroups["BÌNH THƯỜNG"].length > 0 && (
          <p style={{ color: "color: #757575" }}>
            Trẻ có trạng thái sự phát triển <b>BÌNH THƯỜNG</b> ở các lĩnh vực{" "}
            <b>{statusGroups["BÌNH THƯỜNG"].join(", ")}</b>. Ta thấy trẻ có điểm
            nằm trong vùng màu <b>XANH LÁ</b>. Điều này có nghĩa là trẻ phát
            triển tương đương với trẻ khác ở cùng độ tuổi trong các lĩnh vực
            này. Phụ huynh nếu vẫn lo lắng về tình trạng của trẻ có thể kết hợp
            các giải pháp dạy tại nhà thông qua <b>CHATBOT</b> của chúng tôi và
            làm lại bài kiểm tra sau 2 tháng với các lĩnh vực này.
          </p>
        )}

        {statusGroups["CHẬM"].length > 0 && (
          <p>
            Trẻ có trạng thái sự phát triển <b>CHẬM</b> ở lĩnh vực{" "}
            <b>{statusGroups["CHẬM"].join(", ")}</b>. Ta thấy trẻ có điểm nằm
            trong vùng màu <b>CAM</b>. Điều này có nghĩa có một số các kỹ năng
            trong các lĩnh vực này trẻ chưa thực hiện được, hoặc đã thực hiện
            được nhưng chưa thường xuyên. Phụ huynh không cần quá lo lắng nhưng
            nên đưa trẻ đến phòng khám để chuẩn đoán với bác sĩ.
          </p>
        )}

        {statusGroups["CHẬM RÕ RỆT"].length > 0 && (
          <p>
            Trẻ có trạng thái sự phát triển <b>CHẬM RÕ RỆT</b> ở lĩnh vực{" "}
            <b>{statusGroups["CHẬM RÕ RỆT"].join(", ")}</b>. Ta thấy trẻ có điểm
            nằm trong vùng màu <b>XÁM</b>. Điều đó có nghĩa có một số các kỹ
            năng trong các lĩnh vực này trẻ chưa thực hiện được, hoặc đã thực
            hiện được nhưng chưa thường xuyên tức là trẻ chậm so với các trẻ
            khác cùng tuổi ở lĩnh vực này. Phụ huynh nên đưa trẻ đến phòng khám
            để chuẩn đoán chính xác với bác sĩ và có giải pháp can thiệp sớm cho
            trẻ.
          </p>
        )}
      </div>
    );
  };

  const solutionSuggestions = {
    "GIAO TIẾP": `Gia đình nên đưa trẻ đi đến cơ sở y tế để đánh giá thêm về sự phát triển của trẻ và Kiểm tra về thính lực cho trẻ, Khám chuyên khoa để kiểm tra thêm, Khám chuyên khoa nhi (khoa tâm bệnh, khoa tâm lý, khoa phục hồi chức năng...), Kiểm tra về thị lực cho trẻ.
  
  Gia đình có thể tham khảo một số trò chơi hữu ích cho sự phát triển của trẻ cùng CHATBOT.`,

    "VẬN ĐỘNG TINH": `Gia đình nên đưa trẻ đi đến cơ sở y tế để đánh giá thêm về sự phát triển của trẻ và Kiểm tra vận động của trẻ, Kiểm tra về thị lực cho trẻ, Kiểm tra về thính lực cho trẻ, Khám chuyên khoa để kiểm tra thêm.
  
  Gia đình có thể tham khảo một số trò chơi hữu ích cho sự phát triển của trẻ cùng CHATBOT.`,

    "VẬN ĐỘNG THÔ": `Gia đình nên đưa trẻ đi đến cơ sở y tế để đánh giá thêm về sự phát triển của trẻ và Kiểm tra về thính lực cho trẻ, Khám chuyên khoa để kiểm tra thêm, Khám chuyên khoa nhi (khoa tâm bệnh, khoa tâm lý, khoa phục hồi chức năng...), Kiểm tra về thị lực cho trẻ.
  
  Gia đình có thể tham khảo một số trò chơi hữu ích cho sự phát triển của trẻ cùng CHATBOT.`,

    "CÁ NHÂN XÃ HỘI": `Gia đình nên đưa trẻ đi đến cơ sở y tế để đánh giá thêm về sự phát triển của trẻ và Kiểm tra vận động của trẻ.
  
  Gia đình có thể tham khảo một số trò chơi hữu ích cho sự phát triển của trẻ cùng CHATBOT.`,

    "GIẢI QUYẾT VẤN ĐỀ": `Gia đình nên đưa trẻ đi đến cơ sở y tế để đánh giá thêm về sự phát triển của trẻ và Kiểm tra về thính lực cho trẻ, Khám chuyên khoa để kiểm tra thêm, Khám chuyên khoa nhi (khoa tâm bệnh, khoa tâm lý, khoa phục hồi chức năng...), Kiểm tra về thị lực cho trẻ.
  
  Gia đình có thể tham khảo một số trò chơi hữu ích cho sự phát triển của trẻ cùng CHATBOT.`,
  };

  return (
    <div className="result-page">
      <div className="print-pdf" ref={resultRef}>
        <div className="pdf-only-header">
          <h2 className="pdf-title">
            Kết quả bài sàng lọc đánh giá phát triển theo độ tuổi ASQ-3
          </h2>
          <p className="pdf-time">Thời gian: {new Date().toLocaleString()}</p>
        </div>

        {/* 1. THÔNG TIN TRẺ */}
        <section className="section">
          <h3 className="chapter">1. THÔNG TIN CHUNG</h3>
          <div className="info-grid">
            <div>
              <strong>Họ và tên trẻ:</strong> {childInfo.fullName}
            </div>
            <div>
              <strong>Ngày sinh:</strong> {formatDate(childInfo.birthDate)}
            </div>
            <div>
              <strong>SĐT liên hệ:</strong> {parentInfo.phone}
            </div>
            <div>
              <strong>Nơi sàng lọc:</strong> {parentInfo.place}
            </div>
            <div>
              <strong>Ngày thực hiện:</strong> {new Date().toLocaleDateString()}
            </div>
          </div>
        </section>

        {/* 2. GIẢI THÍCH */}
        <section className="section">
          <h3 className="chapter">2. GIẢI THÍCH VỀ SÀNG LỌC ASQ-3</h3>
          <p>
            ASQ-3 là bộ sàng lọc chuẩn dành cho cha mẹ/ người chăm sóc để tự
            điền nhằm sàng lọc sự phát triển của trẻ nhỏ...
          </p>
          <div className="legend">
            <p className="lv1">
              - Vùng điểm thể hiện trẻ đang gặp khó khăn - CHẬM PHÁT TRIỂN
            </p>
            <p className="lv2">
              - Vùng điểm thể hiện trẻ cần được theo dõi thêm và làm sàng lọc
              lại do một số kỹ năng chưa thành thục - CẦN THEO DÕI{" "}
            </p>
            <p className="lv3">
              - Vùng điểm thể hiện trẻ có sự phát triển bình thường - BÌNH
              THƯỜNG
            </p>
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
                {/* <th>Điểm tối đa</th> */}
                <th>Điểm của trẻ</th>
                <th>Trạng thái</th>

                <th style={{ width: "400px" }}>Thang chuẩn 0 - 60</th>
              </tr>
            </thead>
            <tbody>
              {Array.isArray(lstScores) && lstScores.length > 0 ? (
                lstScores.map(({ field, score, cutoff, max, status }, idx) => {
                  const leftPercent = Math.min(
                    Math.max((score / 60) * 100, 0),
                    100
                  );
                  const cutoffPercent = Math.round((cutoff / 60) * 100);
                  const maxPercent = Math.round((max / 60) * 100);

                  return (
                    <tr key={idx}>
                      <td>{field}</td>
                      <td>{cutoff}</td>
                      {/* <td>{max}</td> */}
                      <td>{`${score}`}</td>
                      <td>{status}</td>

                      <td>
                        <div className="slider-container">
                          <div
                            className="slider-track"
                            style={{
                              background: `linear-gradient(
                to right,
                #757575 0%,
                #757575 ${cutoffPercent}%,
                #f1a446 ${cutoffPercent}%,
                #f1a446 ${maxPercent}%,
                #7acc98 ${maxPercent}%,
                #7acc98 100%
              )`,
                            }}
                          >
                            {[0, 15, 30, 45, 60].map((val) => (
                              <span
                                key={val}
                                className="slider-marker"
                                style={{ left: `${(val / 60) * 100}%` }}
                              >
                                {val}
                              </span>
                            ))}
                          </div>
                          <div
                            className="slider-dot"
                            style={{ left: `${leftPercent}%` }}
                          />
                        </div>
                        <div style={{ marginTop: 4, textAlign: "center" }}>
                          {/* {score} */}
                        </div>
                      </td>
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
          <h3 className="chapter">
            4. NHẬN XÉT CHUNG VỀ MỨC ĐỘ PHÁT TRIỂN CỦA TRẺ
          </h3>

          <DevelopmentSummary resultTest={testResult.resultTest} />

          <div>
            <h3 className="chapter">5. ĐỀ XUẤT GIẢI PHÁP</h3>
            {lstScores
              .filter(
                (item) =>
                  item.status === "CHẬM" || item.status === "CHẬM RÕ RỆT"
              )
              .map((item, index) => (
                <div key={index} style={{ marginBottom: "1rem" }}>
                  <h4 style={{ color: "#d84315" }}>
                    {index + 1}.{" "}
                    {item.status === "CHẬM" ? "Chậm" : "Chậm rõ rệt"}{" "}
                    {item.field}
                  </h4>
                  <p style={{ whiteSpace: "pre-line" }}>
                    {solutionSuggestions[item.field]}
                  </p>
                </div>
              ))}
          </div>
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
