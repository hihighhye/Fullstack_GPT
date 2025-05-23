# DocumentGPT

<img src="https://github.com/user-attachments/assets/8bf05058-e21f-4d2f-975e-f75f513a36b9" alt="Flow of DocumentGPT" width="400" />

<br>
<br>

## Description

A Chatbot that users are able to upload a file and ask about the content. Using ChatOpenAI(GPT-3.5-turbo) with memory, the model can remember the previous conversation and understand the context of user's questions.

<br>

## The Structure of Chain

> - **retriever(Vectorstore: FAISS) + Stuff prompt + LLM(ChatOpenAI: GPT-3.5-turbo) + ConversationBufferMemory**

<br>

## Stuff Retrieval

```
prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Answer the question using ONLY the following context. If you don't know the answer
    just say you don't know. DON'T make anything up.

    Context: {context}
    """),
    ("human", "{question}")
])
```

<br>

## ConversationBufferMemory

대화 내용 전체 저장. 비효울적. 고비용. 텍스트 자동완성 기능 구현 시 유용.
<br>
\*Ref. [langchain official document](https://python.langchain.com/api_reference/langchain/memory/langchain.memory.buffer.ConversationBufferMemory.html#conversationbuffermemory)

<br>
<br>
<br>
