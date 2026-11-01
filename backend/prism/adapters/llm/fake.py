from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from ..base import LLMAdapter

FACTS_SETS = [
    {
        "title": "Octopuses Have Three Hearts",
        "cover_headline": "Three Hearts. Blue Blood. No Bones.",
        "facts": [
            {
                "heading": "Three hearts, one job each",
                "body": "Two hearts pump blood to the gills, while the third feeds the rest of the body. When an octopus swims, that third heart stops beating.",
            },
            {
                "heading": "Their blood is blue",
                "body": "Octopus blood uses hemocyanin, a copper-based protein, instead of iron-based hemoglobin. That makes it blue and efficient in cold water.",
            },
            {
                "heading": "They taste with their arms",
                "body": "Each arm carries hundreds of suckers packed with chemoreceptors, so an octopus can taste whatever it touches.",
            },
            {
                "heading": "They squeeze through tiny gaps",
                "body": "An octopus has no bones, so it can fold its body through any opening wider than its beak — often the only hard part.",
            },
            {
                "heading": "They change color in milliseconds",
                "body": "Specialized skin cells called chromatophores expand and contract under muscular control, letting an octopus match its surroundings.",
            },
        ],
        "cta": "Follow for one surprising fact every day.",
    },
    {
        "title": "The Fish That Climbs Trees",
        "cover_headline": "This Fish Climbs Trees",
        "facts": [
            {
                "heading": "It leaves the water on purpose",
                "body": "The climbing perch uses its gills and a labyrinth organ to breathe air, letting it survive hours on land.",
            },
            {
                "heading": "It walks with its fins",
                "body": "Stiff pectoral fins and a muscular body let it shuffle across mud and roots in search of water.",
            },
            {
                "heading": "It hides in unexpected places",
                "body": "During dry spells it burrows into mud and waits, sometimes for months, until the rains return.",
            },
            {
                "heading": "It can survive bad water",
                "body": "The climbing perch tolerates low-oxygen water that would kill most fish, which helps it move between shrinking pools.",
            },
            {
                "heading": "It is a patient ambush hunter",
                "body": "Rather than chase prey, it waits near cover and strikes when something small comes close enough.",
            },
        ],
        "cta": "Save this for your next trivia night.",
    },
    {
        "title": "Why Iceland Runs on Steam",
        "cover_headline": "A Country Powered by the Ground",
        "facts": [
            {
                "heading": "Heat comes from the crust",
                "body": "Iceland sits on a rift between tectonic plates, so hot rock lies unusually close to the surface.",
            },
            {
                "heading": "Hot water heats homes",
                "body": "Geothermal water is piped directly into district heating systems that warm most Icelandic homes.",
            },
            {
                "heading": "Steam drives turbines",
                "body": "High-pressure steam spins turbines that generate a large share of the country's electricity.",
            },
            {
                "heading": "The heat is renewable",
                "body": "Geothermal energy comes from the Earth's interior, so it keeps flowing without the fuel a coal plant needs.",
            },
            {
                "heading": "Greenhouses get the surplus",
                "body": "Warm water and cheap heat support greenhouses that grow tomatoes and cucumbers through the Icelandic winter.",
            },
        ],
        "cta": "Follow for more stories about how the world works.",
    },
]

FAQ_SETS = [
    {
        "title": "Why the Sky Changes Color",
        "cover_headline": "Why Is the Sky Blue?",
        "questions": [
            {"question": "Why is the sky blue during the day?", "answer": "Short wavelengths of sunlight scatter far more in the atmosphere than long ones. Blue scatters most, so it fills the sky."},
            {"question": "Why does it turn red at sunset?", "answer": "At sunset light travels through more atmosphere. Much of the blue is scattered away, leaving warm reds and oranges."},
            {"question": "What about other planets?", "answer": "Mars has a butterscotch sky because suspended dust scatters light differently than nitrogen and oxygen."},
        ],
        "cta": "Follow for one clear answer every day.",
    },
    {
        "title": "How Sleep Resets the Brain",
        "cover_headline": "What Does Sleep Actually Do?",
        "questions": [
            {"question": "Why do we need sleep?", "answer": "Sleep clears metabolic waste, consolidates memory, and restores the systems that regulate mood and attention."},
            {"question": "What is deep sleep for?", "answer": "Deep sleep is when the body repairs tissue and the brain replays patterns from the day, strengthening memory."},
            {"question": "What is REM sleep for?", "answer": "REM sleep supports emotional processing and creative association, which is why dreams feel so vivid."},
        ],
        "cta": "Save this the next time you feel tired.",
    },
]

NEWS_SETS = [
    {
        "title": "Deep-sea Mining Talks Resume",
        "cover_headline": "The Ocean Floor Is Back on the Agenda",
        "news_points": [
            {"heading": "Talks restart this week", "body": "Delegates are meeting again to discuss rules for extracting metals from the deep seabed.", "source_index": 0},
            {"heading": "The stakes are high", "body": "The nodules hold nickel and cobalt used in batteries, but ecosystems around them recover slowly.", "source_index": 1},
            {"heading": "No final rules yet", "body": "A moratorium proposal is on the table, and several states say the science is not settled.", "source_index": 2},
            {"heading": "Today's takeaway", "body": "The decision will shape where battery metals come from for the next decade.", "source_index": 0},
            {"heading": "What happens next", "body": "Negotiators aim to publish a draft framework before the next session.", "source_index": 1},
        ],
        "cta": "Follow for calmer recaps of complicated stories.",
    }
]

ANGLES = [
    {
        "hook": "Your body has a second brain",
        "framing": "Three fast facts that reframe how the gut works",
        "target_emotion": "surprise",
        "format_suggestion": "facts",
        "est_slide_count": 7,
        "why_it_works": "It promises a concrete reframe people can repeat at dinner.",
        "recommended_plugin": "facts_carousel",
        "plugin_reasoning": "The topic is evergreen and best told as a short fact list.",
    },
    {
        "hook": "What does 'gut feeling' actually mean?",
        "framing": "Five questions answered in plain language",
        "target_emotion": "curiosity",
        "format_suggestion": "qa",
        "est_slide_count": 7,
        "why_it_works": "The question format matches how people already search for this idea.",
        "recommended_plugin": "faq_carousel",
        "plugin_reasoning": "A Q&A deck keeps each explanation short and scannable.",
    },
    {
        "hook": "This week: the gut-brain story, without the hype",
        "framing": "A sourced recap of the newest research",
        "target_emotion": "concern",
        "format_suggestion": "recap",
        "est_slide_count": 8,
        "why_it_works": "Timely coverage gives viewers a reason to save and share now.",
        "recommended_plugin": "news_carousel",
        "plugin_reasoning": "New evidence is best presented with attribution and a sources slide.",
    },
]


def _digest(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def _extract_headings(prompt: str) -> list[str]:
    headings = re.findall(r"^\d+\.\s+(.+)$", prompt, flags=re.MULTILINE)
    return [h.strip() for h in headings]


def _metadata(prompt: str) -> dict[str, Any]:
    headings = _extract_headings(prompt)
    count = max(1, len(headings))
    caption = (
        "A short deck on something worth knowing. "
        + " ".join(f"{i + 1}. {h}." for i, h in enumerate(headings[:3]))
        + " Follow for more."
    )
    return {
        "caption": caption[:2200],
        "hashtags": [
            "learnsomethingnew", "didyouknow", "facts", "education", "explainer",
            "knowledge", "curiosity", "dailyfacts", "carousel", "instalearn",
        ],
        "alt_text": [
            f"Slide {i + 1}: {headings[i] if i < len(headings) else 'carousel slide'}."
            for i in range(count)
        ],
    }


def _fill_schema(schema: dict[str, Any], key: str = "") -> Any:
    if "enum" in schema:
        return schema["enum"][0]
    stype = schema.get("type")
    if stype == "object":
        props = schema.get("properties", {})
        return {name: _fill_schema(prop, name) for name, prop in props.items()}
    if stype == "array":
        count = max(1, min(int(schema.get("minItems", 1)), 3))
        return [_fill_schema(schema.get("items", {"type": "string"}), key)] * count
    if stype == "integer":
        return int(schema.get("minimum", 7))
    if stype == "number":
        return 0.5
    if stype == "boolean":
        return True
    key = key.lower()
    if "headline" in key or key in {"title", "hook"}:
        return "A Small Fact Worth Sharing"
    if "why" in key:
        return "It gives viewers a concrete idea they can repeat."
    if "reasoning" in key:
        return "Generated by the deterministic fake adapter."
    if "caption" in key:
        return "A short, useful deck built for review."
    if "alt" in key:
        return "A minimal typographic carousel slide."
    if "plugin" in key:
        return "facts_carousel"
    return "A short, useful paragraph for this slide. It stays inside the character limit."


class FakeLLM(LLMAdapter):
    name = "fake"

    def is_available(self) -> bool:
        return True

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        digest = _digest((system or "") + prompt)
        lowered = prompt.lower()

        if "generate exactly 3 angles" in lowered:
            return json.dumps({"angles": ANGLES})

        if "alt_text" in lowered and "hashtags" in lowered:
            return json.dumps(_metadata(prompt))

        if "cover_headline" in lowered:
            if '"facts"' in lowered:
                return json.dumps(FACTS_SETS[digest % len(FACTS_SETS)])
            if '"questions"' in lowered:
                return json.dumps(FAQ_SETS[digest % len(FAQ_SETS)])
            if '"news_points"' in lowered:
                return json.dumps(NEWS_SETS[digest % len(NEWS_SETS)])

        if "score 0.0" in lowered or "scoring topic candidates" in lowered:
            ids = re.findall(r"candidate_id=([\w:.-]+)", prompt)
            return json.dumps(
                {
                    "scores": [
                        {
                            "id": cid,
                            "safety": 0.85,
                            "visual_potential": 0.75,
                            "angle_ability": 0.8,
                            "saturation": round(0.2 + (digest % 30) / 100, 2),
                            "reasoning": "Clear, safe, and easy to distill into a short deck.",
                        }
                        for cid in ids
                    ]
                }
            )

        if json_schema:
            return json.dumps(_fill_schema(json_schema))
        return json.dumps({"text": "Deterministic fake response."})
