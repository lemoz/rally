import { NextRequest, NextResponse } from "next/server";
import { kv, keys, CommentRecord } from "@/lib/kv";
import { getOrCreateSessionId } from "@/lib/session";

export const runtime = "nodejs";

const MAX_BODY_LEN = 280;

type PostBody = {
  video_id: string;
  body: string;
};

export async function POST(req: NextRequest) {
  const data = (await req.json()) as Partial<PostBody>;
  const trimmed = (data.body ?? "").trim();
  if (!data.video_id || !trimmed) {
    return NextResponse.json({ error: "video_id and body required" }, { status: 400 });
  }
  if (trimmed.length > MAX_BODY_LEN) {
    return NextResponse.json({ error: `body must be <= ${MAX_BODY_LEN} chars` }, { status: 400 });
  }

  const sessionId = await getOrCreateSessionId();
  const record: CommentRecord = {
    body: trimmed,
    session_id: sessionId,
    ts: Date.now(),
  };

  await kv.lpush(keys.comments(data.video_id), record);

  console.log(`[comment] session=${sessionId.slice(0, 8)} video=${data.video_id} len=${trimmed.length}`);

  return NextResponse.json({ ok: true, comment: record });
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const videoId = url.searchParams.get("video_id");
  if (!videoId) {
    return NextResponse.json({ error: "video_id query param required" }, { status: 400 });
  }
  const comments = await kv.lrange(keys.comments(videoId), 0, 49);
  return NextResponse.json({ video_id: videoId, comments });
}
