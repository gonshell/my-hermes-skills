---
name: youtube-content
description: >
  Fetch YouTube video transcripts and transform them into structured content
  (chapters, summaries, threads, blog posts). Use when the user shares a YouTube
  URL or video link, asks to summarize a video, requests a transcript, or wants
  to extract and reformat content from any YouTube video.
---

# YouTube Content Tool

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

```bash
# IMPORTANT: Use the correct Python interpreter — multiple Pythons may be on PATH
# Correct interpreter (Hermes uv venv):
/Users/xiesg/.hermes/hermes-agent/venv/bin/python3

# Install to the correct venv:
/Users/xiesg/.hermes/hermes-agent/venv/bin/python3 -m pip install youtube-transcript-api
# OR use uv:
uv pip install youtube-transcript-api  # must run in the hermes-agent dir context

# Verify:
/Users/xiesg/.hermes/hermes-agent/venv/bin/python3 -c "import youtube_transcript_api; print('ok')"
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Workflow

1. **Fetch** the transcript using the helper script with `--text-only --timestamps`.
2. **Validate**: confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript. If still empty, tell the user the video likely has transcripts disabled.
3. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
4. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
5. **Verify**: re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.

## Environment Notes (Hermes / uv)

When running inside Hermes Agent, there are **two distinct Python environments**:

### `terminal()` → Hermes uv venv
```
Python: /Users/xiesg/.hermes/hermes-agent/venv/bin/python3
site-packages: /Users/xiesg/.hermes/hermes-agent/venv/lib/python3.11/site-packages/
```
- `pip install` → fails → use `uv pip install` instead
- `uv pip install youtube-transcript-api` ✅ works
- `uv pip install yt-dlp` ✅ works
- Network requests exit from the server's datacenter IP (often blocked by YouTube)

### `execute_code()` → Independent sandbox
```
Python: 3.13.5 (standard library only)
```
- Cannot use `uv pip install` packages (sandbox isolation)
- Only stdlib modules available (`urllib`, `json`, `re`, etc.)
- Network requests exit from same datacenter IP → also blocked

### Which to use when
- **Transcript extraction** → use `terminal()` with `uv pip install`'d packages
- **Quick HTML/URL inspection** → `execute_code()` with stdlib `urllib`
- **Browser navigation** → uses same blocked IP as terminal (NOT a separate residential proxy)

### IP Warning
The exit IP (e.g., `185.152.67.176`) is a **datacenter/cloud IP**. YouTube blocks all access from such IPs (429, CAPTCHA, empty responses). This blocks:
- `youtube-transcript-api` → `IpBlocked` error
- `yt-dlp` → HTTP 429 + "Sign in to confirm"
- Direct `curl`/`urllib` to YouTube → 429 or empty body
- Browser navigation → CAPTCHA page

**If blocked, fall back to metadata inference** (see Fallback Workflow above) and instruct the user to run locally on their residential IP if transcript is critical.

## Error Handling

- **"Subtitles/closed captions unavailable" shown on video page**: This means the video has NO subtitles uploaded — not a transient failure. Server-side transcript tools will also fail. Reconstruct content from the **description chapter timestamps + source URLs** (see Step 1 above). This is actually a reliable way to get the video's full structure even without transcript. Also try: search for the video title + channel name — creators often republish the same content on their website or blog.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing / script fails**: see Fallback Workflow below.
- **Caption URL returns empty / 200 OK but no content**: This is the **IP-signature binding** issue — YouTube's `api/timedtext` URLs are signed with the requestor's IP and a timestamp. Server-side fetching from a different IP returns HTTP 200 with empty body. See Fallback Workflow Step 1 instead.
- **pip not installed**: Cannot install `youtube-transcript-api`. Use `uv pip install` in Hermes uv venv.
- **Browser also shows CAPTCHA / 429**: The browser shares the same datacenter exit IP as `terminal()`. Even the browser console cannot bypass YouTube's block if the exit IP is blocked. Do NOT keep retrying — fall back to metadata inference immediately and suggest the user run locally.
- **IpBlocked / "datacenter IP"**: The server/Hermes exit IP is from a cloud/datacenter provider (e.g., `185.152.67.x`). YouTube aggressively blocks these. Fall back to metadata inference or have the user run locally on their residential IP.

---

## Fallback Workflow (When Transcript Extraction Fails)

If the helper script fails (timeout, IpBlocked, 429, CAPTCHA), fall back to this pipeline. Two distinct failure modes require different handling — see "Two Distinct Failure Modes" below.

### Step 1 — Get video metadata from the page

Navigate to the YouTube video page and extract:
- **Title** → overall topic
- **Description** → key points, chapter markers (often `0:00`, `1:23` patterns), and **SOURCE LINKS** to referenced articles — these are often clickable URLs confirming what the creator is discussing
- **View count, upload date, channel** → credibility / scope hints
- **Chapter timestamps in the description** → **the single best source when transcripts are unavailable**. Format is typically `[link text](0:00)` or plain `0:00 Topic`. Each chapter gives you a topic + timestamp + often a source URL. Reconstruct the full video structure from these.
- **Related videos** sidebar → other videos by the same creator on the same topic → infer the video's likely structure

> ⚠️ **Important — Why page HTML caption URLs don't work server-side:**
> Even if you find a `baseUrl` in the page HTML for captions (e.g., `youtube.com/api/timedtext?v=...&signature=...`), fetching it from a server returns HTTP 200 with empty body. YouTube signs these URLs with the **requestor's IP** and an **expiry timestamp**. Server IPs differ from the browser's IP, so the signature validation fails silently.
> If you have a browser session open AND the browser is using a residential IP, you CAN use the browser console to fetch captions. Otherwise, proceed with metadata inference.

> ⚠️ **Important — Why page HTML caption URLs don't work server-side:**
> Even if you find a `baseUrl` in the page HTML for captions (e.g., `youtube.com/api/timedtext?v=...&signature=...`), fetching it from a server will return HTTP 200 with empty body. YouTube signs these URLs with the **requestor's IP** and an **expiry timestamp**. Server IPs differ from the browser's IP, so the signature validation fails silently (YouTube returns empty HTML rather than an error).
> If you have a browser session open, you CAN use the browser console to fetch captions (see Quick Browser Extraction below). Otherwise, proceed with metadata inference.

### Step 2 — Infer structure from related videos

YouTube's "Up next" and sidebar recommendations often reveal the video's chapter structure. Look for:
- Videos with similar titles (e.g., "Part 1", "Part 2", or same topic with "Explained", "Tutorial")
- Chapter markers in descriptions of related videos
- Playlist ordering if visible

### Step 3 — Synthesize a content inference

Using metadata + channel content patterns, produce a reasonable summary that includes:
- Likely topics covered (based on title keywords, channel style, description)
- Approximate timing estimates (e.g., "intro ~0-5min, core content ~5-20min, conclusion ~20-23min")
- Key concepts mentioned in title/description
- Note that this is an **inference-based summary** due to transcript unavailability

### Step 4 — Always be transparent

Tell the user:
> "I couldn't access the transcript directly (the transcript API was unavailable in this environment). This summary is inferred from the video title, description, and related content. It may not be fully accurate."

---

### Quick Browser Extraction Commands

```javascript
// Extract title
document.querySelector('meta[name="title"]')?.content || document.title

// Extract description
document.querySelector('meta[property="og:description"]')?.content || ''

// Extract view count
document.querySelector('meta[itemprop="interactionCount"]')?.content || ''

// Extract publish date
document.querySelector('meta[itemprop="datePublished"]')?.content || ''

// Fetch captions directly through browser (bypasses IP-signature issue)
// Run this on the YouTube video page - browser session has valid signature
(async () => {
  try {
    const resp = await fetch('https://www.youtube.com/api/timedtext?v=VIDEO_ID&fmt=json3&lang=en');
    const text = await resp.text();
    console.log('Caption length:', text.length);
    console.log(text);
  } catch(e) { console.error('Failed:', e); }
})();
```

> **Note:** The browser console fetch works only if the browser uses a **residential IP**. In Hermes, the browser shares the same datacenter exit IP as `terminal()` — if YouTube blocks that IP, even the browser console fetch fails silently (returns empty). In that case, no server-side approach works; transcript is unavailable unless the user runs locally on their residential IP.

### Two Distinct Failure Modes (Critical)

YouTube transcript failures have **two different root causes**:

1. **IP blocked** (datacenter IP flagged) — YouTube returns 429/CAPTCHA/timeout
   - Fix: Use **residential proxy** with `youtube-transcript-api`
   - `python3 /path/to/venv/bin/python3 -c "from youtube_transcript_api import YouTubeTranscriptApi; print(YouTubeTranscriptApi.get_transcript('ID', proxies={'http':'http://user:pass@host:port','https':'http://user:pass@host:port'}))"`

2. **Video has no subtitles** (YouTube shows "Subtitles/closed captions unavailable")
   - Fix: **No server-side fix possible** — this is a video-level limitation
   - Workaround: Use **ASR/speech-to-text API** (AssemblyAI, Speechmatics, Rev.com)
     - Download audio via `yt-dlp -x --audio-format mp3 URL` (or `-x --audio-format wav`)
     - Send audio file to ASR API
     - Cost: ~$0.02/min (AssemblyAI) to ~$1.50/min (Rev.com human)
     - AssemblyAI example:
       ```python
       import subprocess
       # 1. Download audio (yt-dlp from hermes venv)
       subprocess.run(['/Users/xiesg/.hermes/hermes-agent/venv/bin/python3', '-m', 'pip', 'install', 'yt-dlp'])
       subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', '-o', '/tmp/audio.%(ext)s', URL])
       # 2. Transcribe
       subprocess.run(['/Users/xiesg/.hermes/hermes-agent/venv/bin/python3', '-m', 'pip', 'install', 'assemblyai'])
       import assemblyai as aai
       aai.settings.api_key = "YOUR_KEY"
       transcript = aai.Transcriber().transcribe("/tmp/audio.mp3")
       print(transcript.text)
       ```
   - **This is the only option that works for no-subtitle videos** when datacenter IP is blocked

For related videos, check the video rows in the sidebar (`#related` or `ytd-watch-next-secondary-results`). Their titles often reveal what topics the main video covers.
