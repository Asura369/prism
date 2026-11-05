import { useEffect, useMemo, useState } from "react";
import { ChevronRight, Plus, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { ReviewMetadata } from "@/types";

interface Props {
  metadata: ReviewMetadata;
  slideCount: number;
  onSave: (patch: Partial<ReviewMetadata>) => Promise<ReviewMetadata>;
  onDirtyChange?: (dirty: boolean) => void;
}

function normalizeTag(raw: string): string {
  return raw.trim().replace(/^#+/, "").replace(/\s+/g, "");
}

export function MetadataForm({ metadata, slideCount, onSave, onDirtyChange }: Props) {
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

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const counterClass = caption.length > 2200 ? "text-signal" : "text-ink-400";

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
        <label htmlFor="meta-title" className="label">
          Title
        </label>
        <Input
          id="meta-title"
          className="mt-1.5"
          value={title}
          maxLength={120}
          onChange={(event) => {
            setTitle(event.target.value);
            setSaved(false);
          }}
        />
      </div>

      <div>
        <div className="flex items-baseline justify-between gap-3">
          <label htmlFor="meta-caption" className="label">
            Caption
          </label>
          <span className={`tnum text-[10.5px] ${counterClass}`}>{caption.length} / 2200</span>
        </div>
        <Textarea
          id="meta-caption"
          className="mt-1.5 min-h-[152px]"
          value={caption}
          maxLength={2200}
          onChange={(event) => {
            setCaption(event.target.value);
            setSaved(false);
          }}
        />
      </div>

      <div>
        <div className="flex items-baseline justify-between gap-3">
          <span className="label">Hashtags</span>
          <span className="tnum text-[10.5px] text-ink-400">{hashtags.length} / 30</span>
        </div>
        {hashtags.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {hashtags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-[2px] border border-ink-900/12 bg-paper-100 px-1.5 py-0.5 text-[11.5px] text-ink-700"
              >
                #{tag}
                <button
                  type="button"
                  aria-label={`Remove #${tag}`}
                  onClick={() => {
                    setHashtags((existing) => existing.filter((item) => item !== tag));
                    setSaved(false);
                  }}
                  className="text-ink-400 transition-colors hover:text-ink-900"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </span>
            ))}
          </div>
        ) : null}
        <div className="mt-2 flex gap-1.5">
          <Input
            aria-label="Add hashtag"
            className="h-8 text-[12.5px]"
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
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Add hashtag button"
            onClick={() => addHashtags(draft)}
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <fieldset>
        <legend className="label">Platforms</legend>
        <div className="mt-2 flex flex-col gap-1.5 text-[12.5px] text-ink-700">
          {[
            ["instagram_feed", "Instagram feed"],
            ["instagram_story", "Instagram story"],
          ].map(([value, label]) => (
            <label key={value} className="flex items-center gap-2">
              <input
                type="checkbox"
                className="h-3.5 w-3.5 rounded-[2px] border-ink-900/30"
                checked={platforms.includes(value)}
                onChange={() => togglePlatform(value)}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex items-center gap-2 border border-ink-900/10 bg-paper-100/70 px-2.5 py-2 text-[12px] text-ink-500">
        <input type="checkbox" checked disabled className="h-3.5 w-3.5" />
        AI disclosure — required, locked on
      </div>

      <details className="group border-t border-ink-900/10 pt-3">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400 transition-colors hover:text-ink-900">
          Alt text per slide ({altText.length})
          <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90 motion-reduce:transition-none" />
        </summary>
        <div className="mt-3 flex flex-col gap-2.5">
          {altText.map((text, index) => (
            <label key={index} className="flex flex-col gap-1">
              <span className="fac text-[9.5px]">Slide {index + 1}</span>
              <Textarea
                value={text}
                className="min-h-[56px] text-[12.5px]"
                onChange={(event) => setAlt(index, event.target.value)}
                aria-label={`Alt text for slide ${index + 1}`}
              />
            </label>
          ))}
        </div>
      </details>

      {error ? <p className="text-[12px] text-signal">{error}</p> : null}

      <div className="flex items-center gap-3 border-t border-ink-900/10 pt-4">
        <Button type="submit" size="sm" disabled={!dirty || saving || altText.some((text) => !text.trim())}>
          <Save className="h-3.5 w-3.5" />
          {saving ? "Saving…" : "Save changes"}
        </Button>
        {saved && !dirty ? (
          <span className="text-[11.5px] font-medium text-[#1f7444]">Saved</span>
        ) : !dirty ? (
          <span className="text-[11.5px] text-ink-400">No unsaved changes</span>
        ) : null}
      </div>
    </form>
  );
}
