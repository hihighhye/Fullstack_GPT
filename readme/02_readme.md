# PrivateGPT

<img src="images/Flow of PrivateGPT.png" width="400" />

<br>
<br>

## Description

A Private Chatbot that users are able to upload a file and ask about the content. Using ChatOllama instead of ChatOpenAI, the conversation between user and chatbot remains confidential.

<br>

## The Structure of Chain

> - **retriever(Vectorstore: FAISS) + Stuff prompt + LLM(ChatOllama: mistral)**

<br>

## Stuff Retrieval

```
prompt = ChatPromptTemplate.from_template(
    """
    Answer the question using ONLY the following context and not your training data. If you don't know the answer
    just say you don't know. DON'T make anything up.

    Context: {context}
    Question: {question}
    """
)
```

<br>
<br>
<br>
