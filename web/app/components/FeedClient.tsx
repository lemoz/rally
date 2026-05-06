"use client";

import { useEffect, useRef, useState } from "react";
import type { Video, EngagementSnapshot } from "@/lib/types";
import VideoCard from "./VideoCard";
import CommentDrawer from "./CommentDrawer";

type EnrichedVideo = Video & EngagementSnapshot;

type Props = {
  initialVideos: EnrichedVideo[];
};

export default function FeedClient({ initialVideos }: Props) {
  const [activeId, setActiveId] = useState<string | null>(initialVideos[0]?.id ?? null);
  const [openComments, setOpenComments] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
            const id = (entry.target as HTMLElement).dataset.videoId;
            if (id) setActiveId(id);
          }
        }
      },
      { root, threshold: [0.6] },
    );

    const sections = root.querySelectorAll<HTMLElement>("[data-video-id]");
    sections.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  if (initialVideos.length === 0) {
    return <EmptyFeed />;
  }

  return (
    <>
      <div
        ref={containerRef}
        className="h-screen w-full overflow-y-scroll snap-y snap-mandatory"
      >
        {initialVideos.map((v) => (
          <div key={v.id} data-video-id={v.id}>
            <VideoCard
              video={v}
              initial={{
                views: v.views,
                likes: v.likes,
                comment_count: v.comment_count,
                liked_by_session: v.liked_by_session,
              }}
              isActive={v.id === activeId}
              onOpenComments={setOpenComments}
            />
          </div>
        ))}
      </div>
      <CommentDrawer videoId={openComments} onClose={() => setOpenComments(null)} />
    </>
  );
}

function EmptyFeed() {
  return (
    <main className="flex flex-col items-center justify-center flex-1 px-6 py-16 text-center min-h-screen">
      <img src="/r-logo.png" alt="Rally" width={120} height={120} className="mb-8" />
      <h1 className="text-5xl font-bold tracking-tight">Rally</h1>
      <p className="mt-4 max-w-md text-lg opacity-80">
        Short videos about real projects. Your engagement directs AI agents.
      </p>
      <p className="mt-12 text-sm opacity-50">
        Generating videos. Check back soon.
      </p>
      <div className="mt-8 flex gap-4 text-sm">
        <a
          href="https://www.tiktok.com/@rallysignal"
          target="_blank"
          rel="noopener noreferrer"
          className="underline opacity-70 hover:opacity-100"
        >
          @rallysignal
        </a>
        <a
          href="https://github.com/lemoz/rally"
          target="_blank"
          rel="noopener noreferrer"
          className="underline opacity-70 hover:opacity-100"
        >
          github
        </a>
      </div>
    </main>
  );
}
