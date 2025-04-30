import streamlit as st
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
from langchain.vectorstores import FAISS
from langchain.storage import LocalFileStore
from langchain_core.documents import Document
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.memory import ConversationBufferMemory


class ChatCallbackHandler(BaseCallbackHandler):
    message = ""

    def on_llm_start(self, *args, **kwargs):
        self.message_box = st.empty()

    def on_llm_end(self, *args, **kwargs):
        save_message(self.message, "ai")

    def on_llm_new_token(self, token, *args, **kwargs):
        self.message += token
        self.message_box.markdown(self.message)

def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})
    
@st.cache_data(show_spinner="Embedding a file...")
def embed_file(file):
    # st.write(file)
    file_content = file.read()
    file_path = f"./.cache/files/{file.name}"
    # st.write(file_content, file_path)

    with open(file_path, "wb") as f:
        f.write(file_content)

    cache_dir = LocalFileStore(f"./.cache/embeddings/{file.name}")

    splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator="\n",
        chunk_size=600,
        chunk_overlap=100,
    )

    # loader = UnstructuredFileLoader(file_path)
    # docs = loader.load_and_split(text_splitter=splitter)   ### didn't work...

    docs = splitter.split_text(file_content.decode('utf-8'))
    docs = [ Document(page_content=doc) for doc in docs ]
    
    embeddings = OpenAIEmbeddings()
    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embeddings, cache_dir)
    vectorstore = FAISS.from_documents(docs, cached_embeddings)
    retriver = vectorstore.as_retriever()
    
    return retriver

def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)

def paint_history():
    for message in st.session_state["messages"]:
        send_message(
            message["message"],
            message["role"],
            save=False
        )

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def load_memory(_):
    return memory.load_memory_variables({})["history"]

prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Answer the question using ONLY the following context. If you don't know the answer
    just say you don't know. DON'T make anything up.
     
    Context: {context}
    """),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])


st.set_page_config(
    page_title="DocumentGPT",
    page_icon="📝"
)

st.title("DocumentGPT")

st.markdown("""
Welcome!
            
Use this chatbot to ask questions to an AI about your files!
            
Upload your file on the sidebar.
"""
)

with st.sidebar:
    st.title("Requirements")
    with st.form("OpenAI API Key Setting"):
        user_openai_api_key = st.text_input("Enter your OpenAI API key.")
        submitted = st.form_submit_button("Set")
        if submitted:
            st.write(f"Your API Key: {user_openai_api_key}")

    file = st.file_uploader("Upload a file. [ *Supported extensions: txt / docx ]", 
                            type=["txt", "docx"]    # "pdf", 
    )

    st.link_button("Go to Github Repo", "https://github.com/hihighhye/Fullstack_GPT")

if user_openai_api_key:
    llm = ChatOpenAI(
        temperature=0.1,
        streaming=True,
        callbacks=[
            ChatCallbackHandler()
        ],
        api_key=user_openai_api_key
    )

    memory = ConversationBufferMemory(
        llm=llm,
        max_token_limit=120,
        return_messages=True,
    )

if file:
    retriever = embed_file(file)
    
    send_message("I'm ready! Ask away!", "ai", save=False)
    paint_history()
    message = st.chat_input("Ask anything about your file...")
    
    if message:
        send_message(message, "human")
        chain = {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
            "history": load_memory
        } | prompt | llm

        with st.chat_message("ai"):
            result = chain.invoke(message)
            memory.save_context(
                                    {"input": message},
                                    {"output": result.content},
                                )
else:
    st.session_state["messages"] = []