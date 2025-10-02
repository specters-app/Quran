#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from subprocess import run, CalledProcessError

# تعريف جميع القراء مع روابطهم
READERS = {
    "hazza": "https://server11.mp3quran.net/download/hazza/{num}.mp3", 
    "husr": "https://server13.mp3quran.net/download/husr/{num}.mp3",
    "sds": "https://server11.mp3quran.net/download/sds/{num}.mp3",
    "basit": "https://server7.mp3quran.net/download/basit/{num}.mp3",
    "s_gmd": "https://server7.mp3quran.net/download/s_gmd/{num}.mp3",
    "jleel": "https://server10.mp3quran.net/download/jleel/{num}.mp3"
}

TOTAL_SURAH = 114
BASE_AUDIO_DIR = Path("audio")

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

def download_all_readers():
    """تحميل جميع السور لجميع القراء"""
    global changed
    
    for reader_name, url_template in READERS.items():
        reader_dir = BASE_AUDIO_DIR / reader_name
        reader_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*50}")
        print(f"تحميل القرآن الكريم للقارئ: {reader_name}")
        print(f"{'='*50}")
        
        for surah_num in range(1, TOTAL_SURAH + 1):
            num = f"{surah_num:03d}"
            audio_url = url_template.format(num=num)
            audio_path = reader_dir / f"{num}.mp3"

            print(f"\n=== سورة {surah_num:03d} - {reader_name} ===")
            if download_file(audio_url, audio_path): 
                changed = True

# إعداد Git LFS أولاً
setup_git_lfs()

# تحميل جميع القراء
download_all_readers()

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

    # إضافة جميع المجلدات والملفات
    run(["git", "add", "audio/", ".gitattributes"], check=True)

    # إنشاء الكوميت
    msg = f"chore: sync Quran audio for all readers ({len(READERS)} readers, {TOTAL_SURAH} surahs each)"
    commit_result = run(["git", "commit", "-m", msg])
    if commit_result.returncode != 0:
        print("\n[-] No new commit created (probably no changes). Exiting.")
        exit(0)

    # سحب آخر تغييرات من الريموت قبل البوش
    run(["git", "pull", "--rebase", "origin", branch], check=True)

    # رفع الكوميت
    run(["git", "push", "origin", branch], check=True)
    print(f"\n✅ Audio files for {len(READERS)} readers committed and pushed successfully with Git LFS.")

except CalledProcessError as e:
    print(f"\n[!] Git operation failed: {e}")
    exit(2)
