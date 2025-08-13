# JediSecurity-X-Account-Scraper
Account scraper for x. Downloads videos and photos. JSON the feed

# 1) deps
pip install snscrape yt-dlp requests tqdm

# 2) run (interactive prompt for username)
python x_media_scraper.py

# or specify user (without @)
python x_media_scraper.py --user jack

Videos/GIFs that require login
If some media are age-restricted or region-locked, export cookies from your browser as cookies.txt (Netscape format) and pass:

python x_media_scraper.py --user jack --cookies /path/to/cookies.txt

What you’ll get

downloads/
  <username>/
    images/
      184732874827_photo1.jpg
      ...
    videos/
      184732874827-<yt-dlp-id>.mp4
    <username>.json
    <username>.jsonl

Why this approach?

snscrape: pulls posts reliably with no official API or Selenium scrolling headaches.

yt-dlp: robust for extracting the best video stream from tweet URLs.

requests: direct, fast image downloads.

Resumable: re-runs won’t waste time or re-download existing media.

# optional filters
python x_media_scraper.py --user jack --since 2024-01-01 --limit 0

User enters a handle (or pass --user on CLI).



It pulls every post (optionally since a date or with a limit).

Downloads all images to downloads/<username>/images/.

Downloads all videos/GIFs to downloads/<username>/videos/ using yt-dlp.

Writes tweet text + metadata to downloads/<username>/<username>.json (and a JSONL too).

Safe to re-run; it skips files that already exist.

No browser automation needed (so “auto-scroll” is handled by the scraper, not a GUI).



python x_media_scraper.py --user jack --cookies /path/to/cookies.txt
