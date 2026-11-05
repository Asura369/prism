# Prism

*A human-in-the-loop content automation framework.*

Prism turns one trending topic into Instagram-ready carousel decks, then puts
every deck in a human review queue before anything leaves the machine.

## Prerequisites

- Python 3.11+
- Node 20.19+ or 22.12+ (Vite 8)

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
runs one of three carousel plugins through a shared pipeline: spec → ingest (news) →
render → export → metadata → policy → validate → publish. Each artifact carries an
immutable provenance manifest and lands in a review queue where you edit
metadata and approve or reject it.

## What it looks like

<p align="center">
  <img src="docs/screenshots/cover.png" width="30%" alt="Cover slide: the ocean floor is back on the agenda" />
  <img src="docs/screenshots/content.png" width="30%" alt="News point slide with heading and body" />
  <img src="docs/screenshots/sources.png" width="30%" alt="Sources slide listing attribution for every claim" />
</p>

One generated `news_carousel` deck (1080×1350 each), from `make demo`: a cover,
a sourced news point, and the attribution slide. Regenerate them any time with
`make demo` and look in `review/<job_id>/slides/`.

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
| Trend sources | Google News RSS, Hacker News, Trends CSV, manual | soft-fail per source |
| News sources | `google_news_rss` | `fake` when `FAKE_ADAPTERS=1` |

The LLM adapter takes any OpenAI-compatible `base_url` + `model`; `LLM_KEY` is the
provider key. Provider-specific request fields can go in `extra_body`.

## Tuning

Scoring weights and the safety threshold in `config.yaml` are defaults, not
facts. Tune them after roughly 20 real runs; the doc marks every knob with
`⚠️ TUNE`.

## Failure paths

Failures surface as typed errors in `manifest.error` and on the job page; no
job fails silently.

| Symptom | Error / response | What you see, what to do |
|---|---|---|
| `LLM_KEY` missing, or the provider is down | `fake` LLM takes over and the job is marked `degraded` (no error); `AdapterUnavailable` only if the whole chain is empty | Amber "degraded" badge on Review; set `LLM_KEY` for real output. |
| Candidate fails the safety filter | `unsafe_candidate` (HTTP 400) on manual entry; auto-discovered candidates are dropped | Nothing is queued; rephrase the topic or title. |
| Spec breaks the plugin schema | one re-prompt, then `SpecValidationError` | Job FAILED at `spec`; retry the job. |
| News run finds fewer articles than `min_sources` | `InsufficientSourcesError(found, required)` | Job FAILED at `ingest`; a failing adapter is recorded in `manifest.ingest_errors` — widen the topic or adjust `min_sources`. |
| Topic matches `block_topics` | `PolicyViolation` | Job FAILED at `policy`; remove the blocked phrase. |
| Card renderer exhausts retries on a slide | `SlideRenderError` | Job FAILED at `render`; the failing slide index is in the error context. |
| Text does not fit a slide's safe area | `SlideOverflowError` | Job FAILED at `render`; shorten the offending field. |
| Artifact fails checks (size, alt text, caption) | `ValidationError` with reasons | Job FAILED at `validate`; each reason is listed in the manifest. |
| Deck breaks the plugin's slide-count or slide-kind rules | `PolicyViolation` | Job FAILED at `policy`; the plugin manifest defines `min_slides`/`max_slides`. |
| Worker dies mid-job | job FAILED with `WorkerLost` once the heartbeat is stale (~15 s) | Restart `make worker`, then re-run the job; runs are not resumed. |
| Trends CSV upload over 5 MB | HTTP 413 `file_too_large` | Trim the CSV and upload again. |

Metadata generation is the one soft failure: if the LLM call fails, captions and
alt text fall back to derived values and the job still succeeds. `ConfigError`
flags a broken setup (invalid `config.yaml`, missing style or font). Every error
serializes to `{error_class, stage, message, retryable, context}`.

## Demo

`make demo` runs all three plugins with the deterministic fakes — no key, no
network — and writes one artifact per plugin to `review/<job_id>/`. The decks
then sit in the review queue.

## Testing

```bash
make test
```

CI uses `FAKE_ADAPTERS=1` and requires no API keys.

## Scope and non-goals

In: discovery, angles, three carousel plugins, review queue, provenance.
Out: auth, cloud deploy, Docker, auto-publishing, video, audio, rich media.

## Fonts and licensing

Every font in this repository is **Inter v4.001**, copyright 2016 The Inter
Project Authors, licensed under the **SIL Open Font License 1.1**. The license
text ships beside the files and is also embedded in each font's own name table
(ID 13), so it travels with the binary.

| File | Used by | Purpose |
|---|---|---|
| `assets/fonts/Inter-Regular.ttf`, `Inter-Bold.ttf` | Pillow renderer | the decks themselves |
| `frontend/public/fonts/InterVariable.woff2` | the web console | variable weight 100–900 |

Commercial use is covered. OFL 1.1 permits commercial use, embedding, and
bundling, and states that *"the requirement for fonts to remain under this
license does not apply to any document created using the fonts"* — so decks
rendered with Inter and posted commercially carry no font obligation. The
restriction is on selling the font software itself, which this project does not
do. Deck text is rasterized into PNGs; no font data is embedded in the output.

Verified for this tree (v4.001, `git-9221beed3`):

```
288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f  Inter-Bold.ttf
40d692fce188e4471e2b3cba937be967878f631ad3ebbbdcd587687c7ebe0c82  Inter-Regular.ttf
693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3  InterVariable.woff2
```

If a font is ever added, it must be OFL-1.1, CC0, or Apache-2.0 licensed, with
its license file committed beside it and its hash recorded here. The renderer
fails with `ConfigError` on a missing font rather than falling back to Pillow's
unlicensed bitmap default; keep it that way.

## License

MIT — see [LICENSE](LICENSE).
