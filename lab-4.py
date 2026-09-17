import streamlit as st
from openai import OpenAI
import tiktoken
import sys

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb
from pathlib import Path
from PyPDF2 import PdfReader

chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_Lab')
collection = chroma_client.get_or_create_collection('Lab4Collection')

st.title("Lab 4: Chatbot with Memory")

if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text = text + page.extract_text()
    return text


def add_to_collection(collection, text, file_name):
    client = st.session_state.openai_client
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding
    collection.add(
        documents=[text],
        ids=[file_name],
        embeddings=[embedding]
    )


if collection.count() == 0:
    pdf_files = Path("./pdf_data").glob("*.pdf")
    for pdf_path in pdf_files:
        text = extract_text_from_pdf(pdf_path)
        file_name = pdf_path.name
        add_to_collection(collection, text, file_name)


max_tokens = 1000

encoding = tiktoken.encoding_for_model("gpt-4o")

system_prompt = {
    "role": "system",
    "content": "You are a friendly chatbot. Explain things so a 10 year old can understand. Answer the user's question, then ask 'Do you want more info?' If they say yes, give more detail and ask again. If they say no, ask what else you can help with."
}

if "messages" not in st.session_state:
    st.session_state.messages = [system_prompt]

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

user_input = st.chat_input("Ask me something")

if user_input:

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    client = st.session_state.openai_client

    query_response = client.embeddings.create(
        input=user_input,
        model="text-embedding-3-small"
    )
    query_embedding = query_response.data[0].embedding

    search_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    retrieved_text = ""
    for i in range(len(search_results["documents"][0])):
        doc_name = search_results["ids"][0][i]
        doc_text = search_results["documents"][0][i]
        retrieved_text = retrieved_text + f"From {doc_name}:\n{doc_text}\n\n"

    history = st.session_state.messages[1:]

    buffer = []
    total_tokens = 0

    for message in reversed(history):
        message_tokens = len(encoding.encode(message["content"]))
        if total_tokens + message_tokens > max_tokens:
            break
        buffer.insert(0, message)
        total_tokens = total_tokens + message_tokens

    context_message = {
        "role": "system",
        "content": "The following is course material retrieved from the syllabus documents for this specific question. When you use this material in your answer, start your response with 'Based on the course materials:' so it's clear you're using retrieved knowledge. If the material doesn't help answer the question, say so and answer from general knowledge instead.\n\n" + retrieved_text
    }
    

    messages_to_send = [system_prompt] + buffer + [context_message]

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            stream = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages_to_send,
                stream=True,
            )
            response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})