import React from 'react';
import './Header.css';
import logo from '../../assets/logo.png';

function Header() {
  return (
    <header className="header">
      <div className="header-container">
      <div className="logo">
        <img src={logo} alt="Phòng khám Tâm lý Nhi Đồng" />
      </div>
      <nav className="nav">
        <a href="#" className="active">Đánh giá trẻ</a>
        <a href="#">Trò chuyện cùng chúng tôi</a>
        <a href="#">Giải pháp</a>
      </nav>
     </div>

    </header>
  );
}

export default Header;

