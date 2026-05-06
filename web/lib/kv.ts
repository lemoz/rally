/**
 * Storage abstraction for engagement counters and comments.
 *
 * v0 (Day 1): in-memory Map. Persists for the lifetime of a single warm
 * serverless instance only. Resets on cold start. Good enough for demo.
 *
 * v1 (Day 2): swap to Upstash Redis via @upstash/redis when Chris provisions
 * the integration. Same interface; only this file changes.
 */

type Counter = number;
type CommentRecord = {
  body: string;
  session_id: string;
  ts: number;
};

const counters = new Map<string, Counter>();
const sets = new Map<string, Set<string>>();
const lists = new Map<string, CommentRecord[]>();

export const kv = {
  async incr(key: string): Promise<number> {
    const next = (counters.get(key) ?? 0) + 1;
    counters.set(key, next);
    return next;
  },

  async decr(key: string): Promise<number> {
    const next = Math.max(0, (counters.get(key) ?? 0) - 1);
    counters.set(key, next);
    return next;
  },

  async get(key: string): Promise<number> {
    return counters.get(key) ?? 0;
  },

  async sadd(key: string, member: string): Promise<boolean> {
    const set = sets.get(key) ?? new Set<string>();
    if (set.has(member)) return false;
    set.add(member);
    sets.set(key, set);
    return true;
  },

  async srem(key: string, member: string): Promise<boolean> {
    const set = sets.get(key);
    if (!set?.has(member)) return false;
    set.delete(member);
    return true;
  },

  async sismember(key: string, member: string): Promise<boolean> {
    return sets.get(key)?.has(member) ?? false;
  },

  async lpush(key: string, item: CommentRecord): Promise<number> {
    const list = lists.get(key) ?? [];
    list.unshift(item);
    lists.set(key, list);
    return list.length;
  },

  async lrange(key: string, start: number, end: number): Promise<CommentRecord[]> {
    const list = lists.get(key) ?? [];
    if (end === -1) return list.slice(start);
    return list.slice(start, end + 1);
  },
};

// Key helpers — keep schema in one place.
export const keys = {
  views: (videoId: string) => `engage:${videoId}:views`,
  likes: (videoId: string) => `engage:${videoId}:likes`,
  sessionLikes: (sessionId: string) => `session:${sessionId}:liked`,
  sessionViews: (sessionId: string) => `session:${sessionId}:viewed`,
  comments: (videoId: string) => `comments:${videoId}`,
};

export type { CommentRecord };
