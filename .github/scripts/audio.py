#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from subprocess import run, CalledProcessError

TOTAL = 114
AUDIO_URL_TMPL = "https://server6.mp3quran.net/download/abkr/{num}.mp3"
AUDIO_DIR = Path("audio/abkr")
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

def setup_git_lfs():
    """إعداد Git LFS لتتبع ملفات MP3"""
    try:
        # تأكد من تثبيت Git LFS
        run(["git", "lfs", "install"], check=True)
        
        # تأكد من أن .gitattributes مضبوط لملفات MP3
        gitattributes = Path(".gitattributes")
        lfs_pattern = "*.mp3 filter=lfs diff=lfs merge=lfs -text"
        
        if gitattributes.exists():
            content = gitattributes.read_text()
            if "*.mp3" not in content:
                # إضافة pattern لملفات MP3
                with open(gitattributes, "a") as f:
                    f.write(f"\n{lfs_pattern}\n")
        else:
            # إنشاء ملف .gitattributes جديد
            gitattributes.write_text(lfs_pattern)
        
        # إضافة .gitattributes إلى Git
        run(["git", "add", ".gitattributes"], check=True)
        
        print("[+] Git LFS setup completed")
        
    except Exception as e:
        print(f"[!] Git LFS setup failed: {e}")

# إعداد Git LFS أولاً
setup_git_lfs()

# تنزيل الصوت لكل سورة
for i in range(1, TOTAL + 1):
    num = f"{i:03d}"
    aud_url = AUDIO_URL_TMPL.format(num=num)
    aud_path = AUDIO_DIR / f"{num}.mp3"

    print(f"\n=== سورة {num} ===")
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
    # إعداد الريموت
    run(["git", "remote", "set-url", "origin", remote_url], check=True)

    # إضافة الملفات باستخدام Git LFS
    run(["git", "add", "audio/abkr/", ".gitattributes"], check=True)

    # إنشاء الكوميت
    msg = f"chore: sync Quran audio ({TOTAL} surahs)"
    commit_result = run(["git", "commit", "-m", msg])
    if commit_result.returncode != 0:
        print("\n[-] No new commit created (probably no changes). Exiting.")
        exit(0)

    # سحب آخر تغييرات من الريموت قبل البوش
    run(["git", "pull", "--rebase", "origin", branch], check=True)

    # رفع الكوميت
    run(["git", "push", "origin", branch], check=True)
    print("\n✅ Audio files committed and pushed successfully with Git LFS.")

except CalledProcessError as e:
    print(f"\n[!] Git operation failed: {e}")
    exit(2)
