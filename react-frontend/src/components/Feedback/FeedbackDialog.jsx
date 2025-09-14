import React, { useState, useEffect } from 'react';

// Icon ngôi sao (bạn có thể tùy chỉnh hoặc dùng SVG khác)
const StarIcon = ({ filled }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.5" className="w-7 h-7">
    <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.619.049.863.842.42 1.261l-4.203 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.822.634l-4.735-2.835a.563.563 0 0 0-.536 0L6.54 20.82a.562.562 0 0 1-.822-.634l1.285-5.385a.563.563 0 0 0-.182-.557l-4.203-3.602a.563.563 0 0 1 .42-1.261l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
  </svg>
);

const FeedbackDialog = ({ onClose }) => {
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [opinion, setOpinion] = useState('');
  const [rate, setRate] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState({ message: '', type: '' });

  // Xử lý đóng khi click ra ngoài (tùy chọn, có thể cần điều chỉnh)
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (event.target.classList.contains('feedback-dialog-overlay')) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (rate === 0) {
      setSubmitStatus({ message: 'Vui lòng chọn điểm đánh giá.', type: 'error' });
      return;
    }
    if (!opinion.trim()) {
      setSubmitStatus({ message: 'Vui lòng nhập nội dung phản hồi.', type: 'error' });
      return;
    }
    setIsSubmitting(true);
    setSubmitStatus({ message: '', type: '' });

    const feedbackData = {
      fullName: fullName.trim() || null,
      phone: phone.trim() || null,
      opinion: opinion.trim(),
      rate: rate,
    };

    try {
      const accessToken = localStorage.getItem('accessToken'); // Hoặc sessionStorage
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/feedback/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
        },
        body: JSON.stringify(feedbackData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Lỗi không xác định.' }));
        throw new Error(errorData.detail || `Lỗi ${response.status}`);
      }
      setSubmitStatus({ message: 'Cảm ơn bạn đã gửi phản hồi!', type: 'success' });
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (error) {
      setSubmitStatus({ message: error.message || 'Đã xảy ra lỗi.', type: 'error' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    // Thêm class 'open' để kích hoạt transition
    <div className={`feedback-dialog-overlay ${isSubmitting ? '' : 'open'}`}>
      <div className="feedback-dialog-content">
        <div className="feedback-dialog-header">
          <h2 className="feedback-dialog-title">Gửi phản hồi của bạn</h2>
          <button onClick={onClose} className="feedback-close-button" aria-label="Đóng">
            × {/* Ký tự X đơn giản */}
          </button>
        </div>

        {submitStatus.message && (
          <div className={`feedback-status-message ${submitStatus.type}`}>
            {submitStatus.message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="feedback-form-group">
            <label htmlFor="fullName">Họ và tên (tùy chọn)</label>
            <input type="text" id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="feedback-form-group">
            <label htmlFor="phone">Số điện thoại (tùy chọn)</label>
            <input type="tel" id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="09xxxxxxxx" />
          </div>
          <div className="feedback-form-group">
            <label htmlFor="opinion">Nội dung phản hồi <span style={{color: 'red'}}>*</span></label>
            <textarea id="opinion" rows="4" value={opinion} onChange={(e) => setOpinion(e.target.value)} required />
          </div>
          <div className="feedback-rating-container">
            <label style={{display: 'block', marginBottom: '8px', fontWeight: 500, color: '#555'}}>Đánh giá của bạn <span style={{color: 'red'}}>*</span></label>
            <div className="feedback-rating-stars">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRate(star)}
                  className={`feedback-star-button ${rate >= star ? 'selected' : ''}`}
                  aria-label={`Đánh giá ${star} sao`}
                >
                  <StarIcon filled={rate >= star} />
                </button>
              ))}
            </div>
          </div>
          <button type="submit" disabled={isSubmitting} className="feedback-submit-button">
            {isSubmitting ? 'Đang gửi...' : 'Gửi phản hồi'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default FeedbackDialog;