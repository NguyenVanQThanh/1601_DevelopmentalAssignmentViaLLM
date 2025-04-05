import { useState } from 'react';
import "./App.css";
import './styles/page_asq.css';
import './styles/page_chatbot.css';
import Header from "./components/Header/Header";
import Footer from "./components/Footer/Footer";
import TitleBox from "./components/Title_box/TitleBox";
import FormWrapper from './page/test-asq/components/Form/FormWrapper';
import FormASQTest from './page/test-asq/components/Form/FormASQTest';


function App() {
  // const navigate = useNavigate();
  const provinces = [
    // Ưu tiên
    "TP. Hồ Chí Minh",
    "Bình Dương",
    "Đồng Nai",
    "Long An",
    "Tây Ninh",
    "Bà Rịa - Vũng Tàu",
    "Hà Nội",
  
    "An Giang", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bắc Ninh", "Bến Tre",
    "Bình Định", "Bình Phước", "Bình Thuận", "Cà Mau", "Cao Bằng", "Cần Thơ",
    "Đà Nẵng", "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Tháp", "Gia Lai",
    "Hà Giang", "Hà Nam", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang",
    "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
    "Lạng Sơn", "Lào Cai", "Lâm Đồng", "Nam Định", "Nghệ An", "Ninh Bình",
    "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi",
    "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La", "Thái Bình", "Thái Nguyên",
    "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh", "Tuyên Quang",
    "Vĩnh Long", "Vĩnh Phúc", "Yên Bái"
  ];
  

  const [showExtraFields, setShowExtraFields] = useState(false);
  const formFields = [
    { type: 'text', name: 'fullName', label: 'Họ và tên:' },
    { type: 'date', name: 'birthDate', label: 'Ngày sinh:' },
    { type: 'select', name: 'location', label: 'Địa chỉ hiện tại:', options: provinces },
    { type: 'radio', name: 'gender', label: 'Giới tính:', options: ['Nam         ', 'Nữ'] },
    { type: 'radio', name: 'pre-birth', label: 'Trẻ sinh non:', options: ['Không', 'Có'] },
    { type: 'radio', name: 'pre-result', label: 'Kết quả chuẩn đoán:', options: ['Không', 'Có'] ,
      onChange: (value) => setShowExtraFields(value === 'Có'), // 👈 xử lý khi chọn radio
    },
  ];

  const results  = ["Rối loạn Phổ tự kỷ", "Chậm nói", "Chậm phát triển trí tuệ"];
  const hospitals  = ["BV Nhi Đồng 1 - HCM", "BV Nhi Đồng 2 - HCM", "BV Nhi Trung Ương - HCM", "BV Đại học Y - HCM", "BV Tỉnh",  "PK Tâm lý Nhi đồng", "Trung tâm Can thiệp", "PK Khác"];
  const doctors  = ["BS Chuyên khoa Tâm lý Nhi", "Bác sĩ Chuyên khoa khác", "Giáo viên Giáo dục", "Giáo viên Giáo dục Đặc biệt", "Khác"];

  const extraFields = [
    { type: 'select', name: 'result', label: 'Kết quả chuẩn đoán:', options: results},
    { type: 'date', name: 'resultDate', label: 'Ngày chuẩn đoán:' },
    { type: 'select', name: 'hospital', label: 'Nơi chuẩn đoán:', options: hospitals },
    { type: 'select', name: 'doctor', label: 'Người chẩn đoán:', options: doctors},
    { type: 'radio', name: 'pre-test', label: 'Trẻ đã được sàng lọc trước đó với ASQ-3/M-CHAT-R:', options: ['Không', 'Có'] }
  ];

  // const handleSubmit = (formData) => {
  //   console.log('Dữ liệu form:', formData);
  // };
  const [step, setStep] = useState(1);
  return (
    <div className="container-page">
      <Header />
      
      <main>
        <section className="container-content">
          {/* 👉 BƯỚC 1: Nhập thông tin trẻ */}
          {step === 1 && (
            <>
              <TitleBox title="THÔNG TIN TRẺ EM" />
              <FormWrapper
                fields={showExtraFields ? [...formFields, ...extraFields] : formFields}
                onSubmit={(data) => {
                  console.log('Bước 1:', data);
                  setStep(2); // chuyển sang bước 2
                }}
              />
            </>
          )}
  
          {/* 👉 BƯỚC 2: Làm bài test */}
          {step === 2 && (
            <>
              <TitleBox
                title="LÀM BÀI SÀNG LỌC ĐÁNH GIÁ PHÁT TRIỂN THEO ĐỘ TUỔI ASQ-3"
                subtitle="(Bộ câu hỏi 20 tháng tuổi)"
                onBack={() => setStep(1)}
              />


              <FormASQTest
                onBack={() => setStep(1)}
                onSubmit={(answers) => {
                  console.log('Hoàn tất bài test:', answers);
                  // setStep(3); // nếu muốn thêm bước 3
                }}
              />
            </>
          )}
        </section>
      </main>
  
      <div className="container-footer">
        <Footer />
      </div>
    </div>
  );
  



}

export default App;
