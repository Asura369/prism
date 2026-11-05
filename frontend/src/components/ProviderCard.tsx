import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ProviderInfo } from "@/types";

type Notice = { tone: "ok" | "bad"; text: string } | null;

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Request failed";
}

export function ProviderCard({ provider }: { provider: ProviderInfo }) {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    setApiKey("");
    setNotice(null);
  }, [provider.key_set, provider.active, provider.configured]);

  const afterWrite = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["providers"] }),
      queryClient.invalidateQueries({ queryKey: ["settings"] }),
    ]);
  };

  const save = useMutation({
    mutationFn: () => api.saveProvider(provider.name, { api_key: apiKey.trim() }),
    onSuccess: async () => {
      setNotice({ tone: "ok", text: "Key stored. It is write-only from here on." });
      await afterWrite();
    },
    onError: (error) => setNotice({ tone: "bad", text: errorText(error) }),
  });

  const test = useMutation({
    mutationFn: () =>
      api.testProvider(provider.name, apiKey.trim() ? { api_key: apiKey.trim() } : {}),
    onSuccess: (result) =>
      setNotice(
        result.ok
          ? { tone: "ok", text: `Responded in ${result.latency_ms} ms.` }
          : { tone: "bad", text: `${result.error}: ${result.message ?? "no response"}` },
      ),
    onError: (error) => setNotice({ tone: "bad", text: errorText(error) }),
  });

  const activate = useMutation({
    mutationFn: () => api.activateProvider(provider.name),
    onSuccess: async () => {
      setNotice({ tone: "ok", text: "Active provider." });
      await afterWrite();
    },
    onError: (error) => setNotice({ tone: "bad", text: errorText(error) }),
  });

  const removeKey = useMutation({
    mutationFn: () => api.deleteProviderKey(provider.name),
    onSuccess: async () => {
      setNotice({ tone: "ok", text: "Key deleted. Enter a new one to reconfigure." });
      await afterWrite();
    },
    onError: (error) => setNotice({ tone: "bad", text: errorText(error) }),
  });

  const busy = save.isPending || test.isPending || activate.isPending || removeKey.isPending;

  return (
    <section className="rounded-plate border border-ink-900/12 bg-paper-50">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-900/8 px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="text-[13px] font-semibold text-ink-900">{provider.label}</h3>
          {provider.active ? <Badge variant="success">active</Badge> : null}
          <Badge variant={provider.key_set ? "default" : "outline"}>
            {provider.key_set ? "key set" : "no key"}
          </Badge>
        </div>
        <span className="font-mono text-[11px] text-ink-400">{provider.name}</span>
      </header>

      <div className="flex flex-col gap-3 px-4 py-3.5">
        <dl className="flex flex-col gap-1.5">
          <div className="flex items-baseline gap-2">
            <dt className="w-20 shrink-0 text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-400">
              Base URL
            </dt>
            <dd className="font-mono text-[11.5px] break-all text-ink-700">{provider.base_url}</dd>
          </div>
          <div className="flex items-baseline gap-2">
            <dt className="w-20 shrink-0 text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-400">
              Model
            </dt>
            <dd className="font-mono text-[11.5px] text-ink-700">{provider.model}</dd>
          </div>
        </dl>

        {provider.key_set ? (
          <p className="text-[11.5px] leading-relaxed text-ink-400">
            The key is stored write-only: it is never shown again. To change it, delete it and re-enter it.
          </p>
        ) : (
          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-400">API key</span>
            <Input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              autoComplete="new-password"
              placeholder="sk-…"
              className="font-mono text-[12px]"
              aria-label={`${provider.label} API key`}
            />
          </label>
        )}

        {notice ? (
          <p
            role="status"
            className={notice.tone === "ok" ? "text-[11.5px] text-ink-500" : "text-[11.5px] text-[#a32d1b]"}
          >
            {notice.text}
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          {provider.key_set && provider.configured && !provider.active ? (
            <Button size="sm" onClick={() => activate.mutate()} disabled={busy}>
              Activate
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="outline"
            onClick={() => test.mutate()}
            disabled={busy || (!provider.key_set && !apiKey.trim())}
          >
            Test connection
          </Button>
          {provider.key_set ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                if (window.confirm(`Delete the stored key for ${provider.label}? You will have to enter it again.`)) {
                  removeKey.mutate();
                }
              }}
            >
              Delete key
            </Button>
          ) : (
            <Button size="sm" onClick={() => save.mutate()} disabled={busy || !apiKey.trim()}>
              Save
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
