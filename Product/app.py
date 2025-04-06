from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from langchain_community.llms import CTransformers
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory

# Tải mô hình và tokenizer bartpho-syllable từ thư mục cục bộ
bartpho_tokenizer = AutoTokenizer.from_pretrained("./models/bartpho-syllable", local_files_only=True)
bartpho_model = AutoModelForSeq2SeqLM.from_pretrained("./models/bartpho-syllable", local_files_only=True)

# Tạo pipeline để tóm tắt hoặc chuẩn hóa câu hỏi
summarizer = pipeline(
    "text2text-generation",
    model=bartpho_model,
    tokenizer=bartpho_tokenizer,
    device=-1
)

# Hàm chuẩn hóa câu hỏi bằng bartpho-syllable
def preprocess_input(text):
    print(f"Đầu vào gốc: {text}")
    processed_text = summarizer(
        text,
        max_length=50,
        min_length=10,
        do_sample=False,
        num_beams=5
    )[0]['generated_text']
    print(f"Đầu vào sau khi chuẩn hóa: {processed_text}")
    return processed_text

# Cấu hình RAG
model_file = "models/vinallama-7b-chat_q5_0.gguf"
vector_db_path = "vectorstores/db_faiss"

# Load LLM
def load_llm(model_file):
    llm = CTransformers(
        model=model_file,
        model_type="llama",
        max_new_tokens=768,
        temperature=0.01,
        n_ctx=2048
    )
    return llm

# Đọc VectorDB
def read_vectors_db():
    embedding_model = GPT4AllEmbeddings(model_file="models/all-MiniLM-L6-v2-f16.gguf")
    db = FAISS.load_local(vector_db_path, embedding_model, allow_dangerous_deserialization=True)
    return db

# Khởi tạo RAG và bộ nhớ hội thoại
db = read_vectors_db()
llm = load_llm(model_file)

# Tạo bộ nhớ hội thoại
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Tạo prompt template (sửa để yêu cầu nghiêm ngặt hơn)
template = """<|im_start|>system
Chỉ dựa trên thông tin trong tài liệu sau và lịch sử hội thoại, trả lời câu hỏi một cách ngắn gọn và chính xác bằng tiếng Việt. Không được sử dụng kiến thức bên ngoài tài liệu. Nếu câu hỏi yêu cầu liệt kê, hãy cung cấp danh sách các mục cụ thể. Nếu không có thông tin liên quan trong tài liệu, trả lời "Không biết". Chỉ trả lời câu hỏi hiện tại, không sinh thêm câu hỏi hoặc nội dung khác.
**Lịch sử hội thoại:**
{chat_history}
**Thông tin từ tài liệu:**
{context}
<|im_end|>
<|im_start|>user
{question}
<|im_end|>
<|im_start|>assistant
"""
prompt = PromptTemplate(
    template=template,
    input_variables=["chat_history", "context", "question"]
)

# Tạo ConversationalRetrievalChain
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=db.as_retriever(search_kwargs={"k": 3}, max_tokens_limit=1200),
    memory=memory,
    combine_docs_chain_kwargs={"prompt": prompt},
    return_source_documents=False
)

# Chatbot response using RAG (chỉ tiếng Việt)
def chatbot_response(msg):
    processed_msg = preprocess_input(msg)
    response = qa_chain.invoke({"question": processed_msg})
    chatbot_response_text = response['answer']
    chatbot_response_text = chatbot_response_text.split('<|im_end|>')[0].strip()
    print(f"Đầu ra: {chatbot_response_text}")
    return chatbot_response_text

# Flask app
from flask import Flask, render_template, request
app = Flask(__name__)
app.static_folder = 'static'

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    user_text = request.args.get('msg')
    print(f"Nhận câu hỏi từ người dùng: {user_text}")
    chatbot_response_text = chatbot_response(user_text)
    return chatbot_response_text

if __name__ == "__main__":
    app.run(debug=True)