import { NextRequest, NextResponse } from "next/server";
import { kv, keys } from "@/lib/kv";
import { getOrCreateSessionId } from "@/lib/session";

export const runtime = "nodejs";

type Body = {
  video_id: string;
  action: "view" | "like" | "unlike";
};

export async function POST(req: NextRequest) {
  const body = (await req.json()) as Partial<Body>;
  if (!body.video_id || !body.action) {
    return NextResponse.json({ error: "video_id and action required" }, { status: 400 });
  }

  const sessionId = await getOrCreateSessionId();
  const videoId = body.video_id;

  if (body.action === "view") {
    const seen = await kv.sismember(keys.sessionViews(sessionId), videoId);
    if (!seen) {
      await kv.sadd(keys.sessionViews(sessionId), videoId);
      await kv.incr(keys.views(videoId));
    }
  } else if (body.action === "like") {
    const already = await kv.sismember(keys.sessionLikes(sessionId), videoId);
    if (!already) {
      await kv.sadd(keys.sessionLikes(sessionId), videoId);
      await kv.incr(keys.likes(videoId));
    }
  } else if (body.action === "unlike") {
    const had = await kv.sismember(keys.sessionLikes(sessionId), videoId);
    if (had) {
      await kv.srem(keys.sessionLikes(sessionId), videoId);
      await kv.decr(keys.likes(videoId));
    }
  } else {
    return NextResponse.json({ error: "unknown action" }, { status: 400 });
  }

  const [views, likes, liked] = await Promise.all([
    kv.get(keys.views(videoId)),
    kv.get(keys.likes(videoId)),
    kv.sismember(keys.sessionLikes(sessionId), videoId),
  ]);

  console.log(
    `[engage] session=${sessionId.slice(0, 8)} video=${videoId} action=${body.action} views=${views} likes=${likes}`,
  );

  return NextResponse.json({ video_id: videoId, views, likes, liked_by_session: liked });
}
