#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from subprocess import run, CalledProcessError

TOTAL = 114
IMAGE_URL_TMPL = "https://raw.githubusercontent.com/quran/audio.quran.com/refs/heads/master/static/images/titles/{num}.svg"
AUDIO_URL_TMPL = "https://server6.mp3quran.net/abkr/{num}.mp3"

IMAGE_DIR = Path("images")
AUDIO_DIR = Path("audio")

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

changed = False

def download_file(url: str, path: Path) -> bool:
    """تحميل الملف وحفظه، يرجع True لو الملف اتغير أو اتضاف جديد."""
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        content = r.content
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
            print(f"[+] {path} updated ({len(content)} bytes)")
            return True
        else:
            print(f"[-] {path} unchanged")
            return False
    except Exception as e:
        print(f"[!] Failed {url} → {e}")
        return False

# تنزيل الصور والصوت لكل سورة
for i in range(1, TOTAL + 1):
    num = f"{i:03d}"
    img_url = IMAGE_URL_TMPL.format(num=num)
    aud_url = AUDIO_URL_TMPL.format(num=num)
    img_path = IMAGE_DIR / f"{num}.svg"
    aud_path = AUDIO_DIR / f"{num}.mp3"

    print(f"\n=== سورة {num} ===")
    if download_file(img_url, img_path): changed = True
    if download_file(aud_url, aud_path): changed = True

if not changed:
    print("\nNo changes detected. Exiting without commit.")
    exit(0)

# --- git add + commit + push مع remote معدل باستخدام GITHUB_TOKEN ---
repo = os.getenv("GITHUB_REPOSITORY")   # مثال: user/repo
token = os.getenv("GITHUB_TOKEN")
branch = os.getenv("GITHUB_REF_NAME", "main")

remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"

try:
    run(["git", "remote", "set-url", "origin", remote_url], check=True)
    run(["git", "add", "images", "audio"], check=True)
    msg = f"chore: sync Quran assets ({TOTAL} surahs)"
    run(["git", "commit", "-m", msg], check=False)
    run(["git", "push", "origin", branch], check=True)
    print("\n✅ Changes committed and pushed successfully.")
except CalledProcessError as e:
    print(f"\n[!] Git operation failed: {e}")
    exit(2)
