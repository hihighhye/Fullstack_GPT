import streamlit as st
import nest_asyncio
from langchain_core.documents import Document
from langchain_community.document_loaders import SitemapLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter 
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import re


llm = ChatOpenAI(
    temperature=0.1,
    model="gpt-4.1-nano-2025-04-14",
)

answers_prompt = ChatPromptTemplate.from_template(
                """
                Using ONLY the following context answer the user's question.
                If you can't just say you don't know, don't make anything up.

                Then, give a score to the answer between 0 and 5. 0 being not helpful to
                the user and 5 being helpful to the user.

                Make sure to include the answer's score.

                Context: {context}

                Examples:

                Question: How far away is the moon?
                Answer: The moon is 384,400 km away.
                Score: 5

                Question: How far away is the sun?
                Answer: I don't know.
                Score: 0

                Your turn!

                Question: {question}
                """)

choose_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Use ONLY the following pre-existing answers to answer the user's
            question.

            Use the answers that have the highest score (more helpful).

            Cite sources. Do not modify the source, keep it as a link.

            Answers: {answers}
            """
        ),
        (
            "human",
            "{question}"
        )
    ]
)

def choose_answer(inputs):
    answers = inputs["answers"]
    question = inputs["question"]

    choose_chain = choose_prompt | llm

    condensed = "\n\n".join(f"Answer: {answer['answer']}\n\
                            Source: {answer['source']}\n" for answer in answers) #   Date: {answer['date']}\n
    
    return choose_chain.invoke({"question": question,"answers": condensed})

def get_answers(inputs):
    docs = inputs["docs"]
    question = inputs["question"]

    answers_chain = answers_prompt | llm
    # answers = []
    # for doc in docs:
    #     result = answers_chain.invoke({"context": doc.page_content, "question": question})
    #     answers.append(result.content)

    # st.write(answers)

    # st.write(docs)
    return {
        "question": question,
        "answers": [
            {
                "answer": answers_chain.invoke(
                    {"context": doc.page_content, "question": question}
                ).content,
                "source": doc.metadata["source"],
                # "date": doc.metadata["lastmod"]
            } for doc in docs
        ]
    }

def parse_page(soup):
    header = soup.find("header")
    footer = soup.find("footer")
    navbar = soup.find("div", "navbar_container")
   
    if header:
        header.decompose()
    if footer:
        footer.decompose()
    if navbar:
        navbar.decompose()
    
    refined = re.sub("([\n\s\t]|\xa0| {2,})", " ",str(soup.get_text()))
    # refined = re.sub("LangChain                           Products  LangGraphLangSmithLangChainResources  Resources HubBlogCustomer StoriesLangChain AcademyCommunityExpertsChangelogDocs  PythonLangGraphLangSmithLangChainJavaScriptLangGraphLangSmithLangChainCompany  AboutCareersPricing", "", refined)
    return refined

@st.cache_resource(show_spinner="Loading website...")
def load_website(url):
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1000,
        chunk_overlap=200,
    )

    loader = SitemapLoader(
        url, 
        # filter_urls=[r"^(.*\/langchain).*"],
        parsing_function=parse_page
    )
    loader.requests_per_second = 5
    docs = loader.load_and_split(text_splitter=splitter)
    vector_store = FAISS.from_documents(docs, OpenAIEmbeddings())
    return vector_store.as_retriever()


st.set_page_config(
    page_title="SiteGPT",
    page_icon="🔦"
)

st.title("SiteGPT")

with st.sidebar:
    url = st.text_input("Write down a URL", 
                        placeholder="https://example.com")


if not url:
    st.markdown(
                """
                Ask questions about the content of a website.

                Start by writing the URL of the website on the sidebar.
            """)
    query = ""
    
else:
    # async chromium loader
    if ".xml" not in url:
        with st.sidebar:
            st.error("Please write down a Sitemap URL.")

    else:
        retriever = load_website(url)
        # docs = retriever.invoke("Can I use langchain in production?")
        query = st.text_input("Ask a question to the website.")
        
        if query:
            chain = {
                "docs": retriever, 
                "question": RunnablePassthrough()
            } | RunnableLambda(get_answers) | RunnableLambda(choose_answer)

            result = chain.invoke(query)

            st.write(result.content.replace("$", "\$"))

