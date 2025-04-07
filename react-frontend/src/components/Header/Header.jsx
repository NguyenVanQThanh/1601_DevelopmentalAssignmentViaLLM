import React from 'react';
import './Header.css';
import logo from '../../assets/logo.png';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { NavLink } from "react-router-dom";

function Header() {

  return (
    <header className="header">
      <div className="header-container">
      <div className="logo">
        <img src={logo} alt="Phòng khám Tâm lý Nhi Đồng" />
      </div>
      <nav className="nav">
  <NavLink to="/guest/asq3-test" className={({ isActive }) => isActive ? 'active' : ''}>
    Đánh giá trẻ
  </NavLink>
  <NavLink to="/guest/chatbot" className={({ isActive }) => isActive ? 'active' : ''}>
    Trò chuyện cùng chúng tôi
  </NavLink>
</nav>
     </div>

    </header>
  );
}

export default Header;

