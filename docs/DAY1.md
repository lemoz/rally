# Day 1 — 2026-05-06

The day Rally went from "concept doc + private POC" to "public repo + live feed + first agent-actionable issues."

## What shipped

### Distribution
- **TikTok account** [@rallysignal](https://www.tiktok.com/@rallysignal) — name "Rally", bio "Short videos about real projects. Your engagement directs AI agents.", brutalist yellow R logo

### Repo
- **Public** at [github.com/lemoz/rally](https://github.com/lemoz/rally) under MIT license
- 4 commits added on top of the existing 3 — `.gitignore`, docs/v2, rally-poc source, LICENSE
- `.gitignore` now keeps the 833 MB of POC video output and reference images out of git; source-only tree is ~640 KB

### Web app
- **Live** at [rallysignal.co](https://rallysignal.co) (Vercel project, custom domain wired via Namecheap → Vercel nameservers)
- Real feed app shape: vertical-scroll with autoplay, like + comment + view counters, anonymous session cookies
- Three API routes — `/api/engage`, `/api/comment`, `/api/feed`
- Components — `FeedClient`, `VideoCard`, `CommentDrawer`
- Storage layer in `web/lib/kv.ts` is in-memory for v0, designed to swap to Upstash Redis when provisioned (Day 2)
- Empty state renders Rally's brand identity until videos land

### Content
- **20 video concepts** drafted across four buckets — build logs, dogfood demos, thesis explainers, style explorations — at `rally-poc/project-rally/concepts.md`
- **2 storyboard JSONs** ready to render — `rally_001_thesis_anime.json` (psyop_anime_90s, 26s, English VO) and `rally_002_proof_carousel.json` (proof_carousel, 24s)

### The loop
- **5 `rally-loop` issues** filed at [github.com/lemoz/rally/labels/rally-loop](https://github.com/lemoz/rally/issues?q=is%3Aopen+label%3Arally-loop) — TikTok engagement poller, signal score formula, agent runner, video-issue auto-link, keystone (the second video)

## What we decided

- **Rally itself is project #1** before any external OSS — the loop has to close on something we control before scaling. OpenScreen videos move to project #2.
- **Real feed app, not landing page** — tests engagement capture even though TikTok already has it
- **Anonymous sessions, no auth** — captures device-level signal without a barrier
- **In-memory storage v0**, Upstash Redis Day 2 — ship the architecture today, swap persistence Day 2
- **Agent work bar = merged PR** for Rally; submitted PR + maintainer engagement for external OSS
- **MIT license** — required for the loop to be observable; permissive default

## What's queued for Day 2

- **Generate the first 3-5 videos.** The two written JSONs are ready; pipeline is proven from Glasswing. Estimated ~$5-9 each, 30-60 min wall clock per render.
- **Provision Upstash Redis** via Vercel marketplace integration; swap the in-memory layer for real persistence
- **rallysignal.co** registered and DNS pointing at Vercel (rally.fyi turned out to be aftermarket-only, not a true new registration)
- **Update TikTok bio** with the live URL
- **First TikTok post** — once the first video renders and eval-passes, post on Day 2 morning timing
- **Implementation work on the 5 `rally-loop` issues** — actual code, not just filings

## What didn't ship

- **rally.fyi** turned out to be aftermarket-only ("Make offer", not a fresh registration). Pivoted to rallysignal.co — registered and DNS configured.
- **First video posted to TikTok** — explicitly held to Day 2 morning per the plan
- **KV / Redis persistence** — in-memory only today
- **Signal score implementation** — issue 2 filed, not built
- **Agent runner** — issue 3 filed, not built

## Numbers

- **$0 spent on the day so far** (all infrastructure on free tiers)
- **Pending spend**: $21 for rally.fyi domain
- **Anticipated Day 2 spend**: ~$25-50 on first video batch generation
- **Repo size**: <10 MB (audited; no media leaked into git)
- **Pre-commit footprint after .gitignore audit**: 0.39 MB
- **Lines added**: ~12k across 5 commits (most are the v2 docs)

## Risks that materialized

- **Vercel free-tier project URL is auto-protected** for team-scoped subdomains; the friendly alias `rally-woad-nine.vercel.app` is public and what we promote.
- **Vercel KV requires marketplace integration**, not CLI provisioning. Hence the in-memory v0 layer.
- **Hard guardrails on identity-affecting actions** during TikTok account setup required Chris to type the handle directly. Logged for memory.

## Risks that didn't materialize

- No 833 MB push to git — the commit-by-commit `git status` review caught it
- No Vercel deploy failures — clean first push, build green, alias active
- No TikTok flag on the new account — `@rallysignal` lives, profile pic + bio set without throttle

## Verification (per plan)

| Check | Pass |
|---|---|
| `github.com/lemoz/rally` public, MIT, no media files | ✅ |
| Vercel feed URL loads, brand renders | ✅ |
| Empty-state messaging visible | ✅ |
| API routes deployed (`/api/engage`, `/api/comment`, `/api/feed`) | ✅ |
| 5 `rally-loop` issues filed | ✅ |
| 20 concepts written | ✅ |
| 2 storyboard JSONs ready to render | ✅ |
| First video rendered + eval-passed | ⏳ Day 2 |
| Engagement persistence in KV | ⏳ Day 2 (in-memory today) |
| Custom domain live | ⏳ Pending purchase |

## Tomorrow's first hour

1. Provision Upstash Redis via Vercel dashboard, plug into `web/lib/kv.ts`
2. Confirm + register `rally.fyi`
3. Run `python3 -m pipeline.run_pipeline rally_001_thesis_anime.json` and eval the result
4. Post the first video to `@rallysignal`
5. Update TikTok bio with `rally.fyi`
