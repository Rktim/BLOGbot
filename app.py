from typing import Optional
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import streamlit as st

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Custom CSS
st.markdown("""
<style>
    /* Main container */
    .stApp {
        background-color: #0f0f0f;
        color: white;
    }
    
    /* Headers */
    h1 {
        color: #ff0000 !important;
        font-size: 2.5em !important;
        text-align: center;
        margin-bottom: 10px !important;
    }
    
    /* Subheaders */
    h2, h3 {
        color: #aaaaaa !important;
        font-size: 1.5em !important;
    }
    
    /* Text input */
    .stTextInput > div > div > input {
        background-color: #1f1f1f !important;
        color: white !important;
        border: 1px solid #303030 !important;
        border-radius: 4px !important;
        font-size: 1.2em !important;
        padding: 12px !important;
        height: 60px !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #ff0000 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 12px 24px !important;
        font-weight: 500 !important;
        font-size: 1.2em !important;
        width: 100% !important;
        margin: 10px 0 !important;
    }
    
    .stButton > button:hover {
        background-color: #cc0000 !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        background-color: #1f1f1f !important;
        border: 1px solid #303030 !important;
        border-radius: 8px !important;
        padding: 16px !important;
        margin: 12px 0 !important;
        font-size: 1.1em !important;
    }
    
    .stChatMessage[data-testid="user-message"] {
        border-left: 4px solid #ff0000 !important;
    }
    
    .stChatMessage[data-testid="assistant-message"] {
        border-left: 4px solid #3ea6ff !important;
    }
    
    /* Blog content preview */
    .blog-preview {
        background-color: #1f1f1f !important;
        border: 1px solid #303030 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        margin: 20px 0 !important;
        max-height: 400px !important;
        overflow-y: auto !important;
        font-size: 1.1em !important;
        line-height: 1.6 !important;
    }
    
    /* Chat input */
    .stChatInput > div > div > textarea {
        background-color: #1f1f1f !important;
        color: white !important;
        border: 1px solid #303030 !important;
        border-radius: 4px !important;
        font-size: 1.2em !important;
        padding: 12px !important;
        min-height: 80px !important;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1f1f1f;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #303030;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #404040;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None

if "current_blog_url" not in st.session_state:
    st.session_state.current_blog_url = None

if "blog_content" not in st.session_state:
    st.session_state.blog_content = None

# 1. Function to fetch and extract blog text
def fetch_blog_text(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = [p.get_text() for p in soup.find_all("p")]
    return "\n".join(paragraphs)

# 2. Function to create vector store from blog text
def create_vector_store(text: str):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)
    embeddings = HuggingFaceEmbeddings()
    vectordb = Chroma.from_texts(chunks, embeddings)
    return vectordb

# 3. Set up the RAG chain
def setup_chain(vectordb):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    llm = ChatGroq(api_key=GROQ_API_KEY, model="gemma2-9b-it")
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm, vectordb.as_retriever(), memory=memory
    )
    return qa_chain

# App title
st.markdown("<h1>Blog Bot 📝</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #aaaaaa; font-size: 1.2em;'>Your AI-powered blog analysis companion</p>", unsafe_allow_html=True)

# Create two columns
col1, col2 = st.columns(2)

with col1:
    # Blog URL input
    blog_url = st.text_input("📝 Enter Blog URL", placeholder="Paste your blog URL here...", key="blog_url_input")
    
    # Process button
    if st.button("✨ Load Blog", key="load_blog_btn"):
        if not blog_url:
            st.error("Please enter a blog URL.")
        else:
            try:
                with st.spinner("🔍 Processing blog content..."):
                    # Fetch and process blog content
                    text = fetch_blog_text(blog_url)
                    st.session_state.blog_content = text  # Store blog content
                    vectordb = create_vector_store(text)
                    st.session_state.qa_chain = setup_chain(vectordb)
                    st.session_state.current_blog_url = blog_url
                    st.session_state.messages = []  # Clear chat history
                    st.success("✅ Blog content loaded! You can now ask questions about it.")
            except Exception as e:
                st.error(f"❌ Error processing blog: {str(e)}")
    
    # Display blog content preview
    if st.session_state.blog_content:
        st.markdown("### 📄 Blog Content Preview")
        st.markdown(f"""
        <div class="blog-preview">
            {st.session_state.blog_content[:2000] + "..." if len(st.session_state.blog_content) > 2000 else st.session_state.blog_content}
        </div>
        """, unsafe_allow_html=True)

with col2:
    # Chat interface
    st.markdown("### 💬 Chat")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the blog...", key="chat_input"):
        if not st.session_state.qa_chain:
            st.error("Please load a blog first.")
        else:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            try:
                # Get AI response
                with st.spinner("🤔 Thinking..."):
                    result = st.session_state.qa_chain({
                        "question": prompt,
                        "chat_history": [(m["content"] if m["role"] == "user" else "", m["content"] if m["role"] == "assistant" else "") 
                                       for m in st.session_state.messages[:-1]]
                    })
                    response = result["answer"]
                
                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Display assistant message
                with st.chat_message("assistant"):
                    st.markdown(response)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

