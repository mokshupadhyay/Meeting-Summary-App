import json
from types import SimpleNamespace

import summarizer as core


def test_clean_transcript_strips_markup_and_subtitles():
    raw = (
        "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.500\n<v Priya>Hello team</v>\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\nSee https://example.com for details\n<script>alert(1)</script>"
    )
    assert core.clean_transcript(raw) == "Hello team\nSee for details"


def test_clean_transcript_keeps_speaker_labels():
    assert core.clean_transcript("Priya:   Let's  start.\r\nArjun: Ok") == "Priya: Let's start.\nArjun: Ok"


def test_format_time_and_segments():
    segs = [core.Segment(0, 2, "Hi."), core.Segment(65.4, 70, "Next item."), core.Segment(3725, 3730, "Bye.")]
    assert core.format_time(65.4) == "1:05"
    assert core.format_time(3725) == "1:02:05"
    assert core.segments_to_text(segs) == "Hi. Next item. Bye."
    assert core.segments_to_text(segs, timestamps=True).splitlines()[1] == "[1:05] Next item."


def test_pick_model_prefers_newest_plain_flash():
    names = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-flash-lite", "gemini-3.8-flash",
             "gemini-3.7-flash", "gemini-3.1-flash-image", "gemini-omni-flash-preview", "gemini-4-argon"]
    assert core.pick_model(names) == "gemini-3.8-flash"
    assert core.model_candidates(names)[:3] == ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-2.5-flash"]
    assert core.model_candidates(names, "gemini-2.5-pro")[:2] == ["gemini-2.5-pro", "gemini-3.8-flash"]
    assert core.pick_model(["gemini-9-pro"]) == "gemini-9-pro"
    assert core.pick_model([]) is None


def test_moves_to_next_model_only_when_retired_or_overloaded():
    assert core.should_try_next_model(Exception("404 NOT_FOUND. This model is no longer available"))
    assert core.should_try_next_model(Exception("503 UNAVAILABLE. This model is currently experiencing high demand."))
    assert not core.should_try_next_model(Exception("429 RESOURCE_EXHAUSTED"))
    assert not core.should_try_next_model(Exception("400 API key not valid"))


def test_available_models_filters_to_text_generation():
    models = [
        SimpleNamespace(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/text-embedding-004", supported_actions=["embedContent"]),
        SimpleNamespace(name="models/imagen-4", supported_actions=["predict"]),
    ]
    client = SimpleNamespace(models=SimpleNamespace(list=lambda: models))
    assert core.available_models(client) == ["gemini-2.5-flash"]


SAMPLE_JSON = {
    "title": "Checkout fix and mobile release",
    "tldr": "The double-charge fix ships Thursday and the mobile release moves to 27 November.",
    "key_points": ["Duplicate webhooks caused double charges."],
    "decisions": ["Refund all 14 affected customers automatically.", "Move the release to 27 November."],
    "action_items": [{"task": "Ship the checkout fix", "owner": "Arjun", "due": "Thursday"}],
    "open_questions": ["Is the backend role remote-only or hybrid?"],
    "participants": ["Priya", "Arjun", "Neha", "Rahul"],
}


class FakeModels:
    def __init__(self, parsed=None, text=""):
        self.calls = []
        self._parsed, self._text = parsed, text

    def generate_content(self, model, contents, config):
        self.calls.append((model, contents, config))
        return SimpleNamespace(parsed=self._parsed, text=self._text)


def test_summarize_requests_structured_json_and_parses_text_fallback():
    fake = FakeModels(parsed=None, text=json.dumps(SAMPLE_JSON))
    s = core.summarize(SimpleNamespace(models=fake), "gemini-2.5-flash", "Priya: hi")
    assert s.action_items[0].owner == "Arjun"
    model, contents, config = fake.calls[0]
    assert model == "gemini-2.5-flash"
    assert contents.endswith("Priya: hi")
    assert config.response_mime_type == "application/json"
    assert config.response_schema is core.MeetingSummary


def test_to_markdown_has_every_section():
    md = core.to_markdown(core.MeetingSummary.model_validate(SAMPLE_JSON))
    assert md.startswith("# Checkout fix and mobile release")
    assert "| Ship the checkout fix | Arjun | Thursday |" in md
    for heading in ["## Key points", "## Decisions", "## Action items", "## Open questions"]:
        assert heading in md


def test_sample_transcript_cleans_to_speaker_lines():
    from pathlib import Path

    text = core.clean_transcript((Path(__file__).parent.parent / "samples" / "product_sync.txt").read_text())
    assert text.splitlines()[0].startswith("Priya:")
    assert len(text.splitlines()) == 19
