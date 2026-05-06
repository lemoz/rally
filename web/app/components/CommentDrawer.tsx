"use client";

import { useEffect, useState } from "react";
import type { CommentRecord } from "@/lib/kv";

type Props = {
  videoId: string | null;
  onClose: () => void;
};

export default function CommentDrawer({ videoId, onClose }: Props) {
  const [comments, setComments] = useState<CommentRecord[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    if (!videoId) return;
    setLoading(true);
    fetch(`/api/comment?video_id=${encodeURIComponent(videoId)}`)
      .then((r) => r.json())
      .then((data) => setComments(data.comments ?? []))
      .finally(() => setLoading(false));
  }, [videoId]);

  if (!videoId) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || posting) return;
    setPosting(true);
    try {
      const res = await fetch("/api/comment", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ video_id: videoId, body: trimmed }),
      });
      if (res.ok) {
        const data = await res.json();
        setComments((prev) => [data.comment, ...prev]);
        setDraft("");
      }
    } finally {
      setPosting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/80"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md h-2/3 bg-zinc-950 border-t-2 border-brand-yellow rounded-t-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="p-4 border-b border-brand-yellow/20 flex justify-between items-center">
          <h3 className="text-brand-yellow font-bold">Comments</h3>
          <button onClick={onClose} className="text-brand-yellow/70 text-2xl leading-none">
            ×
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && <p className="text-brand-yellow/50 text-sm">Loading…</p>}
          {!loading && comments.length === 0 && (
            <p className="text-brand-yellow/50 text-sm">No comments yet. Be the first.</p>
          )}
          {comments.map((c, i) => (
            <div key={`${c.ts}-${i}`} className="text-sm">
              <p className="text-brand-yellow/50 text-xs mb-0.5">
                anon-{c.session_id.slice(0, 6)} · {timeAgo(c.ts)}
              </p>
              <p className="text-brand-yellow break-words">{c.body}</p>
            </div>
          ))}
        </div>
        <form
          onSubmit={submit}
          className="p-4 border-t border-brand-yellow/20 flex gap-2"
        >
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            maxLength={280}
            placeholder="Comment…"
            className="flex-1 bg-black border border-brand-yellow/30 rounded px-3 py-2 text-brand-yellow placeholder:text-brand-yellow/30 text-sm focus:outline-none focus:border-brand-yellow"
          />
          <button
            type="submit"
            disabled={!draft.trim() || posting}
            className="bg-brand-yellow text-brand-black px-3 py-2 rounded text-sm font-bold disabled:opacity-30"
          >
            Post
          </button>
        </form>
      </div>
    </div>
  );
}

function timeAgo(ts: number): string {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}
