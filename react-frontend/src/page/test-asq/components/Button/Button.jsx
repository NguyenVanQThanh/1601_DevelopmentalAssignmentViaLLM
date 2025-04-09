import React, { useState } from 'react';
import './Button.css';

function Button({ children, onClick, type = 'button' }) {
  const [clicked, setClicked] = useState(false);

  const handleClick = (e) => {
    if (onClick) onClick(e);
    setClicked(true);
    setTimeout(() => setClicked(false), 300); // reset lại sau 0.3s
  };

  return (
    <button
      className={`custom-button ${clicked ? 'clicked' : ''}`}
      onClick={handleClick}
      type={type}
    >
      {children}
    </button>
  );
}

export default Button;