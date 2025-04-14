import React, { useState } from 'react';
import './ChatbotPage.css';

function ChatbotPage() {
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: 'Xin chào! Tôi có thể hỗ trợ gì cho bạn về bài test ASQ-3 hay vấn đề bạn quan tâm là gì?',
    },
  ]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const res = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });

      const data = await res.json();
      const botMessage = { sender: 'bot', text: data.reply };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      const botMessage = { sender: 'bot', text: '⚠️ Lỗi kết nối đến máy chủ.' };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  return (
    <div className="chatbot-wrapper">
      <div className="chatbot-header">
        🤖 Chuyên gia AI đời đầu Tâm lý Nhi Đồng - Hảo Thanh
      </div>

      <div className="chatbot-body">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.sender}`}>
            <div className="message-bubble">{msg.text}</div>
          </div>
        ))}
      </div>

      <div className="chatbot-footer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Nhập câu hỏi..."
        />
        <button onClick={handleSend}>Gửi</button>
      </div>
    </div>
  );
}

export default ChatbotPage;
