#!/usr/bin/env python3
"""
X (Twitter) Media Scraper
-------------------------
- Input: a username (without @)
- Output:
  downloads/<username>/images/...jpg|png
  downloads/<username>/videos/...mp4
  downloads/<username>/<username>.json  (tweet text + metadata)

Notes:
- Uses snscrape (no official API) + yt_dlp to fetch media
- Resumes safely: skips files that already exist
- Add a cookies file to yt_dlp if you need to access restricted media (optional)

Install dependencies:
  pip install snscrape yt-dlp requests tqdm

Usage:
  python x_media_scraper.py --user <username> [--limit 0] [--since YYYY-MM-DD] [--max-consec-errors 50]
"""

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import requests
from tqdm import tqdm

# snscrape imports (installed via pip)
import snscrape.modules.twitter as sntwitter

# yt_dlp for videos / GIFs
from yt_dlp import YoutubeDL

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

@dataclass
class MediaItem:
    type: str  # 'photo' | 'video' | 'gif'
    url: str
    local_path: Optional[str] = None

@dataclass
class TweetRecord:
    id: int
    url: str
    date: str
    content: str
    replyCount: int
    retweetCount: int
    likeCount: int
    quoteCount: int
    viewCount: Optional[int]
    media: List[MediaItem] = field(default_factory=list)

def safe_filename(name: str, maxlen: int = 150) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    if len(name) > maxlen:
        name = name[:maxlen]
    return name

def download_image(url: str, dest: Path, session: requests.Session, timeout: int = 30) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT, "Referer": "https://x.com"}
    with session.get(url, headers=headers, stream=True, timeout=timeout) as r:
        if r.status_code == 200:
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
    return False

def download_video_with_ytdlp(tweet_url: str, outtmpl: str, cookies: Optional[str] = None) -> Optional[str]:
    ydl_opts = {
        "outtmpl": outtmpl,  # e.g., '/path/to/%(id)s.%(ext)s'
        "quiet": True,
        "noprogress": True,
        "ignoreerrors": True,
        "retries": 10,
        "concurrent_fragment_downloads": 3,
        "http_headers": {"User-Agent": USER_AGENT},
        # Prefer mp4 when possible
        "merge_output_format": "mp4",
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tweet_url, download=True)
            if info:
                # Return the final filename if yt-dlp provides it
                return ydl.prepare_filename(info)
    except Exception as e:
        # Swallow and let caller decide
        return None
    return None

def iter_user_tweets(username: str, since: Optional[str] = None, limit: int = 0):
    # Build the snscrape query: from:username since:YYYY-MM-DD
    query = f"from:{username}"
    if since:
        query += f" since:{since}"

    scraper = sntwitter.TwitterSearchScraper(query)
    count = 0
    for tweet in scraper.get_items():
        # Optional limit
        if limit and count >= limit:
            break
        count += 1
        yield tweet

def main():
    ap = argparse.ArgumentParser(description="X (Twitter) media scraper")
    ap.add_argument("--user", help="Username without @ (e.g., 'jack')")
    ap.add_argument("--limit", type=int, default=0, help="Max number of tweets to process (0 = no limit)")
    ap.add_argument("--since", type=str, default=None, help="Only tweets since this date (YYYY-MM-DD)")
    ap.add_argument("--cookies", type=str, default=None, help="Path to cookies.txt (optional, for yt-dlp)")
    ap.add_argument("--max-consec-errors", type=int, default=50, help="Stop after this many consecutive errors")
    args = ap.parse_args()

    username = args.user
    if not username:
        username = input("Enter X/Twitter username (without @): ").strip().lstrip("@")

    base = Path("downloads") / username
    images_dir = base / "images"
    videos_dir = base / "videos"
    json_path = base / f"{username}.json"

    base.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    records: List[TweetRecord] = []
    consec_errors = 0

    print(f"[+] Scraping @{username} (limit={args.limit or 'ALL'}) ...")
    for tweet in tqdm(iter_user_tweets(username, since=args.since, limit=args.limit)):
        try:
            tweet_url = f"https://x.com/{username}/status/{tweet.id}"
            rec = TweetRecord(
                id=int(tweet.id),
                url=tweet_url,
                date=tweet.date.isoformat(),
                content=tweet.rawContent or "",
                replyCount=getattr(tweet, "replyCount", 0) or 0,
                retweetCount=getattr(tweet, "retweetCount", 0) or 0,
                likeCount=getattr(tweet, "likeCount", 0) or 0,
                quoteCount=getattr(tweet, "quoteCount", 0) or 0,
                viewCount=getattr(tweet, "viewCount", None),
                media=[],
            )

            # Media handling
            media_set = getattr(tweet, "media", None)
            if media_set:
                for m in media_set:
                    # Photos
                    if m.__class__.__name__ == "Photo":
                        # Prefer 'fullUrl' if present; fallback to 'url'
                        url = getattr(m, "fullUrl", None) or getattr(m, "url", None)
                        if not url:
                            continue
                        fname = safe_filename(f"{tweet.id}_{Path(url).name}")
                        dest = images_dir / fname
                        if not dest.exists():
                            ok = download_image(url, dest, session)
                            if not ok:
                                # Try adding '?name=orig' if missing
                                if "name=" not in url:
                                    alt = url + "?name=orig"
                                    ok = download_image(alt, dest, session)
                            if not ok:
                                # Skip on failure
                                pass
                        if dest.exists():
                            rec.media.append(MediaItem(type="photo", url=url, local_path=str(dest)))
                    # GIFs and Videos (handle via yt-dlp on the tweet URL)
                    elif m.__class__.__name__ in ("Video", "Gif"):
                        outtmpl = str(videos_dir / f"{tweet.id}-%(id)s.%(ext)s")
                        # If a file for this tweet already exists, skip
                        existing = list(videos_dir.glob(f"{tweet.id}-*.*"))
                        if not existing:
                            final_path = download_video_with_ytdlp(tweet_url, outtmpl, cookies=args.cookies)
                        else:
                            final_path = str(existing[0])
                        # Record best guess
                        if final_path:
                            rec.media.append(MediaItem(type="video" if m.__class__.__name__=="Video" else "gif",
                                                       url=tweet_url, local_path=final_path))

            records.append(rec)
            consec_errors = 0  # reset on success
            # Gentle rate limit to be kind
            time.sleep(0.2)
        except KeyboardInterrupt:
            print("\n[!] Interrupted by user. Saving progress...")
            break
        except Exception as e:
            consec_errors += 1
            if consec_errors >= args.max_consec_errors:
                print(f"[!] Too many consecutive errors ({consec_errors}). Aborting.")
                break
            # brief backoff
            time.sleep(1)
            continue

    # Save JSON (pretty + line-delimited companion)
    out_data = [{
        **asdict(r),
        "media": [asdict(mi) for mi in r.media]
    } for r in records]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    # Also save a JSONL for easier streaming tools
    jsonl_path = base / f"{username}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in out_data:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[✓] Done. Media saved under: {base}")

if __name__ == "__main__":
    main()
