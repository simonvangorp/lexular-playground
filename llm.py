import os
import asyncio
import streamlit as st
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Set the API model
openai_model = 'gpt-4o-mini'  # You can change this to 'gpt-4' or any other model

# Flexible API key loading for OpenAI
def load_openai_api_key():
    try:
        api_key = st.secrets['openai_api_key']
    except Exception:
        load_dotenv()
        api_key = os.getenv('openai_api_key')

    if not api_key:
        raise ValueError("OpenAI API key is not properly loaded. Please check your setup.")

    return api_key

# Initialize the OpenAI client after API key is properly loaded
openai_api_key = load_openai_api_key()
client = AsyncOpenAI(api_key=openai_api_key)

def initialize_chatbot():
    """
    Initialize chatbot session state for Streamlit.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "model" not in st.session_state:
        st.session_state.model = openai_model

def display_chat():
    """
    Render chat messages in the Streamlit interface.
    """
    if "messages" in st.session_state:
        for message in st.session_state["messages"]:
            if message["role"] == "system":
                # Skip displaying system messages
                continue
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

def handle_user_input():
    """
    Handle user input and generate responses in the chatbot.
    """
    if user_prompt := st.chat_input("Your prompt"):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # Use OpenAI API to generate chatbot response
            try:
                response = asyncio.run(
                    client.chat.completions.create(
                        model=st.session_state.model,
                        messages=st.session_state.messages,
                    )
                )
                full_response = response.choices[0].message.content
                message_placeholder.markdown(full_response)
            except Exception as e:
                message_placeholder.markdown(f"Fout bij ophalen antwoord: {e}")

        st.session_state.messages.append({"role": "assistant", "content": full_response})

def generate_first_response(messages):
    """
    Generate the first response from the chatbot based on the provided initial messages.
    """
    response = asyncio.run(
        client.chat.completions.create(
            model=openai_model,
            messages=messages,
        )
    )
    return response.choices[0].message.content
