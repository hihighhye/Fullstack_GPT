from fastapi import FastAPI, Body, Form, Request
from typing import Any, Dict
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore


load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder()

embeddings = OpenAIEmbeddings()

vector_store = PineconeVectorStore.from_existing_index(
    "recipes", 
    embeddings
)


app = FastAPI(
    title="ChefGPT. The best provider of Indian Recipes in the world.",
    description="Give ChefGPT a couple of ingredients and it will give you recipes in return.",
    servers=[
        {"url": "https://institutes-senior-fears-webshots.trycloudflare.com"}   ## 수정 필요.
    ]
)

class Document(BaseModel):
    page_content:str

@app.get(
        "/recipes", 
        summary="Returns a list of recipes.",
        description="Upon receiving an ingredient, this endpoint will return a\
            list of recipes that contain that ingredient.",
        response_description="A Document object that contains the recipe and preparation instructions",
        response_model=list[Document],
        openapi_extra={
            "x-openai-isConsequential": False,
        }
)

def get_recipe(ingredient:str):
    docs = vector_store.similarity_search(ingredient)
    return docs


user_token_db = {
    "ABCDEF": "nico"
}

@app.get("/authorize", response_class=HTMLResponse, include_in_schema=False)
def handle_authorize(client_id:str, redirect_uri:str, state:str):
    print(
        client_id,
        redirect_uri,
        state,
    )

    return f"""
    <html>
        <head>
            <title>ChefGPT Log In</title>
        </head>
        <body>
            <h1>Log Into ChefGPT</h1>
            <a href="{redirect_uri}?code=ABCDEF&state={state}">Authorize ChefGPT</a>
        </body>
    </html>
    """

@app.post("/token", include_in_schema=False)
def handle_token(code = Form(...)):
    print(code)
    return {
        "access_token": user_token_db[code]
    }

