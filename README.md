# Prism

*A human-in-the-loop content automation framework.*

Prism turns one trending topic into Instagram-ready carousel decks, then puts
every deck in a human review queue before anything leaves the machine.

## Prerequisites

- Python 3.11+
- Node 20+

No Docker, no ffmpeg, no audio/video tooling.

## Quick start

```bash
cp .env.example .env     # set LLM_KEY, or leave empty for the FakeLLM demo
make setup
make dev                 # http://localhost:5173
```

API docs: http://localhost:8000/docs

## What it is

Prism discovers topics from pluggable sources, generates angle options, and
runs one of three carousel plugins through a shared pipeline: spec → render →
export → metadata → policy → validate → publish. Each artifact carries an
immutable provenance manifest and lands in a review queue where you edit
metadata and approve or reject it.

## Architecture

React + Vite → FastAPI (:8000) → SQLite (WAL) ← worker process → plugin pipeline
→ Pillow renderer → zip. Three local processes, no containers.

## Plugins

| Plugin | Slide structure | Output |
|---|---|---|
| `facts_carousel` | cover + facts + CTA | 1080×1350 PNG sequence + zip |
| `news_carousel` | cover + news points + sources + CTA | 1080×1350 PNG sequence + zip |
| `faq_carousel` | cover + Q&A + CTA | 1080×1350 PNG sequence + zip |

## Adapters

| Interface | Default | Fallbacks |
|---|---|---|
| LLM | `openai_compat` (any OpenAI-compatible provider) | `fake` |
| Card renderer | `templated` (Pillow + Inter) | — |
| Export | `zip` | — |
| Trend sources | Google News RSS, Hacker News, Reddit, Trends CSV, manual | soft-fail per source |
| News sources | `google_news_rss` | `manual` |

The LLM adapter takes any OpenAI-compatible `base_url` + `model`; `LLM_KEY` is the
provider key. Provider-specific request fields can go in `extra_body`.

## Tuning

Scoring weights and the safety threshold in `config.yaml` are defaults, not
facts. Tune them after roughly 20 real runs; the doc marks every knob with
`⚠️ TUNE`.

## Testing

```bash
make test
```

CI uses `FAKE_ADAPTERS=1` and requires no API keys.

## Scope and non-goals

In: discovery, angles, three carousel plugins, review queue, provenance.
Out: auth, cloud deploy, Docker, auto-publishing, video, audio, rich media.
