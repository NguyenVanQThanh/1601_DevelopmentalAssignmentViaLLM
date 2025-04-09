import "./Header.css";
import logo from "../../assets/logo.png";
import { NavLink } from "react-router-dom";

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
        <nav className="nav">
          <NavLink
            to="/guest/asq3-test"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Đánh giá trẻ
          </NavLink>
          <NavLink
            to="/guest/chatbot"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Trò chuyện cùng chúng tôi
          </NavLink>
        </nav>
      </div>
    </header>
  );
}

export default Header;
