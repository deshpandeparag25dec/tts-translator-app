import streamlit as st
from google import genai
from gtts import gTTS
from dotenv import load_dotenv
from pypdf import PdfReader
import pandas as pd
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

LANGUAGES = {
    "French": "fr", "Spanish": "es", "Hindi": "hi",
    "German": "de", "Japanese": "ja", "Arabic": "ar", "Marathi": "mr"
}

st.title("Text to Speech Translator")
st.write("Type text or upload a file, pick a language, and get translated speech.")

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "result" not in st.session_state:
    st.session_state.result = None


def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.name.split(".")[-1].lower()
    try:
        if file_type == "txt":
            raw_bytes = uploaded_file.read()
            try:
                return raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return raw_bytes.decode("utf-16")
                except UnicodeDecodeError:
                    return raw_bytes.decode("latin-1", errors="replace")
        elif file_type == "pdf":
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif file_type == "csv":
            df = pd.read_csv(uploaded_file)
            return df.to_string()
        elif file_type in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
            return df.to_string()
        else:
            return ""
    except Exception as e:
        st.error(f"Couldn't read that file - it may be corrupted or in an unexpected format. ({e})")
        return ""


def translate_text(input_text, target_language):
    prompt = f"Translate the following text to {target_language}. Translate it literally and do not add, infer, guess, or correct any information that is not explicitly present in the source text. Respond with ONLY the translated text, nothing else: {input_text}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()


def generate_audio(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    tts.save("output.mp3")
    audio_file = open("output.mp3", "rb")
    audio_bytes = audio_file.read()
    audio_file.close()
    return audio_bytes


user_text = st.text_area("Enter text to translate:", key=f"text_{st.session_state.reset_counter}")
uploaded_file = st.file_uploader(
    "...or upload a file (TXT, PDF, CSV, XLSX):",
    type=["txt", "pdf", "csv", "xlsx"],
    key=f"file_{st.session_state.reset_counter}"
)
target_language = st.selectbox("Translate to:", list(LANGUAGES.keys()))

if st.button("Translate & Speak"):
    input_text = ""
    if uploaded_file is not None:
        input_text = extract_text_from_file(uploaded_file)
        if user_text.strip() != "":
            st.info("Both text and a file were provided - using the uploaded file. Remove the file to translate your typed text instead.")
    else:
        input_text = user_text

    if input_text.strip() == "":
        st.warning("Please enter text or upload a file with readable content.")
    elif len(input_text) > 2000:
        st.warning(f"Your input is {len(input_text)} characters. Please limit it to 2000 characters for reasonable processing time.")
    else:
        lang_code = LANGUAGES[target_language]
        translated_text = None

        try:
            with st.spinner("Translating..."):
                translated_text = translate_text(input_text, target_language)
        except Exception as e:
            st.error(f"Translation failed. This is usually a temporary API issue - please try again. ({e})")

        if translated_text:
            try:
                with st.spinner("Generating audio..."):
                    audio_bytes = generate_audio(translated_text, lang_code)
                st.session_state.result = {
                    "translated_text": translated_text,
                    "audio_bytes": audio_bytes
                }
            except Exception as e:
                st.error(f"Couldn't generate audio for this text/language combination. ({e})")

if st.session_state.result:
    st.subheader("Translated Text:")
    st.write(st.session_state.result["translated_text"])
    st.audio(st.session_state.result["audio_bytes"], format="audio/mp3")
    st.download_button("Download MP3", st.session_state.result["audio_bytes"], file_name="translation.mp3")

    if st.button("Start Over"):
        st.session_state.result = None
        st.session_state.reset_counter += 1
        st.rerun()