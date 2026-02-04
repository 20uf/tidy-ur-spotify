"""Bounded context: Classification — AI response parsing

Business rules for interpreting LLM responses into actionable suggestions.
"""

import json

from src.adapters.classifier._prompt import parse_suggestions


class TestAiResponseParsing:
    """The system must reliably parse AI responses into suggestions."""

    def test_valid_response_is_parsed(self):
        raw = json.dumps([{
            "track_id": "t1",
            "suggested_theme": "ambiance",
            "confidence": 0.9,
            "reasoning": "Chill vibes",
        }])
        result = parse_suggestions(raw)

        assert len(result) == 1
        assert result[0].track_id == "t1"
        assert result[0].theme_key == "ambiance"
        assert result[0].confidence == 0.9

    def test_code_fences_are_stripped(self):
        raw = '```json\n[{"track_id":"t1","suggested_theme":"lets_dance","confidence":0.8,"reasoning":"Upbeat"}]\n```'
        result = parse_suggestions(raw)

        assert len(result) == 1
        assert result[0].theme_key == "lets_dance"

    def test_invalid_json_returns_empty_list(self):
        result = parse_suggestions("This is not JSON at all")
        assert result == []

    def test_empty_array_returns_empty_list(self):
        result = parse_suggestions("[]")
        assert result == []

    def test_track_can_match_multiple_themes(self):
        raw = json.dumps([
            {"track_id": "t1", "suggested_theme": "ambiance", "confidence": 0.7, "reasoning": "Warm"},
            {"track_id": "t1", "suggested_theme": "lets_dance", "confidence": 0.6, "reasoning": "Groovy"},
        ])
        result = parse_suggestions(raw)

        assert len(result) == 2
        assert result[0].track_id == result[1].track_id == "t1"
        themes = {s.theme_key for s in result}
        assert themes == {"ambiance", "lets_dance"}

    def test_missing_fields_get_safe_defaults(self):
        raw = json.dumps([{"track_id": "t1"}])
        result = parse_suggestions(raw)

        assert len(result) == 1
        assert result[0].theme_key == ""
        assert result[0].confidence == 0.0
        assert result[0].reasoning == ""
