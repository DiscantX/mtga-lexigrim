import os
import pytest
from config.settings import Settings

def test_default_collection_settings():
    settings = Settings()
    assert settings.qdrant_collection_cards == "mtg_cards"
    assert settings.qdrant_collection_rules == "mtg_rules"
    assert settings.qdrant_collection_rulings == "mtg_rulings"
    assert settings.qdrant_collection_decks == "mtg_decks"
    assert settings.qdrant_collection_strategy == "mtg_strategy"
    assert settings.qdrant_collection_name == "mtg_cards"

def test_environment_variable_overrides(monkeypatch):
    monkeypatch.setenv("QDRANT_COLLECTION_CARDS", "custom_cards")
    monkeypatch.setenv("QDRANT_COLLECTION_RULES", "custom_rules")
    monkeypatch.setenv("QDRANT_COLLECTION_RULINGS", "custom_rulings")
    monkeypatch.setenv("QDRANT_COLLECTION_DECKS", "custom_decks")
    monkeypatch.setenv("QDRANT_COLLECTION_STRATEGY", "custom_strategy")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "custom_name")

    settings = Settings()
    assert settings.qdrant_collection_cards == "custom_cards"
    assert settings.qdrant_collection_rules == "custom_rules"
    assert settings.qdrant_collection_rulings == "custom_rulings"
    assert settings.qdrant_collection_decks == "custom_decks"
    assert settings.qdrant_collection_strategy == "custom_strategy"
    assert settings.qdrant_collection_name == "custom_name"

def test_backward_compatibility_fallback(monkeypatch):
    monkeypatch.delenv("QDRANT_COLLECTION_NAME", raising=False)
    monkeypatch.setenv("QDRANT_COLLECTION_CARDS", "fallback_cards")
    settings = Settings()
    assert settings.qdrant_collection_name == "fallback_cards"
