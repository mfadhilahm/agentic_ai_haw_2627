from src.app.settings import Settings
from src.llm.factory import get_chat_model


def test_ollama_json_mode_preserves_budgets():
    settings = Settings(
        _env_file=None, llm_provider="ollama",
        llm_timeout_seconds=180, llm_max_output_tokens=384,
    )
    model = get_chat_model(settings, json_mode=True)
    assert model.reasoning is False
    assert model.format == "json"
    assert model.num_predict == 384
    assert model.client_kwargs["timeout"] == 180
    assert get_chat_model(settings).format is None


def test_json_mode_preserves_explicit_reasoning_choice():
    settings = Settings(_env_file=None, llm_provider="ollama")
    assert get_chat_model(settings, json_mode=True, reasoning=True).reasoning is True
    assert get_chat_model(settings).reasoning is None


def test_openai_json_mode_is_opt_in():
    settings = Settings(_env_file=None, llm_provider="openai_compatible")
    model = get_chat_model(settings, json_mode=True)
    assert model.kwargs["response_format"] == {"type": "json_object"}
    assert "response_format" not in get_chat_model(settings).model_kwargs
