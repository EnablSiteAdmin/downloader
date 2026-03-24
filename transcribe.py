import os
import urllib.request
import xml.etree.ElementTree as ET
import whisper
import re
from datetime import datetime

RSS_URL = "https://anchor.fm/s/f7cac464/podcast/rss"
TRACKER_FILE = "last_episode.txt"
TRANSCRIPT_DIR = "transcripts"

def strip_namespaces(content):
    """Remove all XML namespace declarations and prefixes."""
    # Remove namespace declarations: xmlns:foo="..." and xmlns="..."
    content = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', content)
    # Remove namespace prefixes from tags: <itunes:foo> -> <foo>, </itunes:foo> -> </foo>
    content = re.sub(r'<(/?)[\w]+:([\w]+)', r'<\1\2', content)
    # Remove namespace prefixes from attributes: itunes:foo="bar" -> foo="bar"
    content = re.sub(r'\b[\w]+:([\w]+)="', r'\1="', content)
    return content

def run():
    # 1. Fetch RSS and parse
    print("Checking RSS feed...")
    req = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "Mozilla/5.0 (podcast transcriber)"}
    )
    with urllib.request.urlopen(req) as response:
        content = response.read().decode("utf-8")

    # Strip XML namespace prefixes to simplify parsing
    content = re.sub(r'\sxmlns[^"]*"[^"]*"', '', content)
    root = ET.fromstring(content)

    latest_item = root.find(".//item")
    if latest_item is None:
        print("No items found in RSS feed.")
        return

    enclosure = latest_item.find("enclosure")
    if enclosure is None:
        print("No enclosure (MP3) found in latest item.")
        return

    mp3_url = enclosure.attrib["url"]
    title_el = latest_item.find("title")
    title = title_el.text if title_el is not None else "untitled"

    print(f"Latest episode: {title}")
    print(f"MP3 URL: {mp3_url}")

    # 2. Handle tracker file (Create if missing)
    if not os.path.exists(TRACKER_FILE):
        print(f"Initial run: Creating {TRACKER_FILE}")
        with open(TRACKER_FILE, "w") as f:
            f.write("")

    with open(TRACKER_FILE, "r") as f:
        last_url = f.read().strip()

    if last_url == mp3_url:
        print("No new episodes found. Skipping.")
        return

    # 3. Download new episode
    print(f"New episode found: {title}")
    print("Downloading MP3...")

    req_mp3 = urllib.request.Request(
        mp3_url,
        headers={"User-Agent": "Mozilla/5.0 (podcast transcriber)"}
    )
    # urlretrieve doesn't support custom headers; use urlopen + write manually
    with urllib.request.urlopen(req_mp3) as response:
        with open("podcast.mp3", "wb") as f:
            f.write(response.read())

    print("Download complete.")

    # 4. Transcribe with Whisper 'small' model on CPU
    print("Loading Whisper 'small' model (CPU)...")
    model = whisper.load_model("small")
    print("Starting transcription (this may take 45-60 mins)...")
    result = model.transcribe("podcast.mp3", verbose=True)

    # 5. Save transcript with date + title
    if not os.path.exists(TRANSCRIPT_DIR):
        os.makedirs(TRANSCRIPT_DIR)

    today = datetime.now().strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    file_name = f"{today}_{safe_title}.txt"
    file_path = os.path.join(TRANSCRIPT_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(result["text"])

    # 6. Update tracker
    with open(TRACKER_FILE, "w") as f:
        f.write(mp3_url)

    print(f"Success! Transcript saved to {file_path}")

    # 7. Cleanup
    if os.path.exists("podcast.mp3"):
        os.remove("podcast.mp3")
        print("Cleaned up podcast.mp3")

if __name__ == "__main__":
    run()
