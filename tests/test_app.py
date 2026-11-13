"""Drive the Streamlit UI end to end with Gemini replaced by a fake."""

from streamlit.testing.v1 import AppTest

import summarizer as core
from tests.test_summarizer import SAMPLE_JSON


def test_sample_meeting_summary_renders(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(core, "make_client", lambda key: object())
    monkeypatch.setattr(core, "available_models", lambda client: ["gemini-2.5-pro", "gemini-2.5-flash"])
    monkeypatch.setattr(core, "summarize", lambda c, m, t: core.MeetingSummary.model_validate(SAMPLE_JSON))
    monkeypatch.setattr(core, "ask", lambda c, m, t, q: f"Answer to: {q}")

    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert not at.exception
    assert at.sidebar.selectbox[0].value == "gemini-2.5-flash"

    next(b for b in at.button if b.label == "Try the sample meeting").click().run()
    next(b for b in at.button if b.label == "Summarise meeting").click().run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Checkout fix and mobile release" in text
    assert "Refund all 14 affected customers automatically." in text
    assert [m.value for m in at.metric] == ["2", "1", "1"]

    next(t for t in at.text_input if t.label == "Question").input("When is the release?").run()
    assert "Answer to: When is the release?" in " ".join(m.value for m in at.markdown)
