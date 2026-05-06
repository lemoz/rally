import { NextResponse } from "next/server";
import { kv, keys } from "@/lib/kv";
import { getSessionId } from "@/lib/session";
import videosManifest from "@/data/videos.json";
import type { Video } from "@/lib/types";

export const runtime = "nodejs";
export const revalidate = 10;

export async function GET() {
  const videos = (videosManifest as { videos: Video[] }).videos;
  const sessionId = await getSessionId();

  const enriched = await Promise.all(
    videos.map(async (video) => {
      const [views, likes, comments] = await Promise.all([
        kv.get(keys.views(video.id)),
        kv.get(keys.likes(video.id)),
        kv.lrange(keys.comments(video.id), 0, -1),
      ]);
      const likedByMe = sessionId
        ? await kv.sismember(keys.sessionLikes(sessionId), video.id)
        : false;
      return {
        ...video,
        views,
        likes,
        comment_count: comments.length,
        liked_by_session: likedByMe,
      };
    }),
  );

  return NextResponse.json({ videos: enriched });
}
