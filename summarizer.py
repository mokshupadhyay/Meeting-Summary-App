"""Core logic for Meeting Summary: transcription, transcript clean-up, and Gemini summaries.

Kept free of Streamlit so it can be tested and reused from the command line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from pydantic import BaseModel, Field

# Models tried in order when the user has not picked one. The first one the key can use wins;
# if none match, any available "flash" model is used.
PREFERRED_MODELS = [
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]


# ---------- Structured summary ----------


class ActionItem(BaseModel):
    task: str = Field(description="What needs to be done, as a short imperative sentence.")
    owner: str = Field(description="Who owns it, exactly as named in the meeting, or 'Unassigned'.")
    due: str = Field(description="Deadline as stated in the meeting, or 'Not set'.")


class MeetingSummary(BaseModel):
    title: str = Field(description="A short title for the meeting, at most 8 words.")
    tldr: str = Field(description="Two or three sentences on what the meeting was about and its outcome.")
    key_points: list[str] = Field(description="The main points discussed, one sentence each.")
    decisions: list[str] = Field(description="Decisions that were actually made. Empty if none.")
    action_items: list[ActionItem] = Field(description="Follow-up tasks agreed in the meeting. Empty if none.")
    open_questions: list[str] = Field(description="Questions raised but not resolved. Empty if none.")
    participants: list[str] = Field(description="Names of people who spoke or were mentioned as attending.")


SYSTEM_INSTRUCTION = (
    "You summarise meeting transcripts for the people who attended. "
    "Use only what is in the transcript: never invent owners, dates, numbers or decisions. "
    "If something is unclear, leave it out or put it under open questions. "
    "Write in plain, direct English."
)


def summary_prompt(transcript: str) -> str:
    return (
        "Summarise this meeting transcript. Fill every field of the schema; use empty lists when a "
        "section has nothing in it.\n\n--- TRANSCRIPT ---\n" + transcript
    )


def question_prompt(transcript: str, question: str) -> str:
    return (
        "Answer the question using only the meeting transcript below. If the transcript does not "
        "answer it, say so plainly. Quote the relevant line when it helps.\n\n"
        f"Question: {question}\n\n--- TRANSCRIPT ---\n{transcript}"
    )


# ---------- Transcript clean-up ----------

_TIMESTAMP_LINE = re.compile(r"^\d{2}:\d{2}(:\d{2})?[.,]\d{3}\s*-->\s*\d{2}:\d{2}(:\d{2})?[.,]\d{3}")


def clean_transcript(text: str) -> str:
    """Strip HTML, URLs and subtitle (SRT/VTT) markup, keeping the spoken words and speaker labels."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)

    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s == "WEBVTT" or s.isdigit() or _TIMESTAMP_LINE.match(s):
            continue
        lines.append(s)
    # Join and collapse whitespace while keeping one line per utterance.
    return "\n".join(re.sub(r"[ \t]+", " ", l) for l in lines).strip()


# ---------- Transcription ----------


@dataclass
class Segment:
    start: float
    end: float
    text: str


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def load_whisper(size: str = "base"):
    """Load a faster-whisper model on CPU. int8 keeps it small and fast on laptops."""
    from faster_whisper import WhisperModel

    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe(model, audio_path: str, language: Optional[str] = None) -> tuple[list[Segment], str]:
    """Return timestamped segments and the detected language code."""
    segments, info = model.transcribe(audio_path, language=language, vad_filter=True, beam_size=5)
    out = [Segment(s.start, s.end, s.text.strip()) for s in segments if s.text.strip()]
    return out, info.language


def segments_to_text(segments: Iterable[Segment], timestamps: bool = False) -> str:
    if timestamps:
        return "\n".join(f"[{format_time(s.start)}] {s.text}" for s in segments)
    return " ".join(s.text for s in segments)


# ---------- Gemini ----------


def make_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def available_models(client) -> list[str]:
    """Gemini models this key can call for text generation, without the 'models/' prefix."""
    names = []
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        name = (m.name or "").removeprefix("models/")
        if "generateContent" in actions and name.startswith("gemini"):
            names.append(name)
    return names


def pick_model(names: list[str]) -> Optional[str]:
    for preferred in PREFERRED_MODELS:
        if preferred in names:
            return preferred
    flash = sorted((n for n in names if "flash" in n and "image" not in n and "tts" not in n), reverse=True)
    if flash:
        return flash[0]
    return names[0] if names else None


def summarize(client, model: str, transcript: str) -> MeetingSummary:
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=summary_prompt(transcript),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=MeetingSummary,
            temperature=0.2,
        ),
    )
    if isinstance(response.parsed, MeetingSummary):
        return response.parsed
    return MeetingSummary.model_validate_json(response.text)


def ask(client, model: str, transcript: str, question: str) -> str:
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=question_prompt(transcript, question),
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.2),
    )
    return (response.text or "").strip()


# ---------- Export ----------


def to_markdown(summary: MeetingSummary) -> str:
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "_None_"

    lines = [f"# {summary.title}", "", summary.tldr, ""]
    if summary.participants:
        lines += [f"**Participants:** {', '.join(summary.participants)}", ""]
    lines += ["## Key points", bullets(summary.key_points), "", "## Decisions", bullets(summary.decisions), ""]
    lines += ["## Action items"]
    if summary.action_items:
        lines += ["| Task | Owner | Due |", "|---|---|---|"]
        lines += [f"| {a.task} | {a.owner} | {a.due} |" for a in summary.action_items]
    else:
        lines.append("_None_")
    lines += ["", "## Open questions", bullets(summary.open_questions), ""]
    return "\n".join(lines)
