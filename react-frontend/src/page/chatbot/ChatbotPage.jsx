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

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msg: input }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}`);
      }

      const data = await res.json();
      const botMessage = { sender: 'bot', text: data.reply };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      const botMessage = { sender: 'bot', text: '⚠️ Lỗi kết nối đến máy chủ. Vui lòng thử lại.' };
      setMessages((prev) => [...prev, botMessage]);
      console.error(err);
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
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
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