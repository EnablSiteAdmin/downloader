import os
import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime

RSS_URL = "https://anchor.fm/s/f7cac464/podcast/rss"
TRACKER_FILE = "last_episode.txt"
TRANSCRIPT_DIR = "transcripts"

def run():
    # 1. Fetch RSS
    print("Checking RSS feed...")
    with urllib.request.urlopen(RSS_URL) as response:
        rss_content = response.read()
    root = ET.fromstring(rss_content)
    channel = root.find("channel")
    items = channel.findall("item")
    latest = items[0]
    title = latest.find("title").text
    enclosure = latest.find("enclosure")
    mp3_url = enclosure.attrib["url"]
    print(f"Title: {title}")
    print(f"MP3 URL: {mp3_url}")

    # 2. Handle tracker file
    if not os.path.exists(TRACKER_FILE):
        print(f"Initial run: Creating {TRACKER_FILE}")
        with open(TRACKER_FILE, "w") as f:
            f.write("")
    with open(TRACKER_FILE, "r") as f:
        last_url = f.read().strip()

    # ✅ Early exit BEFORE any heavy imports or downloads
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
    with urllib.request.urlopen(req_mp3) as response:
        with open("podcast.mp3", "wb") as f:
            f.write(response.read())
    print("Download complete.")

    # 4. Lazy import + load faster-whisper only when needed
    print("Loading Whisper 'small' model (CPU)...")
    from faster_whisper import WhisperModel  # noqa: PLC0415 — intentional lazy import
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)

    print("Starting transcription...")
    segments, info = model.transcribe("podcast.mp3")

    # 5. Save transcript
    if not os.path.exists(TRANSCRIPT_DIR):
        os.makedirs(TRANSCRIPT_DIR)
    today = datetime.now().strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    file_name = f"{today}_{safe_title}.txt"
    file_path = os.path.join(TRANSCRIPT_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        for segment in segments:
            f.write(segment.text + "\n")

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