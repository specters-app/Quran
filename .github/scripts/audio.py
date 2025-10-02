#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from subprocess import run, CalledProcessError

# كل القراء / السيرفرات
READERS = {
    "hazza": "https://server11.mp3quran.net/download/hazza/{num}.mp3", 
    "husr":  "https://server13.mp3quran.net/download/husr/{num}.mp3",
    "sds":   "https://server11.mp3quran.net/download/sds/{num}.mp3",
    "basit": "https://server7.mp3quran.net/download/basit/{num}.mp3",
    "jleel": "https://server10.mp3quran.net/download/jleel/{num}.mp3"
}

TOTAL = 114
changed = False

def download_file(url: str, path: Path) -> bool:
    """تحميل الملف وحفظه، يرجع True لو الملف اتغير أو اتضاف جديد."""
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        content = r.content
        if not path.exists() or path.read_bytes() != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            print(f"[+] {path} updated ({len(content)} bytes)")
            return True
        else:
            print(f"[-] {path} unchanged")
            return False
    except Exception as e:
        print(f"[!] Failed {url} → {e}")
        return False

def setup_git_lfs():
    """إعداد Git LFS لتتبع ملفات MP3"""
    try:
        run(["git", "lfs", "install"], check=True)
        gitattributes = Path(".gitattributes")
        lfs_pattern = "*.mp3 filter=lfs diff=lfs merge=lfs -text"
        
        if gitattributes.exists():
            content = gitattributes.read_text()
            if "*.mp3" not in content:
                with open(gitattributes, "a") as f:
                    f.write(f"\n{lfs_pattern}\n")
        else:
            gitattributes.write_text(lfs_pattern)
        
        run(["git", "add", ".gitattributes"], check=True)
        print("[+] Git LFS setup completed")
    except Exception as e:
        print(f"[!] Git LFS setup failed: {e}")

# --- MAIN ---
setup_git_lfs()

# تنزيل الصوت لكل سورة من كل سيرفر
for reader, url_tmpl in READERS.items():
    print(f"\n=== 📥 Reader: {reader} ===")
    reader_dir = Path("audio") / reader
    
    for i in range(1, TOTAL + 1):
        num = f"{i:03d}"
        aud_url = url_tmpl.format(num=num)
        aud_path = reader_dir / f"{num}.mp3"

        print(f"--- سورة {num} ---")
        if download_file(aud_url, aud_path):
            changed = True

if not changed:
    print("\nNo changes detected. Exiting without commit.")
    exit(0)

# --- git add + commit + push ---
repo = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")
branch = os.getenv("GITHUB_REF_NAME", "main").replace("refs/heads/", "")

remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"

try:
    run(["git", "remote", "set-url", "origin", remote_url], check=True)

    # إضافة كل الملفات المتغيرة والجديدة
    run(["git", "add", "-A"], check=True)

    msg = f"chore: sync Quran audio ({TOTAL} surahs × {len(READERS)} readers)"
    commit_result = run(["git", "commit", "-m", msg])
    if commit_result.returncode != 0:
        print("\n[-] No new commit created (probably no changes). Exiting.")
        exit(0)

    # تحديث الريبو قبل البوش
    run(["git", "pull", "--rebase", "origin", branch], check=True)

    # رفع الكوميت
    run(["git", "push", "origin", branch], check=True)
    print("\n✅ Audio files committed and pushed successfully with Git LFS.")

except CalledProcessError as e:
    print(f"\n[!] Git operation failed: {e}")
    exit(2)
