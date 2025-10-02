#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from subprocess import run, CalledProcessError

TOTAL_PAGES = 604  # إجمالي صفحات المصحف
IMAGE_URL_TMPL = "https://raw.githubusercontent.com/batoulapps/quran-svg/refs/heads/main/svg/{num:03d}.svg"

IMAGE_DIR = Path("quran-pages")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

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
    """إعداد Git LFS لتتبع ملفات SVG"""
    try:
        # تأكد من تثبيت Git LFS
        run(["git", "lfs", "install"], check=True)
        
        # تأكد من أن .gitattributes مضبوط لملفات SVG
        gitattributes = Path(".gitattributes")
        lfs_pattern = "*.svg filter=lfs diff=lfs merge=lfs -text"
        
        if gitattributes.exists():
            content = gitattributes.read_text()
            if "*.svg" not in content:
                # إضافة pattern لملفات SVG
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

print(f"بدء تحميل صفحات المصحف الكاملة ({TOTAL_PAGES} صفحة)...")

# تنزيل جميع صفحات المصحف
for page_num in range(1, TOTAL_PAGES + 1):
    img_url = IMAGE_URL_TMPL.format(num=page_num)
    img_path = IMAGE_DIR / f"page-{page_num:03d}.svg"

    print(f"\n=== صفحة {page_num:03d} ===")
    if download_file(img_url, img_path): 
        changed = True
        
    # إظهار تقدم كل 50 صفحة
    if page_num % 50 == 0:
        print(f"\n📊 تم تحميل {page_num} من {TOTAL_PAGES} صفحة...")

if not changed:
    print(f"\nNo changes detected. All {TOTAL_PAGES} pages are up to date.")
    exit(0)

# --- git add + commit + push مع remote معدل باستخدام GITHUB_TOKEN ---
repo = os.getenv("GITHUB_REPOSITORY")   # مثال: user/repo
token = os.getenv("GITHUB_TOKEN")
branch = os.getenv("GITHUB_REF_NAME", "main").replace("refs/heads/", "")

remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"

try:
    # إعداد الريموت
    run(["git", "remote", "set-url", "origin", remote_url], check=True)

    # إضافة الملفات
    run(["git", "add", "quran-pages/", ".gitattributes"], check=True)

    # إنشاء الكوميت (لو في تغييرات فقط)
    msg = f"chore: sync complete Quran pages ({TOTAL_PAGES} pages)"
    commit_result = run(["git", "commit", "-m", msg])
    if commit_result.returncode != 0:
        print("\n[-] No new commit created (probably no changes). Exiting.")
        exit(0)

    # سحب آخر تغييرات من الريموت قبل البوش عشان نتجنب التضارب
    run(["git", "pull", "--rebase", "origin", branch], check=True)

    # رفع الكوميت
    run(["git", "push", "origin", branch], check=True)
    print(f"\n✅ Quran pages ({TOTAL_PAGES} pages) committed and pushed successfully.")

except CalledProcessError as e:
    print(f"\n[!] Git operation failed: {e}")
    exit(2)
