import React from 'react';
import './TitleBox.css'; 
import { FaArrowLeft } from 'react-icons/fa';
{/* ✅ npm install react-icons */}

function TitleBox({ title, subtitle, icon, onBack }) {
  return (
    <div className="title-box">
      {onBack && (
        <button className="back-button" onClick={onBack}>
          <FaArrowLeft /> {/* ✅ đây mới là icon back */}
        </button>
      )}

      {icon && <img src={icon} alt="icon" className="title-icon" />}

      <div className="title-text">
        <h2>{title}</h2>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>
    </div>
  );
}

export default TitleBox;