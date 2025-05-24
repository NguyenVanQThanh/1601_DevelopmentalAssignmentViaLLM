import "./Footer.css";
import logo from "../../assets/logo.png";
import facebookIcon from "../../assets/logo_fb.png";
import tiktokIcon from "../../assets/logo_tiktok.png";

function Footer() {
  return (
    <footer>
      <div className="footer-logo">
        <img src={logo} alt="Logo" />
      </div>

      <div className="footer-content">
        <div className="footer-column">
          <h3>Phòng khám Tâm lý Nhi Đồng</h3>
          <div className="column-inner">
            <p>
              Chẩn đoán, điều trị/định hướng can thiệp các vấn đề về phát triển,
              hành vi, sức khỏe tinh thần ở trẻ em và trẻ vị thành niên
            </p>
            <p>
              <a href="https://maps.app.goo.gl/Ni2XNa6DoymUHRDh8"
              target="_blank"
              rel="noopener noreferrer">
                <strong>Địa chỉ:</strong> 34 Đường số 20, Phường 11, Quận 6, TP.HCM
                </a>
            </p>
            <p>
              <strong>Số điện thoại:</strong> 098.150.2721
            </p>
          </div>
        </div>

        <div className="footer-column">
          <h3>Giờ làm việc</h3>
          <div className="column-inner">
            <ul>
              <li>Thứ 2 đến thứ 6: từ 16g30 đến 20g00</li>
              <li>Thứ 7: từ 7g00 đến 20g00</li>
              <li>Chủ nhật: từ 7g00 đến 16g00</li>
            </ul>
          </div>
        </div>

        <div className="footer-column">
          <h3>Kết nối với chúng tôi</h3>
          <div className="social-icons">
            <div className="icon-item">
              <a href="https://www.facebook.com/tamlynhidong"
                 target="_blank"
                 rel="noopener noreferrer">
                <img src={facebookIcon} alt="Facebook" />
                {/* <span>Facebook</span> */}
              </a>
            </div>
            <div className="icon-item">
               <a href="https://www.tiktok.com/@tamlynhidong"
                  target="_blank"
                  rel="noopener noreferrer">
                <img src={tiktokIcon} alt="TikTok" />
                {/* <span>Tiktok</span> */}
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
