// ChatbotPage.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './ChatbotPage.css'; // Ensure this CSS file exists and is correctly linked
import TitleBox from '../../components/Title_box/TitleBox'; // Adjust path if necessary

// Function Name: ChatbotPage
// Functionality: Renders the main chatbot interface, handles message sending,
//                displays chat history, initial ASQ-related messages, and provides
//                a way to start new conversations.
// Input: initialMessage (Optional[string]) - An initial message from the AI (e.g., ASQ remark) to display.
// Input: sessionId (Optional[string]) - The current user's session ID for API calls.
// Input: accessToken (Optional[string]) - The JWT access token for authenticated API calls.
// Input: onInitialMessageShown (function) - Callback function to notify App.js that the initial message has been displayed.
// Output: JSX.Element - The rendered chatbot page.
function ChatbotPage({ initialMessage, sessionId, accessToken, onInitialMessageShown }) {
  // messages: Array<Object> - State for the list of current conversation messages.
  //                         Each message object has 'sender' ('user' or 'bot') and 'text'.
  const [messages, setMessages] = useState([]);
  // input: string - State for the current text in the message input field.
  const [input, setInput] = useState('');
  // isLoading: boolean - State to indicate if an API call is in progress (e.g., sending a message or fetching history).
  const [isLoading, setIsLoading] = useState(false);
  // error: Optional[string] - State to store and display any error messages encountered during API calls.
  const [error, setError] = useState(null);
  // chatBodyRef: React.RefObject - Ref attached to the chat body div element for scrolling.
  const chatBodyRef = useRef(null);
  // isMounted: React.RefObject - Ref to track if the component is currently mounted,
  //                            used to prevent state updates on unmounted components.
  const isMounted = useRef(true);

  // API_BASE_URL: string - Base URL for backend API calls, loaded from environment variables with a fallback.
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  // Function Name: scrollToBottom
  // Functionality: Scrolls the chat body to the bottom to show the latest messages.
  // Input: None.
  // Output: None.
  const scrollToBottom = useCallback(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, []);

  // Effect to set isMounted to false when the component unmounts.
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Function Name: fetchChatHistory
  // Functionality: Fetches the chat history for the current session from the backend API.
  //                It only fetches if a session is active and there are no messages currently displayed (neither initial nor fetched).
  // Input: None. (Relies on component's state and props like sessionId, accessToken).
  // Output: None (updates 'messages' and 'error' state).
  const fetchChatHistory = useCallback(async () => {
    if (sessionId && accessToken && isMounted.current && messages.length === 0 && !initialMessage) {
      setIsLoading(true); setError(null);
      console.log("Fetching chat history for session:", sessionId);
      try {
        const response = await fetch(`${API_BASE_URL}/chat/history`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'ngrok-skip-browser-warning': 'true'
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: `Server error: ${response.status}` }));
          throw new Error(errorData.detail || `Error loading chat history: ${response.status}`);
        }

        const historyData = await response.json();
        if (isMounted.current) {
          if (historyData && historyData.history && historyData.history.length > 0) {
            setMessages(historyData.history);
          } else {
            setMessages([{ sender: 'bot', text: 'Chào bạn, tôi là trợ lý AI. Bạn cần tư vấn về vấn đề gì cho bé ạ?' }]);
          }
        }
      } catch (err) {
        console.error("Error loading chat history:", err);
        if (isMounted.current) {
          setError(err.message || "Could not load chat history.");
          if(messages.length === 0) {
            setMessages([{ sender: 'bot', text: `Chào bạn! Hiện tại không thể tải lịch sử trò chuyện. Bạn có thể bắt đầu một cuộc trò chuyện mới.` }]);
          }
        }
      } finally {
        if (isMounted.current) setIsLoading(false);
      }
    }
  }, [sessionId, accessToken, API_BASE_URL, messages.length, initialMessage]);

  // Effect for handling the initial ASQ remark message and fetching initial chat history.
  useEffect(() => {
    if (isMounted.current) {
      if (initialMessage && messages.length === 0) {
        console.log("Displaying initial ASQ remark message.");
        setMessages([{ sender: 'bot', text: initialMessage }]);
        if (onInitialMessageShown) {
          onInitialMessageShown();
        }
      } else if (!initialMessage && messages.length === 0 && sessionId && accessToken) {
        fetchChatHistory();
      }
    }
  }, [initialMessage, onInitialMessageShown, messages.length, sessionId, accessToken, fetchChatHistory]);


  // Effect to scroll to bottom when new messages are added.
  useEffect(scrollToBottom, [messages]);

  // Function Name: handleNewConversation
  // Functionality: Clears the chat history on the backend for the current session and resets the local message state
  //                to a default welcome message, effectively starting a new conversation.
  // Input: None.
  // Output: None (updates 'messages' state and calls backend).
  const handleNewConversation = async () => {
    if (!accessToken || !sessionId || isLoading) {
      alert(isLoading ? "Vui lòng chờ..." : "Không thể bắt đầu cuộc trò chuyện mới: thiếu thông tin phiên làm việc.");
      return;
    }

    setIsLoading(true); setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/chat/history/clear?clear_asq=true`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'ngrok-skip-browser-warning': 'true',
          'Content-Type': 'application/json'
        },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Lỗi khi tạo cuộc trò chuyện mới: ${response.status}`);
      }
      const data = await response.json();
      console.log("New conversation response:", data.message);

      if (isMounted.current) {
        setMessages([{ sender: 'bot', text: 'Chào bạn! Chúng ta bắt đầu cuộc trò chuyện mới nhé. Bạn cần hỗ trợ gì?' }]);
        setInput('');
        if (onInitialMessageShown) {
          onInitialMessageShown();
        }
      }
    } catch (err) {
      console.error("Error starting new conversation:", err);
      if (isMounted.current) setError(err.message || "Không thể tạo cuộc trò chuyện mới.");
    } finally {
      if (isMounted.current) setIsLoading(false);
    }
  };

  // Function Name: handleSend
  // Functionality: Sends the user's current input as a message to the backend's /ask endpoint,
  //                updates the local message state with the user's message and the bot's reply.
  // Input: None (uses 'input' state).
  // Output: None (updates 'messages' state).
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    if (!accessToken || !sessionId) {
      setError('Phiên làm việc không hợp lệ hoặc đã hết hạn. Vui lòng làm mới trang.');
      setIsLoading(false); return;
    }

    const userMessageText = input;
    const userMessage = { sender: 'user', text: userMessageText };
    
    if (isMounted.current) {
        setMessages((prev) => [...prev, userMessage]);
        setInput(''); setIsLoading(true); setError(null);
    }

    try {
      const apiUrl = `${API_BASE_URL}/ask`;
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ msg: userMessageText }),
      });
      if (!res.ok) {
        let errorMessage = `Server error: ${res.status}`;
        try { const errorData = await res.json(); if (errorData?.detail) errorMessage = errorData.detail; }
        catch (jsonError) { console.error("Could not parse error JSON:", jsonError); }
        throw new Error(errorMessage);
      }
      const data = await res.json();
      if (isMounted.current) setMessages((prev) => [...prev, { sender: 'bot', text: data.reply || "Sorry, I couldn't process that." }]);
    } catch (err) {
      if (isMounted.current) {
        let displayError = `⚠️ ${err.message || 'Connection error.'}`;
        if (err.message && err.message.toLowerCase().includes("not found")) {
            displayError = "⚠️ Xin lỗi, yêu cầu không tìm thấy hoặc dịch vụ đang gặp sự cố."
        }
        setMessages((prev) => [...prev, { sender: 'bot', text: displayError }]);
      }
      console.error("Fetch error in chatbot:", err);
    } finally { if (isMounted.current) setIsLoading(false); }
  };

  return (
    <div className="chatbot-page-container">
      <TitleBox title="TRỢ LÝ AI NHI KHOA" subtitle="Hỗ trợ giải đáp thắc mắc và tư vấn về ASQ-3"/>
      <div className="chatbot-wrapper">
        <div className="chatbot-body" ref={chatBodyRef}>
          {error && !messages.some(m => m.text.includes(error)) && (
            <div className="message-row bot-row error-message">
              <div className="message-bubble bot">{error}</div>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-row ${msg.sender === 'user' ? 'user-row' : 'bot-row'}`}>
              <div className={`message-bubble ${msg.sender}`}>
                {msg.text.split('\n').map((line, i) => (<span key={i}>{line}{i < msg.text.split('\n').length - 1 && <br />}</span>))}
              </div>
            </div>
          ))}
          {isLoading && (!messages.length || messages[messages.length -1]?.sender === 'user') && (
            <div className="message-row bot-row">
              <div className="message-bubble bot typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
        </div>

        <div className="chatbot-footer">
          <button 
            onClick={handleNewConversation} 
            className="new-chat-button-footer"
            disabled={isLoading || !accessToken || !sessionId}
            title="Bắt đầu cuộc trò chuyện mới"
          >
            Mới
          </button>
          <input 
            type="text" 
            value={input} 
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !isLoading && accessToken && sessionId && input.trim()) handleSend();}}
            placeholder={!accessToken || !sessionId ? "Đang chờ thông tin phiên..." : "Nhập câu hỏi của bạn..."}
            disabled={isLoading || !accessToken || !sessionId} 
            className="chat-input"
          />
          <button 
            onClick={handleSend} 
            disabled={isLoading || !accessToken || !sessionId || !input.trim()}
            className="send-button"
          >
            {isLoading && messages.length > 0 && messages[messages.length -1]?.sender === 'user' ? <span className="sending-spinner"></span> : 'Gửi'}
          </button>
        </div>
      </div>
    </div>
  );
}
export default ChatbotPage;