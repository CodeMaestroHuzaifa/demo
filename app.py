# modules
import streamlit as st
from dotenv import load_dotenv
import os
from PyPDF2 import PdfReader
from docx import Document
from csv import reader
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.callbacks import get_openai_callback
from streamlit_chat import message

# page
st.set_page_config(page_title="Talk With File", page_icon="logo.png")


def main():
    load_dotenv()

    # page
    hide_button = """
    <style>
        header{
            visibility:hidden;
        }
    </style>
    """
    st.markdown(hide_button, unsafe_allow_html=True)
    st.title("Document GPT")
    
    # memory
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    if "processCompletion" not in st.session_state:
        st.session_state.processCompletion = False

    # interface
    with st.sidebar:
        uploaded_files = st.file_uploader("Upload Your File", type=['pdf','docx'], accept_multiple_files=True)
        openai_key = st.text_input("OpenAI Key", key="openai_api_key", type="password")
        process = st.button("Process")  
    
    # processing
    if process:
        if not openai_key:
            st.info("Select your \"OpenAI Key\" to continue.")
            st.stop()
        
        pl = st.empty()

        files_text = get_files_text(uploaded_files)
        pl.write("Please wait..")

        text_chunk = get_text_chunk(files_text)
        pl.write("Please wait....")

        vectorstore = get_vectorstore(text_chunk)        
        pl.write("Please wait......")

        st.session_state.conversation = get_conversation_chain(vectorstore , openai_key)
        pl.write("File Uploaded!")

        st.session_state.processCompletion = True
    
    if st.session_state.processCompletion == True:
        user_query = st.chat_input("Ask question about the document.")
        if user_query:
            handle_userinput(user_query)


def get_files_text(documents):
    text = ""

    for document in documents:
        split_tup = os.path.splitext(document.name)
        file_extension = split_tup[1]

        if (file_extension == ".pdf"):
            text = text + get_pdf_text(document)
        elif (file_extension == ".docx"):
            text = text + get_docx_text(document)
        else:
            text = text + get_csv_file(document)
    
    return text

def get_pdf_text(file):
    text = ""
    reader = PdfReader(file)
    for page in reader.pages:
        text = text + page.extract_text()
    return text

def get_docx_text(file):
    data = []
    reader =  Document(file)
    for para in reader.paragraphs:
        data.append(para.text)
    text = " ".join(data)
    return text

def get_csv_file(file):
    data = []
    with open(file, "r", newline=" ", encoding="utf-8") as csv_file:
        csv_reader = reader(csv_file)
        for row in csv_reader:
            for cell in row:
                data.append(cell)
        text = " ".join(data)
    return text

def get_text_chunk(text):
    text_spliter  =CharacterTextSplitter(
        separator="\n",
        chunk_size=900,
        chunk_overlap=100,
        length_function=len
    )
    chunks = text_spliter.split_text(text)
    return chunks

def get_vectorstore(chunks):
    # embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-small-v2")
    # embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    knowledge_base = FAISS.from_texts(chunks, embeddings)
    return knowledge_base

def get_conversation_chain(vectorstore, openai_key):
    llm = ChatOpenAI(
        model_name = "gpt-3.5-turbo-16k",
        openai_api_key=openai_key,
        temperature=0
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    chains = ConversationalRetrievalChain.from_llm(
        llm=llm,
        memory=memory,
        retriever=vectorstore.as_retriever()
    )

    return chains

def handle_userinput(query):
    with get_openai_callback():
        response = st.session_state.conversation({"question":query})
    st.session_state.chat_history = response["chat_history"]

    with st.container():
        for i, messages in enumerate(st.session_state.chat_history):
            if (i%2==0):
                message(messages.content, is_user=True, key=str(i))
            else:
                message(messages.content, key=str(i))


if __name__ == "__main__":
    main()

