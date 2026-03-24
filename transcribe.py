import os
import urllib.request
import xml.etree.ElementTree as ET
import whisper
import re
from datetime import datetime

RSS_URL = "https://anchor.fm"
TRACKER_FILE = "last_episode.txt"
TRANSCRIPT_DIR = "transcripts"

def run():
    # 1. Fetch RSS and parse
    print("Checking RSS feed...")
    with urllib.request.urlopen(RSS_URL) as response:
        root = ET.fromstring(response.read().decode('utf-8'))

    latest_item = root.find(".//item")
    mp3_url = latest_item.find("enclosure").attrib["url"]
    title = latest_item.find("title").text

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

    # 3. Process new episode
    print(f"New episode found: {title}")
    print("Downloading MP3...")
    urllib.request.urlretrieve(mp3_url, "podcast.mp3")

    # 4. Transcribe (Using 'small' model on CPU)
    print("Loading Whisper 'small' model (CPU)...")
    model = whisper.load_model("small") 
    print("Starting transcription (this takes 45-60 mins)...")
    result = model.transcribe("podcast.mp3", verbose=True)

    # 5. Save with Date
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

    print(f"Success! Saved to {file_path}")

if __name__ == "__main__":
    run()
