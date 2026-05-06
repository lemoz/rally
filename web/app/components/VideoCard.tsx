"use client";

import { useEffect, useRef, useState } from "react";
import type { Video, EngagementSnapshot } from "@/lib/types";

type Props = {
  video: Video;
  initial: EngagementSnapshot;
  isActive: boolean;
  onOpenComments: (videoId: string) => void;
};

export default function VideoCard({ video, initial, isActive, onOpenComments }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [counts, setCounts] = useState<EngagementSnapshot>(initial);
  const [viewFired, setViewFired] = useState(false);

  // Autoplay/pause when becoming active.
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    if (isActive) {
      el.play().catch(() => {/* user gesture needed; leave paused */});
    } else {
      el.pause();
      el.currentTime = 0;
    }
  }, [isActive]);

  // Fire a view event after 2s of active playback.
  useEffect(() => {
    if (!isActive || viewFired) return;
    const t = setTimeout(() => {
      setViewFired(true);
      fetch("/api/engage", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ video_id: video.id, action: "view" }),
      })
        .then((r) => r.json())
        .then((data: EngagementSnapshot) => setCounts((prev) => ({ ...prev, ...data })))
        .catch(() => {/* ignore */});
    }, 2000);
    return () => clearTimeout(t);
  }, [isActive, viewFired, video.id]);

  async function toggleLike() {
    const action = counts.liked_by_session ? "unlike" : "like";
    setCounts((prev) => ({
      ...prev,
      liked_by_session: !prev.liked_by_session,
      likes: prev.likes + (prev.liked_by_session ? -1 : 1),
    }));
    try {
      const res = await fetch("/api/engage", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ video_id: video.id, action }),
      });
      const data: EngagementSnapshot = await res.json();
      setCounts((prev) => ({ ...prev, ...data }));
    } catch {
      // revert optimistic update on failure
      setCounts((prev) => ({
        ...prev,
        liked_by_session: !prev.liked_by_session,
        likes: prev.likes + (prev.liked_by_session ? -1 : 1),
      }));
    }
  }

  return (
    <section
      className="relative h-screen w-full snap-start snap-always flex items-center justify-center bg-black"
      aria-label={video.title}
    >
      <video
        ref={videoRef}
        src={video.file}
        poster={video.poster}
        playsInline
        muted
        loop
        preload="metadata"
        className="h-full w-full object-contain"
      />
      <div className="absolute bottom-6 left-4 right-20 text-brand-yellow">
        <p className="text-xs uppercase opacity-60">{video.project}</p>
        <h2 className="text-lg font-bold leading-tight mt-1">{video.title}</h2>
        {video.caption && <p className="text-sm opacity-80 mt-1 line-clamp-2">{video.caption}</p>}
      </div>
      <div className="absolute bottom-6 right-3 flex flex-col items-center gap-5">
        <button
          onClick={toggleLike}
          aria-label={counts.liked_by_session ? "Unlike" : "Like"}
          className="flex flex-col items-center text-brand-yellow"
        >
          <span className={`text-3xl ${counts.liked_by_session ? "" : "opacity-60"}`}>
            {counts.liked_by_session ? "♥" : "♡"}
          </span>
          <span className="text-xs mt-1 tabular-nums">{counts.likes}</span>
        </button>
        <button
          onClick={() => onOpenComments(video.id)}
          aria-label="Open comments"
          className="flex flex-col items-center text-brand-yellow"
        >
          <span className="text-3xl opacity-60">💬</span>
          <span className="text-xs mt-1 tabular-nums">{counts.comment_count}</span>
        </button>
        <div className="flex flex-col items-center text-brand-yellow opacity-60">
          <span className="text-xs">views</span>
          <span className="text-xs tabular-nums">{counts.views}</span>
        </div>
      </div>
      {video.tiktok_url && (
        <a
          href={video.tiktok_url}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute top-4 right-4 text-xs text-brand-yellow opacity-70 underline"
        >
          tiktok
        </a>
      )}
    </section>
  );
}
