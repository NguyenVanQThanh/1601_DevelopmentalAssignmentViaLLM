import "./Header.css";
import logo from "../../assets/logo.png";
import { NavLink } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

function Header() {
  return (
    <header className="header">
      <div className="header-container">
        <div className="logo">
          <a
            href="https://tamlynhidong.vn/"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src={logo} alt="Phòng khám Tâm lý Nhi Đồng" />
          </a>
        </div>
        <div className="nav-account-wrapper">
          <nav className="nav">
            <NavLink
              to="/guest/predict"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Dự đoán Tự Kỷ
            </NavLink>
            <NavLink
              to="/guest/asq3-test"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Đánh giá phát triển ASQ-3
            </NavLink>
            <NavLink
              to="/guest/chatbot"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Trò chuyện cùng AI
            </NavLink>
          </nav>
          <div className="account-icon">
            <FaUserCircle size={35} />
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
