import streamlit as st
from openai import OpenAI
import tiktoken

st.title("Lab 3: Chatbot with Memory")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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

    history = st.session_state.messages[1:]

    buffer = []
    total_tokens = 0

    for message in reversed(history):
        message_tokens = len(encoding.encode(message["content"]))
        if total_tokens + message_tokens > max_tokens: 
            break
        buffer.insert(0, message)
        total_tokens = total_tokens + message_tokens

    messages_to_send = [system_prompt] + buffer

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            stream = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages_to_send,
                stream=True,
            )
            response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})