"""Tests for LLMClassifier: parsing, caching, batch logic."""

import json

import pytest

from src.services.llm_classifier import LLMClassifier, TrackSuggestion


class TestParseResponse:
    def test_valid_json(self):
        raw = json.dumps([
            {
                "track_id": "t1",
                "suggested_theme": "ambiance",
                "confidence": 0.9,
                "reasoning": "Chill vibes",
            }
        ])
        result = LLMClassifier._parse_response(raw)
        assert len(result) == 1
        assert result[0].track_id == "t1"
        assert result[0].suggested_theme == "ambiance"
        assert result[0].confidence == 0.9

    def test_json_with_code_fences(self):
        raw = '```json\n[{"track_id":"t1","suggested_theme":"lets_dance","confidence":0.8,"reasoning":"Upbeat"}]\n```'
        result = LLMClassifier._parse_response(raw)
        assert len(result) == 1
        assert result[0].suggested_theme == "lets_dance"

    def test_invalid_json(self):
        result = LLMClassifier._parse_response("not valid json at all")
        assert result == []

    def test_empty_array(self):
        result = LLMClassifier._parse_response("[]")
        assert result == []

    def test_multiple_themes_same_track(self):
        raw = json.dumps([
            {"track_id": "t1", "suggested_theme": "ambiance", "confidence": 0.7, "reasoning": "Warm"},
            {"track_id": "t1", "suggested_theme": "lets_dance", "confidence": 0.6, "reasoning": "Groovy"},
        ])
        result = LLMClassifier._parse_response(raw)
        assert len(result) == 2
        assert result[0].track_id == result[1].track_id == "t1"

    def test_missing_fields_defaults(self):
        raw = json.dumps([{"track_id": "t1"}])
        result = LLMClassifier._parse_response(raw)
        assert len(result) == 1
        assert result[0].suggested_theme == ""
        assert result[0].confidence == 0.0
        assert result[0].reasoning == ""


class TestClassifyBatch:
    def test_empty_batch(self):
        classifier = LLMClassifier.__new__(LLMClassifier)
        classifier._cache = {}
        result = classifier.classify_batch([])
        assert result == []

    def test_all_cached(self):
        classifier = LLMClassifier.__new__(LLMClassifier)
        suggestion = TrackSuggestion("t1", "ambiance", 0.9, "Chill")
        classifier._cache = {"t1": [suggestion]}
        result = classifier.classify_batch([{"id": "t1", "name": "X", "artist": "Y", "album": "Z", "popularity": 50}])
        assert len(result) == 1
        assert result[0].track_id == "t1"
