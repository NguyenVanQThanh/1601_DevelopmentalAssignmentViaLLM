import React, { useState, useEffect, useRef } from 'react';
import './ChatbotPage.css';

function ChatbotPage() {
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: 'Xin chào! Tôi có thể hỗ trợ gì cho bạn về bài test ASQ-3 hay vấn đề bạn quan tâm là gì?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatBodyRef = useRef(null);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    // Lấy API base URL từ biến môi trường
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
    // Tạo URL đầy đủ cho endpoint /ask
    const apiUrl = `${apiBaseUrl}/ask`; 

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Sử dụng apiUrl đã tạo
      const res = await fetch(apiUrl, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msg: input }),
      });

      if (!res.ok) {
        // Cố gắng lấy thông tin lỗi chi tiết từ server nếu có
        let errorMessage = `HTTP error! Status: ${res.status}`;
        try {
            const errorData = await res.json();
            if (errorData && errorData.detail) {
                errorMessage = errorData.detail;
            }
        } catch (jsonError) {
            // Bỏ qua nếu response không phải là JSON hoặc lỗi parse
            console.error("Could not parse error response as JSON:", jsonError);
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();
      const botMessage = { sender: 'bot', text: data.reply };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      // Hiển thị thông báo lỗi cụ thể hơn nếu có
      const displayErrorMessage = err.message || 'Lỗi kết nối đến máy chủ. Vui lòng thử lại.';
      const botMessage = { sender: 'bot', text: `⚠️ ${displayErrorMessage}` };
      setMessages((prev) => [...prev, botMessage]);
      console.error("Fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chatbot-wrapper">
      <div className="chatbot-header">
        🤖 Chuyên gia AI Tâm lý Nhi Đồng - Hảo Thanh
      </div>

      <div className="chatbot-body" ref={chatBodyRef}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.sender}`}>
            <div className="message-bubble">{msg.text}</div>
          </div>
        ))}
        {isLoading && (
          <div className="message bot">
            <div className="message-bubble">Đang xử lý...</div>
          </div>
        )}
      </div>

      <div className="chatbot-footer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !isLoading) { // Thêm điều kiện !isLoading
              handleSend();
            }
          }}
          placeholder="Nhập câu hỏi..."
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading}>
          {isLoading ? 'Đang gửi...' : 'Gửi'}
        </button>
      </div>
    </div>
  );
}

export default ChatbotPage;