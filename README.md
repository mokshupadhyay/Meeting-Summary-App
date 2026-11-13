# Meeting Summary

Upload a meeting recording or transcript and get a structured summary: the decisions, the action items (with owner and due date), the open questions and a one-paragraph TL;DR. Then ask follow-up questions about the meeting.

- **Local transcription.** Audio is transcribed on your machine with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), with timestamps and language detection. Recordings are never uploaded for transcription.
- **Structured output.** Gemini returns JSON that matches a fixed schema (`MeetingSummary` in `summarizer.py`), so the summary always has the same sections and can be exported.
- **Grounded.** The model is told to use only what is in the transcript and never invent owners, dates or decisions; anything unclear goes under open questions.
- **Any input.** MP3, WAV, M4A, OGG, WEBM and MP4 recordings; TXT, VTT and SRT transcripts (subtitle timing is stripped); or pasted text.
- **Export.** Download the transcript, and the summary as Markdown.

## Run it

Needs Python 3.10+. ffmpeg is not required: PyAV bundles it.

```bash
git clone https://github.com/mokshupadhyay/Meeting-Summary-App.git
cd Meeting-Summary-App
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...   # optional; you can also paste it in the sidebar
streamlit run app.py
```

Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey). The app lists the models your key can use and picks a Flash model by default.

The first transcription downloads the chosen Whisper model (`base` is about 140 MB). No audio handy? Use **Transcript file → Try the sample meeting**, or upload `harvard.wav`.

## How it works

| Step | Where |
|---|---|
| Transcribe audio to timestamped segments | `summarizer.transcribe` (faster-whisper, int8 on CPU) |
| Clean transcripts (HTML, URLs, SRT/VTT timing) | `summarizer.clean_transcript` |
| Summarise to a fixed JSON schema | `summarizer.summarize` (Gemini, `response_schema=MeetingSummary`) |
| Answer questions from the transcript only | `summarizer.ask` |
| Export to Markdown | `summarizer.to_markdown` |
| UI | `app.py` (Streamlit) |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests run without network access or an API key; Gemini is replaced with a fake client.
