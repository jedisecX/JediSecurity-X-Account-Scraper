# X (Twitter) Media Scraper

Download **all images and videos** from a public X (Twitter) account and export the **text + metadata** to JSON — no official API keys required.

- ✅ Scrapes posts with **snscrape** (no Selenium needed)
- 🎞️ Saves **videos/GIFs** via **yt-dlp**
- 🖼️ Saves **images** via `requests`
- 🗃️ Organizes everything under `downloads/<username>/{images,videos}/`
- 🧾 Exports `downloads/<username>/<username>.json` (pretty) and `.jsonl` (streaming-friendly)
- ♻️ **Idempotent**: safe to re-run; skips files that already exist
- 🔒 Optional `cookies.txt` support for restricted media (age-gated/region-locked)

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Interactive:
```bash
python x_media_scraper.py
```

Non-interactive:
```bash
python x_media_scraper.py --user jack
```

With filters:
```bash
python x_media_scraper.py --user jack --since 2024-01-01 --limit 500
python x_media_scraper.py --user jack --cookies ./cookies.txt
```

## Output
```
downloads/
  <username>/
    images/
    videos/
    <username>.json
    <username>.jsonl
```

## Legal
For personal archival/research. Respect copyright and terms of service.

