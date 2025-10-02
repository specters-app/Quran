#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from subprocess import run, CalledProcessError

TOTAL = 114
AUDIO_URL_TMPL = "https://server6.mp3quran.net/abkr/{num}.mp3"
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url: str, path: Path) -> bool:
    """تحميل الملف وحفظه، يرجع True إذا تم التحميل بنجاح."""
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        content = r.content
        
        # كتابة الملف دائماً (استبدال الملفات التالفة)
        path.write_bytes(content)
        print(f"[+] {path} downloaded ({len(content)} bytes)")
        return True
        
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
                with open(gitattributes, "a") as f:
                    f.write(f"\n{lfs_pattern}\n")
        else:
            gitattributes.write_text(lfs_pattern)
        
        run(["git", "add", ".gitattributes"], check=True)
        print("[+] Git LFS setup completed")
        
    except Exception as e:
        print(f"[!] Git LFS setup failed: {e}")

def clean_audio_directory():
    """تنظيف مجلد audio من الملفات التالفة"""
    print("🧹 تنظيف الملفات الصوتية التالفة...")
    
    # حذف جميع ملفات MP3 التالفة
    for mp3_file in AUDIO_DIR.glob("*.mp3"):
        try:
            mp3_file.unlink()
            print(f"🗑️  تم حذف: {mp3_file.name}")
        except Exception as e:
            print(f"[!] فشل في حذف {mp3_file.name}: {e}")
    
    print("✅ تم تنظيف المجلد")

# تنظيف الملفات التالفة أولاً
clean_audio_directory()

# إعداد Git LFS
setup_git_lfs()

success_count = 0
failed_count = 0

# تنزيل جميع السور من جديد
for i in range(1, TOTAL + 1):
    num = f"{i:03d}"
    aud_url = AUDIO_URL_TMPL.format(num=num)
    aud_path = AUDIO_DIR / f"{num}.mp3"

    print(f"\n=== سورة {num} ===")
    if download_file(aud_url, aud_path):
        success_count += 1
    else:
        failed_count += 1

print(f"\n{'='*50}")
print(f"✅ التحميل الناجح: {success_count} سورة")
print(f"❌ الفاشل: {failed_count} سورة")
print(f"📊 الإجمالي: {TOTAL} سورة")

if success_count == 0:
    print("\n❌ لم يتم تحميل أي ملفات. الخروج بدون commit.")
    exit(1)

# --- git add + commit + push ---
repo = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")
branch = os.getenv("GITHUB_REF_NAME", "main").replace("refs/heads/", "")

remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"

try:
    run(["git", "remote", "set-url", "origin", remote_url], check=True)
    run(["git", "add", "audio/", ".gitattributes"], check=True)

    msg = f"chore: re-download all Quran audio ({success_count}/{TOTAL} surahs)"
    commit_result = run(["git", "commit", "-m", msg])
    
    if commit_result.returncode != 0:
        print("\n[-] No new commit created. Exiting.")
        exit(0)

    run(["git", "pull", "--rebase", "origin", branch], check=True)
    run(["git", "push", "origin", branch], check=True)
    print(f"\n✅ تم رفع {success_count} ملف صوتي بنجاح باستخدام Git LFS.")

except CalledProcessError as e:
    print(f"\n[!] Git operation failed: {e}")
    exit(2)
