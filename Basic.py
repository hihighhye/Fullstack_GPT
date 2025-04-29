import streamlit as st
from langchain.prompts import PromptTemplate
from datetime import datetime


today = datetime.today().strftime("%H:%M:%S")

st.title(today)

# st.title("Hello world!")
# st.subheader("Welcome to streamlit")
# st.markdown(
#     """
#     #### I love it!
#     """
# )

# st.write("hello")

# st.write([1, 2, 3])

# st.write({"x": 1})

# st.write(PromptTemplate)


# p = PromptTemplate.from_template("xxxxx")

# st.write(p)

model = st.selectbox(
    "Choose your model",
    (
        "GPT-3",
        "GPT-4"
    )
)

if model == "GPT-3":
    st.write("cheap")
else:
    st.write("expensive")

name = st.text_input("What is your name?")

st.write(name)

value = st.slider("temperature", min_value=0.1, max_value=1.0,)

st.write(value)





##### Chapter 7. DocumentGPT

import streamlit as st
import time

st.set_page_config(
    page_title="DocumentGPT",
    page_icon="📝"
)

st.title("DocumentGPT")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

def send_message(message, role, save=True):
    with st.chat_message(role):
        st.write(message)
    if save:
        st.session_state["messages"].append({"message": message, "role": role})

for message in st.session_state["messages"]:
    send_message(message["message"], message["role"], save=False)

# with st.status("Embedding files...", expanded=True) as status:
#     time.sleep(2)
#     st.write("Getting the file")
#     time.sleep(2)
#     st.write("Embedding the file")
#     time.sleep(2)
#     st.write("Caching the file")
#     status.update(label="Error", state="error")



message = st.chat_input("Send a message to the AI.")

if message:
    send_message(message, "human")
    time.sleep(1)
    send_message(f"You said: {message}", "ai")

    with st.sidebar:
        st.write(st.session_state)