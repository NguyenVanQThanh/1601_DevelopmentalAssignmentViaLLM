import React, { useState } from 'react';
import './Button.css';

function Button({ children, onClick, type = 'button' }) {
  const [clicked, setClicked] = useState(false);

  const handleClick = (e) => {
    if (onClick) onClick(e);
    setClicked(true);
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