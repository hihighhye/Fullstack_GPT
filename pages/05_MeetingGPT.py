import streamlit as st
import subprocess
from pydub import AudioSegment
import math
import openai
import glob
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.memory import ConversationBufferMemory


llm = ChatOpenAI(
    temperature=0.1,
)

memory = ConversationBufferMemory(
    llm=llm,
    max_token_limit=20,
    return_messages=True,
)

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                    chunk_size=800,
                    chunk_overlap=100,
                )

has_transcript = os.path.exists("./.cache/podcast.txt")

def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def load_memory(_):
    return memory.load_memory_variables({})["history"]

@st.cache_data()
def extract_audio_from_video(video_path):
    if has_transcript:
        return
    audio_path = video_path.replace("mp4", "mp3")
    command = ["ffmpeg", "-y", "-i", video_path, "-vn", audio_path]
    subprocess.run(command, shell=True)

@st.cache_data()
def cut_audio_in_chunks(audio_path, chunk_size, chunks_folder):
    if has_transcript:
        return
    track = AudioSegment.from_mp3(audio_path)
    chunk_len = chunk_size * 60 * 1000

    chunks = math.ceil(len(track) / chunk_len)

    for i in range(chunks):
        start_time = i * chunk_len
        end_time = (i+1) * chunk_len
        chunk = track[start_time:end_time]
        chunk.export(f"{chunks_folder}/chunk_{i}.mp3", format="mp3")

@st.cache_data()
def transcribe_chunks(chunks_folder, destination):
    if has_transcript:
        return
    files = glob.glob(f"{chunks_folder}/*.mp3")
    files.sort()

    for file in files:
        with open(file, "rb") as audio_file, open(destination, "a") as text_file:
            transcript = openai.audio.transcriptions.create(
                                model="whisper-1", 
                                file=audio_file,
                        )
            text_file.write(transcript.text)

@st.cache_resource(show_spinner="Embedding file...")
def embed_file(file_path):
    cache_dir = LocalFileStore(f"./.cache/embeddings/{file.name}")

    loader = TextLoader(file_path)
    docs = loader.load_and_split(text_splitter=splitter)
    embeddings = OpenAIEmbeddings()
    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
        embeddings, cache_dir
    )
    embeddings = OpenAIEmbeddings()
    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embeddings, cache_dir)
    vectorstore = FAISS.from_documents(docs, cached_embeddings)
    retriver = vectorstore.as_retriever()
    
    return retriver


st.set_page_config(
    page_title="MeetingGPT",
    page_icon="👩‍💻",
)

st.title("MeetingGPT")

with st.sidebar:
    video = st.file_uploader(
            "Video", 
            type=["mp4", "avi", "mkv", "mov"]
        )

if video:
    video_content = video.read()
    video_path = f"./.cache/{video.name}"
    video_ext = video.name.split(".")[-1]
    audio_path = video_path.replace(video_ext,"mp3")
    chunks_folder = "./.cache/chunks"
    transcript_path = video_path.replace(video_ext,"txt")
    with st.status("Loading video....") as status:
        with open(video_path, "wb") as f:
            f.write(video_content)
        status.update(label="Extracting audio...")
        extract_audio_from_video(video_path)
        status.update(label="Cutting the audio segments...")
        cut_audio_in_chunks(audio_path, 10, chunks_folder)
        status.update(label="Transcribing audio...")
        transcribe_chunks(chunks_folder, transcript_path)
        status.update(label="Successfully ready with the transcript.")

    transcript_tab, summary_tab, qna_tab = st.tabs(
        [
            "Transcript",
            "Summary",
            "Q&A"
        ]
    )

    with transcript_tab:
        with open(transcript_path, "r") as file:
            st.write(file.read())

    with summary_tab:
        start = st.button("Generate summary")

        if start:
            with st.status("Summarizing...") as status:
                loader = TextLoader(transcript_path)

                docs = loader.load_and_split(text_splitter=splitter)

                first_summary_prompt = ChatPromptTemplate.from_template(
                    """
                        Write a concise summary of the following:
                        "{text}"
                        CONCISE SUMMARY:
                    """
                )

                first_summary_chain = first_summary_prompt | llm | StrOutputParser()

                status.update(label=f"Processing document 1 / {len(docs)}")
                summary = first_summary_chain.invoke({
                    "text": docs[0].page_content
                })

                refine_prompt = ChatPromptTemplate.from_template(
                    """
                    Your job is to produce a final summary.
                    We have provided an existing summary up to a
                    certain point: {existing_summary}
                    We have the opportunity to refine the existing 
                    summary (only if needed) with some more context
                    below.
                    -------------
                    {text}
                    -------------
                    Given the new context, refine the original
                    summary.
                    If the context isn't useful, RETURN the
                    original summary.
                    """
                )

                refine_chain = refine_prompt | llm | StrOutputParser()

                for i, doc in enumerate(docs[1:]):
                    status.update(label=f"Processing document {i+2} / {len(docs)}")
                    summary = refine_chain.invoke({
                        "existing_summary": summary,
                        "text": doc.page_content
                    })

            st.write(summary)

    with qna_tab:
        retriever = embed_file(transcript_path)

        query = st.text_input("Ask anything about the audio content that you uploaded.")

        if query:
            save_message(query, "human")
            with st.spinner("Loading..."):            
                qna_prompt = ChatPromptTemplate.from_messages([
                    (
                        "system",
                        """
                            Answer the question using ONLY the following context and the conversation history. 
                            If you don't know the answer,
                            just say you don't know. DON'T make anything up.
        
                            Context: {context}
                        """
                    ),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{question}")
                ])
                qna_chain = {
                        "context": retriever | RunnableLambda(format_docs), 
                        "question": RunnablePassthrough(),
                        "history": load_memory
                    } | qna_prompt | llm

                res = qna_chain.invoke(query)
                st.write(res.content)
                memory.save_context({"input": query}, {"output": res.content})

else:
    st.session_state["messages"] = []

    