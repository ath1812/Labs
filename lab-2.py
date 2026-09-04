import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI

# ---------- Page setup ----------
st.title("📄 Lab 2: Document Summarizer")
st.write(
    "Upload a PDF and get a summary. Choose the summary style, output language, "
    "and model below."
)

# ---------- Get the API key from Streamlit secrets (no text box) ----------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------- Controls in the main page body (not the sidebar) ----------
LANGUAGES = ["English", "Spanish", "French", "German", "Chinese"]
SUMMARY_TYPES = {
    "100 words": "Summarize the document in exactly 100 words.",
    "2 connecting paragraphs": "Summarize the document in 2 connecting paragraphs.",
    "5 bullet points": "Summarize the document in 5 concise bullet points.",
}

col1, col2 = st.columns(2)
with col1:
    language = st.selectbox("Summary language", LANGUAGES)
with col2:
    summary_choice = st.selectbox("Summary type", list(SUMMARY_TYPES.keys()))

use_advanced_model = st.checkbox("Use advanced model")

# Basic model = nano, advanced model = mini.
model_name = "gpt-5-mini" if use_advanced_model else "gpt-5-nano"


def read_pdf(uploaded_file):
    """Read text from an uploaded PDF file."""
    try:
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_pages = [page.get_text() for page in pdf_document]
        pdf_document.close()
        return "\n".join(text_pages)
    except Exception as exc:
        st.error(f"Unable to read PDF file: {exc}")
        return ""


# ---------- Upload + summarize ----------
uploaded_file = st.file_uploader("Upload a PDF document", type=("pdf",))

if uploaded_file:
    document = read_pdf(uploaded_file)

    if document:
        instruction = SUMMARY_TYPES[summary_choice]

        messages = [
            {
                "role": "user",
                "content": (
                    f"{instruction} Write the summary in {language}.\n\n"
                    f"Document:\n{document}"
                ),
            }
        ]

        if st.button("Generate summary"):
            with st.spinner(f"Summarizing with {model_name}..."):
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                )
                st.subheader(f"Summary ({summary_choice}, {language}, {model_name})")
                st.write_stream(stream)