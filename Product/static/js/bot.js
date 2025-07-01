// bot.js

// Cập nhật thời gian
function updateTime() {
  var now = new Date();
  var hours = now.getHours();
  var minutes = now.getMinutes();
  var seconds = now.getSeconds();
  var timeString = hours + ':' + minutes;
  document.getElementById('clock').textContent = timeString;
}
setInterval(updateTime, 1000);

// Toggle chatbot
var running = false;
document.getElementById("chatbot_toggle").onclick = function () {
  if (document.getElementById("chatbot").classList.contains("collapsed")) {
    document.getElementById("chatbot").classList.remove("collapsed");
    document.getElementById("chatbot_toggle").children[0].style.display = "none";
    document.getElementById("chatbot_toggle").children[1].style.display = "";
    setTimeout(addResponseMsg, 1000, "Hi");
  } else {
    document.getElementById("chatbot").classList.add("collapsed");
    document.getElementById("chatbot_toggle").children[0].style.display = "";
    document.getElementById("chatbot_toggle").children[1].style.display = "none";
  }
};

// Hàm thêm tin nhắn chào
function addResponseMsg(text) {
  appendMessage(BOT_NAME, BOT_IMG, "left", text);
}

const msgerForm = get(".msger-inputarea");
const msgerInput = get(".msger-input");
const msgerChat = get(".msger-chat");

// Icons made by Freepik from www.flaticon.com
const BOT_IMG = "/static/img/mhcicon.png";
const PERSON_IMG = "/static/img/person.png";
const BOT_NAME = "Psychiatrist Bot";
const PERSON_NAME = "You";

// Hàm xử lý ký tự xuống dòng và loại bỏ khoảng trắng dư
function formatText(text) {
  if (typeof text !== 'string') {
    return ''; // Trả về chuỗi rỗng nếu text không phải là string
  }
  // Loại bỏ khoảng trắng dư, chuẩn hóa khoảng trắng giữa các từ, giữ lại xuống dòng
  text = text
    .trim() // Loại bỏ khoảng trắng ở đầu và cuối
    .replace(/\s+/g, ' ') // Thay thế nhiều khoảng trắng liên tiếp bằng 1 khoảng trắng
    .replace(/\n/g, '<br>'); // Thay \n bằng <br>
  return text;
}

// Hàm thêm tin nhắn vào giao diện
function appendMessage(name, img, side, text, isLoading = false) {
  const msgHTML = `
    <div class="msg ${side}-msg ${isLoading ? 'loading-msg' : ''}" ${isLoading ? 'id="loading-msg"' : ''}>
      <div class="msg-img" style="background-image: url(${img})"></div>
      <div class="msg-bubble">
        <div class="msg-info">
          <div class="msg-info-name">${name}</div>
          <div class="msg-info-time">${formatDate(new Date())}</div>
        </div>
        <div class="msg-text">${text}</div>
      </div>
    </div>
  `;

  msgerChat.insertAdjacentHTML("beforeend", msgHTML);
  msgerChat.scrollTop += 500;
}

// Hàm hiển thị tin nhắn loading
function showLoading() {
  appendMessage(BOT_NAME, BOT_IMG, "left", '<span class="loading-dots">...</span>', true);
}

// Hàm xóa tin nhắn loading
function removeLoading() {
  const loadingMsg = document.getElementById("loading-msg");
  if (loadingMsg) {
    loadingMsg.remove();
  }
}

// Xử lý sự kiện gửi tin nhắn
msgerForm.addEventListener("submit", event => {
  event.preventDefault();
  const msgText = msgerInput.value;
  if (!msgText) return;
  appendMessage(PERSON_NAME, PERSON_IMG, "right", msgText);
  msgerInput.value = "";
  showLoading(); // Hiển thị loading
  botResponse(msgText);
});

async function botResponse(rawText) {
  try {
    const response = await fetch(`/get?msg=${encodeURIComponent(rawText)}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    console.log(response);
    const data = await response.json(); // Parse JSON
    const botMessage = data || "Không có phản hồi từ server."; // Dùng trực tiếp data
    console.log("User message:", rawText);
    console.log("Bot response:", botMessage);
    removeLoading(); // Xóa loading
    appendMessage(BOT_NAME, BOT_IMG, "left", formatText(botMessage)); // Áp dụng formatText
  } catch (error) {
    console.error("Error fetching bot response:", error);
    removeLoading(); // Xóa loading nếu có lỗi
    appendMessage(BOT_NAME, BOT_IMG, "left", "Đã có lỗi xảy ra, vui lòng thử lại!");
  }
}

// Utils
function get(selector, root = document) {
  return root.querySelector(selector);
}

function formatDate(date) {
  const h = "0" + date.getHours();
  const m = "0" + date.getMinutes();
  return `${h.slice(-2)}:${m.slice(-2)}`;
}