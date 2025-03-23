c
import streamlit as st
import google.generativeai as genai
import os
import tempfile
import whisper
import re  # For cleaning text

def configure_gemini():
    """Configures Gemini API with the provided API key."""
    api_key = st.session_state.get("gemini_api_key")
    
    if not api_key:
        st.warning("Please enter your Gemini API key.")
        return False
    
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {e}")
        return False

def clean_transcript(text):
    """Removes unnecessary metadata, HTML tags, and scripts from the transcript."""
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)  # Remove scripts
    text = re.sub(r'<.*?>', '', text)  # Remove any HTML tags
    text = re.sub(r'https?://\S+', '', text)  # Remove URLs
    text = re.sub(r'Clone this repository.*', '', text, flags=re.IGNORECASE)  # Remove GitHub gist references
    return text.strip()

def transcribe_audio(audio_path):
    """Transcribes audio using Whisper model."""
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return clean_transcript(result['text'])  # Clean transcript before use

def get_available_model():
    """Fetches an available Gemini model."""
    try:
        available_models = [model.name for model in genai.list_models()]
        print("DEBUG: Available models:", available_models)

        for model_name in [
            "gemini-1.5-pro-latest",  
            "gemini-1.5-pro-002",
            "gemini-1.5-pro",
            "gemini-2.0-pro-exp",
            "gemini-2.0-pro-exp-02-05"
        ]:
            if f"models/{model_name}" in available_models:
                print(f"DEBUG: Using model {model_name}")
                return f"models/{model_name}"

        return None
    except Exception as e:
        print(f"Error fetching available models: {e}")
        return None

def summarize_text(text):
    """Generates a summary using the selected Gemini model."""
    model_name = get_available_model()
    if model_name is None:
        return "Error: No available Gemini model found. Check your API access."

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(f"Summarize the following meeting transcript concisely: {text}")
        return response.text
    except Exception as e:
        return f"Error generating summary: {e}"

def main():
    st.title("Meeting Summary App")
    st.write("Upload a meeting recording or transcript to get a summary.")

    # Input field for Gemini API key (now using session state correctly)
    st.text_input("Enter your Gemini API key:", type="password", key="gemini_api_key")

    if not configure_gemini():
        return

    uploaded_audio = st.file_uploader("Upload Audio File", type=["mp3", "wav", "m4a"])
    uploaded_transcript = st.file_uploader("Upload Transcript File (TXT)", type=["txt"])

    transcript = None  # Initialize transcript variable

    if uploaded_audio is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(uploaded_audio.read())
            temp_audio_path = temp_audio.name

        st.write("Transcribing the audio...")
        transcript = transcribe_audio(temp_audio_path)
        os.remove(temp_audio_path)

    elif uploaded_transcript is not None:
        transcript = uploaded_transcript.read().decode("utf-8")
        transcript = clean_transcript(transcript)  # Clean the uploaded transcript

    # Debugging: Show transcript content before summarization
    if transcript:
        st.write("Transcript Received ✅")
        st.text_area("Transcript Preview", transcript[:1000])  # Show first 1000 chars

        st.write("Generating summary...")
        summary = summarize_text(transcript)

        st.subheader("Meeting Summary:")
        st.write(summary)
    else:
        st.warning("Please upload either an audio file or a transcript.")

if __name__ == "__main__":
    main()
