from __future__ import annotations

import json

import pytest

from prism.errors import SpecValidationError


def _payload(facts_payload: dict) -> dict:
    return json.loads(json.dumps(facts_payload))


def test_parse_spec_builds_cover_facts_cta(facts_plugin, facts_payload):
    spec = facts_plugin.parse_spec(json.dumps(facts_payload))
    assert [s.kind for s in spec.slides] == ["cover", "fact", "fact", "fact", "fact", "fact", "cta"]
    assert spec.slides[0].heading == facts_payload["cover_headline"]
    assert spec.output_kind.value == "image_sequence"


def test_body_over_260_fails_at_parse(facts_plugin, facts_payload):
    payload = _payload(facts_payload)
    payload["facts"][0]["body"] = "x" * 261
    with pytest.raises(SpecValidationError):
        facts_plugin.parse_spec(json.dumps(payload))


def test_body_at_260_passes_parse(facts_plugin, facts_payload):
    payload = _payload(facts_payload)
    payload["facts"][0]["body"] = ("A useful sentence. " * 20)[:260]
    spec = facts_plugin.parse_spec(json.dumps(payload))
    assert len(spec.slides[1].body) == 260


def test_cover_headline_over_60_fails(facts_plugin, facts_payload):
    payload = _payload(facts_payload)
    payload["cover_headline"] = "x" * 61
    with pytest.raises(SpecValidationError):
        facts_plugin.parse_spec(json.dumps(payload))


def test_content_heading_over_50_fails(facts_plugin, facts_payload):
    payload = _payload(facts_payload)
    payload["facts"][0]["heading"] = "x" * 51
    with pytest.raises(SpecValidationError):
        facts_plugin.parse_spec(json.dumps(payload))


def test_malformed_json_fails(facts_plugin):
    with pytest.raises(SpecValidationError):
        facts_plugin.parse_spec("not json at all")


def test_fenced_json_is_accepted(facts_plugin, facts_payload):
    spec = facts_plugin.parse_spec("```json\n" + json.dumps(facts_payload) + "\n```")
    assert len(spec.slides) == 7
