from app.core.ollama_coordination import _holder_label, holder_is_self


def test_holder_label():
    assert _holder_label("learnai:unit:abc") == "LearnAI"
    assert _holder_label("slitprojekthub:idea:12") == "SlitProjektHub"


def test_holder_is_self(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ollama_lock_app_name", "learnai")
    assert holder_is_self("learnai:unit:x")
    assert not holder_is_self("slitprojekthub:idea:1")
