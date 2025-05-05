import streamlit as st
from langchain_community.retrievers import WikipediaRetriever
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain_core.documents import Document
from langchain.schema import BaseOutputParser, output_parser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
import json


format = {
            "name": "create_quiz",
            "description": "function that takes a list of questions and answers and returns a quiz",
            "parameters": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                },
                                "answers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "answer": {
                                                "type": "string",
                                            },
                                            "correct": {
                                            "type": "boolean",
                                            },
                                        },
                                        "required": ["answer", "correct"],
                                        },
                                },
                            },
                            "required": ["question", "answers"],
                            },
                        }
                    },
                    "required": ["questions"],
            },
}

llm = ChatOpenAI(
    temperature=0.1,
    model="gpt-4.1-nano-2025-04-14",
    streaming=True,
    callbacks=[
        StreamingStdOutCallbackHandler()
    ]
).bind(
    function_call={
        "name": "create_quiz",
    },
    functions=[
        format
    ],
)

questions_prompt = ChatPromptTemplate.from_messages( [
        (
            "system",
            """
            You are a helpful assistant that is role playing as a teacher.
                
            Based ONLY on the following context make {number} questions with the level of difficulty the user chose
            in order to test the user's knowledge about the text.
            *The level of difficulty: from Level 1(The easiest) to Level 3(The hardest)
            -----
            The level user chose: {level}
            
            Keep in mind that each question should have 4 answers, three of them must be incorrect and one should be correct.
                
                
            Questions examples:
                
            Question: What is the color of the ocean?
            Answers: [ (Red, False) | (Yellow, False) | (Green, False) | (Blue, True) ]
                
            Question: What is the capital or Georgia?
            Answers: [ (Baku, False) | (Tbilisi, True) | (Manila, False) | (Beirut, False) ]
                
            Question: When was Avatar released?
            Answers: [ (2007, False) | (2001, False) | (2009, True) | (1998, False) ]
                
            Question: Who was Julius Caesar?
            Answers: [ (A Roman Emperor, True) | (Painter, False) | (Actor, False) | (Model, False) ]
                
            Your turn!
                
            Context: {context}
        """,
        )
    ])

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

questions_chain = questions_prompt | llm


st.set_page_config(
    page_title="QuizGPT",
    page_icon="🎲"
)

st.title("QuizGPT")

@st.cache_data(show_spinner="Loading file...")
def split_file(file):
    # st.write(file)
    file_content = file.read()
    file_path = f"./.cache/quiz_files/{file.name}"
    # st.write(file_content, file_path)

    with open(file_path, "wb") as f:
        f.write(file_content)

    splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator="\n",
        chunk_size=600,
        chunk_overlap=100,
    )

    # loader = UnstructuredFileLoader(file_path)
    # docs = loader.load_and_split(text_splitter=splitter)   ### didn't work...

    docs = splitter.split_text(file_content.decode('utf-8'))
    docs = [ Document(page_content=doc) for doc in docs ]
    return docs


@st.cache_data(show_spinner="Making quiz...")
def run_quiz_chain(_docs, number, level, topic):
    formatted_docs = format_docs(_docs)
    return questions_chain.invoke({"context": formatted_docs, "number": number, "level": level})

@st.cache_data(show_spinner="Searching Wikipedia...")
def wiki_search(term):
    retriever = WikipediaRetriever(top_k_results=5)
    docs = retriever.invoke(term) # retriever.get_relevant_documents(term)
    return docs


with st.sidebar:
    docs = None
    topic = None
    level = None

    number = st.number_input("The number of questions", value=10, step=1)

    level = st.selectbox("The level of difficulty", (
        "Level 1",
        "Level 2",
        "Level 3"
    ))

    choice = st.selectbox("Choose what you want to use", (
        "File", 
        "Wikipedia Article",
    ))

    if choice == "File":
        file = st.file_uploader("Upload a .docx, .txt or .pdf file", type=["pdf", 'txt', "docx"])

        if file:
            docs = split_file(file)

    else:
        topic = st.text_input("The topic to learn")
        if topic:
            docs = wiki_search(topic)

if not docs:
    st.markdown("""
                Welcom to QuizGPT.

                I will make a quiz from Wikipedia articles or files you upload to test
                your knowledge and help you study.

                Get started by uploading a file or searching on Wikipedia in the sidebar.
                """)
    
else:
    _response = run_quiz_chain(docs, number, level, topic if topic else file.name)
    response = json.loads(_response.additional_kwargs["function_call"]["arguments"])
    # st.write(response)

    with st.form("questions_form"):
        i = 1
        for question in response["questions"]:
            st.write(str(i) + ". ", question["question"])
            value = st.radio("Select an option", [answer["answer"] for answer in question["answers"]],
                     index=None)
            i += 1
            
            if {"answer": value, "correct": True} in question["answers"]:
                st.success("Correct!")
            elif value is not None:
                st.error("Wrong")

        button = st.form_submit_button()