import React, { useState } from 'react';
import FeedbackDialog from './FeedbackDialog';
// Bạn có thể tự tạo SVG icon hoặc dùng một ký tự
const FeedbackIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.026 3 11.25c0 4.106 3.122 7.496 7.207 8.135a.75.75 0 0 1 .588.048l2.861 1.431A.75.75 0 0 0 15 20.25Z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 11.379A.75.75 0 0 1 11.25 10.125h1.5a.75.75 0 0 1 0 1.5h-1.5a.75.75 0 0 1-1.371-.75Z" />
  </svg>
);


const FeedbackButton = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const toggleDialog = () => {
    setIsDialogOpen(prevState => !prevState);
  };

  const closeDialog = () => {
    setIsDialogOpen(false);
  };

  return (
    <>
      <button
        onClick={toggleDialog}
        title="Gửi phản hồi"
        className="feedback-button-fixed" // Sử dụng class từ Feedback.css
        aria-label="Mở hoặc đóng form phản hồi"
      >
        <FeedbackIcon />
      </button>
      {isDialogOpen && <FeedbackDialog onClose={closeDialog} />}
    </>
  );
};

export default FeedbackButton;