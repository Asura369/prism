import { useMemo, useState } from "react";
import { Plus, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { ReviewMetadata } from "@/types";

interface Props {
  metadata: ReviewMetadata;
  slideCount: number;
  onSave: (patch: Partial<ReviewMetadata>) => Promise<ReviewMetadata>;
}

function normalizeTag(raw: string): string {
  return raw.trim().replace(/^#+/, "").replace(/\s+/g, "");
}

export function MetadataForm({ metadata, slideCount, onSave }: Props) {
  const [title, setTitle] = useState(metadata.title ?? "");
  const [caption, setCaption] = useState(metadata.caption ?? "");
  const [hashtags, setHashtags] = useState<string[]>(metadata.hashtags ?? []);
  const [platforms, setPlatforms] = useState<string[]>(metadata.platforms ?? ["instagram_feed"]);
  const [altText, setAltText] = useState<string[]>(
    Array.from({ length: slideCount }, (_, i) => metadata.alt_text?.[i] ?? ""),
  );
  const [draft, setDraft] = useState("");
  const [baseline, setBaseline] = useState(() =>
    JSON.stringify([metadata.title, metadata.caption, metadata.hashtags, metadata.platforms, metadata.alt_text]),
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current = JSON.stringify([title, caption, hashtags, platforms, altText]);
  const dirty = current !== baseline;

  const counterClass = caption.length > 2200 ? "text-red-600" : "text-ink-400";

  const patch = useMemo<Partial<ReviewMetadata>>(
    () => ({
      title: title.trim(),
      caption,
      hashtags,
      platforms,
      alt_text: altText,
    }),
    [title, caption, hashtags, platforms, altText],
  );

  function addHashtags(raw: string) {
    const next = raw
      .split(/[,\s]+/)
      .map(normalizeTag)
      .filter(Boolean);
    if (next.length === 0) return;
    setHashtags((existing) => Array.from(new Set([...existing, ...next])).slice(0, 30));
    setDraft("");
    setSaved(false);
  }

  function togglePlatform(platform: string) {
    setPlatforms((existing) =>
      existing.includes(platform) ? existing.filter((p) => p !== platform) : [...existing, platform],
    );
    setSaved(false);
  }

  function setAlt(index: number, value: string) {
    setAltText((existing) => existing.map((text, i) => (i === index ? value : text)));
    setSaved(false);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await onSave(patch);
      setBaseline(JSON.stringify([updated.title, updated.caption, updated.hashtags, updated.platforms, updated.alt_text]));
      setSaved(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <div>
        <label htmlFor="meta-title" className="eyebrow">
          Title
        </label>
        <Input
          id="meta-title"
          className="mt-2"
          value={title}
          maxLength={120}
          onChange={(event) => {
            setTitle(event.target.value);
            setSaved(false);
          }}
        />
      </div>

      <div>
        <div className="flex items-center justify-between">
          <label htmlFor="meta-caption" className="eyebrow">
            Caption
          </label>
          <span className={`text-[11px] ${counterClass}`}>{caption.length} / 2200</span>
        </div>
        <Textarea
          id="meta-caption"
          className="mt-2 min-h-[150px]"
          value={caption}
          maxLength={2200}
          onChange={(event) => {
            setCaption(event.target.value);
            setSaved(false);
          }}
        />
      </div>

      <div>
        <div className="flex items-center justify-between">
          <span className="eyebrow">Hashtags</span>
          <span className="text-[11px] text-ink-400">{hashtags.length} / 30</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {hashtags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-ink-900/5 px-2.5 py-1 text-xs text-ink-700"
            >
              #{tag}
              <button
                type="button"
                aria-label={`Remove #${tag}`}
                onClick={() => {
                  setHashtags((existing) => existing.filter((item) => item !== tag));
                  setSaved(false);
                }}
                className="text-ink-400 hover:text-ink-900"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <Input
            aria-label="Add hashtag"
            value={draft}
            placeholder="Add a hashtag and press Enter"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === ",") {
                event.preventDefault();
                addHashtags(draft);
              }
            }}
          />
          <Button type="button" variant="outline" size="icon" aria-label="Add hashtag button" onClick={() => addHashtags(draft)}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div>
        <span className="eyebrow">Platforms</span>
        <div className="mt-2 flex flex-col gap-2 text-sm text-ink-700">
          {[
            ["instagram_feed", "Instagram feed"],
            ["instagram_story", "Instagram story"],
          ].map(([value, label]) => (
            <label key={value} className="flex items-center gap-2.5">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[#D97757]"
                checked={platforms.includes(value)}
                onChange={() => togglePlatform(value)}
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2.5 text-sm text-ink-500">
        <input type="checkbox" checked disabled className="h-4 w-4 accent-[#D97757]" />
        AI disclosure (required, locked on)
      </label>

      <details className="rounded-xl border border-ink-900/10 bg-white/40 p-3">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-ink-500">
          Alt text per slide ({altText.length})
        </summary>
        <div className="mt-3 flex flex-col gap-3">
          {altText.map((text, index) => (
            <label key={index} className="flex flex-col gap-1 text-[11px] font-semibold text-ink-400">
              Slide {index + 1}
              <Textarea
                value={text}
                className="min-h-[64px] text-sm"
                onChange={(event) => setAlt(index, event.target.value)}
                aria-label={`Alt text for slide ${index + 1}`}
              />
            </label>
          ))}
        </div>
      </details>

      {error && <p className="text-sm text-red-700">{error}</p>}

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={!dirty || saving || altText.some((text) => !text.trim())}>
          <Save className="h-4 w-4" />
          {saving ? "Saving…" : "Save changes"}
        </Button>
        {saved && !dirty && <span className="text-xs font-medium text-emerald-700">Saved</span>}
        {!dirty && !saved && <span className="text-xs text-ink-400">No unsaved changes</span>}
      </div>
    </form>
  );
}
