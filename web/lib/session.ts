import { cookies } from "next/headers";
import { randomUUID } from "node:crypto";

const COOKIE_NAME = "rally_session_id";
const ONE_YEAR = 60 * 60 * 24 * 365;

export async function getOrCreateSessionId(): Promise<string> {
  const store = await cookies();
  const existing = store.get(COOKIE_NAME);
  if (existing?.value) return existing.value;

  const id = randomUUID();
  store.set(COOKIE_NAME, id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: ONE_YEAR,
    path: "/",
  });
  return id;
}

export async function getSessionId(): Promise<string | null> {
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value ?? null;
}
