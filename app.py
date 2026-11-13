"""Meeting Summary: upload a recording or transcript, get a structured summary with action items."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

import summarizer as core

SAMPLE = Path(__file__).parent / "samples" / "product_sync.txt"

st.set_page_config(page_title="Meeting Summary", page_icon="📝", layout="wide")


@st.cache_resource(show_spinner=False)
def whisper_model(size: str):
    return core.load_whisper(size)


@st.cache_resource(show_spinner=False)
def gemini_client(api_key: str):
    return core.make_client(api_key)


@st.cache_data(show_spinner=False, ttl=3600)
def model_names(api_key: str) -> list[str]:
    return core.available_models(gemini_client(api_key))


# ---------- Sidebar: settings ----------

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Gemini API key",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help="Get one free at https://aistudio.google.com/apikey. You can also set GEMINI_API_KEY.",
    )
    model = None
    if api_key:
        try:
            names = model_names(api_key)
            default = core.pick_model(names)
            if names:
                model = st.selectbox("Gemini model", names, index=names.index(default) if default in names else 0)
            else:
                st.error("This key cannot use any Gemini text models.")
        except Exception as e:  # bad key, network, quota
            st.error(f"Could not reach Gemini: {e}")

    whisper_size = st.selectbox(
        "Transcription model",
        ["tiny", "base", "small", "medium"],
        index=1,
        help="Runs locally with faster-whisper. Larger is more accurate but slower.",
    )
    language = st.selectbox("Audio language", ["Auto-detect", "en", "hi", "es", "pt", "fr", "de"], index=0)
    show_timestamps = st.checkbox("Keep timestamps in transcript", value=True)

# ---------- Main: input ----------

st.title("📝 Meeting Summary")
st.caption("Upload a meeting recording or transcript. Get the decisions, action items and open questions.")

tab_audio, tab_text, tab_paste = st.tabs(["🎧 Audio", "📄 Transcript file", "✍️ Paste text"])

with tab_audio:
    audio = st.file_uploader("Recording", type=["mp3", "wav", "m4a", "ogg", "webm", "mp4"])
    if audio is not None:
        st.audio(audio)
        if st.button("Transcribe", type="primary"):
            suffix = Path(audio.name).suffix or ".audio"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio.getvalue())
                path = tmp.name
            try:
                with st.spinner(f"Loading the {whisper_size} model and transcribing… (first run downloads the model)"):
                    segs, lang = core.transcribe(
                        whisper_model(whisper_size), path, None if language == "Auto-detect" else language
                    )
                st.session_state.transcript = core.segments_to_text(segs, timestamps=show_timestamps)
                st.session_state.source = f"{audio.name} · detected language: {lang}"
                st.session_state.pop("summary", None)
            except Exception as e:
                st.error(f"Transcription failed: {e}")
            finally:
                os.remove(path)

with tab_text:
    doc = st.file_uploader("Transcript (.txt, .vtt, .srt)", type=["txt", "vtt", "srt"])
    if doc is not None and st.button("Use this transcript"):
        st.session_state.transcript = core.clean_transcript(doc.getvalue().decode("utf-8", errors="replace"))
        st.session_state.source = doc.name
        st.session_state.pop("summary", None)
    if SAMPLE.exists() and st.button("Try the sample meeting"):
        st.session_state.transcript = core.clean_transcript(SAMPLE.read_text())
        st.session_state.source = "Sample: product sync"
        st.session_state.pop("summary", None)

with tab_paste:
    pasted = st.text_area("Transcript text", height=200, placeholder="Speaker A: …")
    if st.button("Use pasted text") and pasted.strip():
        st.session_state.transcript = core.clean_transcript(pasted)
        st.session_state.source = "Pasted text"
        st.session_state.pop("summary", None)

transcript = st.session_state.get("transcript")
if not transcript:
    st.info("Add a recording or transcript above to begin.")
    st.stop()

# ---------- Transcript + summary ----------

st.divider()
left, right = st.columns([2, 3], gap="large")

with left:
    st.subheader("Transcript")
    st.caption(f"{st.session_state.get('source', '')} · {len(transcript.split()):,} words")
    st.text_area("Transcript", transcript, height=480, label_visibility="collapsed")
    st.download_button("Download transcript", transcript, file_name="transcript.txt")

with right:
    st.subheader("Summary")
    if not api_key or not model:
        st.warning("Add a Gemini API key in the sidebar to summarise.")
        st.stop()

    if st.button("Summarise meeting", type="primary") or "summary" in st.session_state:
        if "summary" not in st.session_state:
            with st.spinner(f"Summarising with {model}…"):
                try:
                    st.session_state.summary = core.summarize(gemini_client(api_key), model, transcript)
                except Exception as e:
                    st.error(f"Summary failed: {e}")
                    st.stop()
        s: core.MeetingSummary = st.session_state.summary

        st.markdown(f"### {s.title}")
        st.write(s.tldr)
        if s.participants:
            st.caption("Participants: " + ", ".join(s.participants))

        c1, c2, c3 = st.columns(3)
        c1.metric("Decisions", len(s.decisions))
        c2.metric("Action items", len(s.action_items))
        c3.metric("Open questions", len(s.open_questions))

        st.markdown("**Key points**")
        st.markdown("\n".join(f"- {p}" for p in s.key_points) or "_None_")
        st.markdown("**Decisions**")
        st.markdown("\n".join(f"- {d}" for d in s.decisions) or "_None_")
        st.markdown("**Action items**")
        if s.action_items:
            st.dataframe(
                [{"Task": a.task, "Owner": a.owner, "Due": a.due} for a in s.action_items],
                hide_index=True,
                width="stretch",
            )
        else:
            st.markdown("_None_")
        st.markdown("**Open questions**")
        st.markdown("\n".join(f"- {q}" for q in s.open_questions) or "_None_")

        st.download_button("Download summary (Markdown)", core.to_markdown(s), file_name="meeting-summary.md")

        st.divider()
        st.markdown("**Ask about this meeting**")
        q = st.text_input("Question", placeholder="What did we decide about the launch date?")
        if q:
            with st.spinner("Thinking…"):
                try:
                    st.write(core.ask(gemini_client(api_key), model, transcript, q))
                except Exception as e:
                    st.error(f"Could not answer: {e}")
