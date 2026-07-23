"""
اسکریپت دانلود تصاویر و جایگزینی لینک‌ها در فایل‌های Markdown
------------------------------------------------------------
این اسکریپت روی پوشه‌ی docs (که از zip استخراج کردی) اجرا می‌شه.
کارهایی که انجام می‌ده:
  1. توی همه‌ی فایل‌های .md دنبال لینک‌های ![...](https://dotnettutorials.net/...) می‌گرده.
  2. هر تصویر رو دانلود می‌کنه و کنار همون فایل md، توی یک پوشه‌ی images/ ذخیره می‌کنه.
  3. لینک تصویر رو توی متن MD با مسیر لوکال (نسبی) جایگزین می‌کنه.

نحوه‌ی اجرا:
  1. پایتون ۳ باید نصب باشه.
  2. کتابخونه‌ی requests رو نصب کن:
         pip install requests
  3. مسیر پوشه‌ی docs رو (که از zip استخراج کردی) به عنوان آرگومان بده:
         python download_images.py "C:\path\to\docs"
     یا اگه اسکریپت رو داخل همون پوشه‌ی docs کپی کنی، بدون آرگومان هم اجرا میشه
     (پیش‌فرض پوشه‌ی جاری رو می‌گیره).

نکته: اگه یک تصویر دانلود نشد (مثلاً لینک از دسترس خارج شده)، در گزارش پایانی
لیست می‌شه ولی لینک اصلی توی فایل MD دست‌نخورده باقی می‌مونه تا خودت بعداً بررسی کنی.
"""

import os
import re
import sys
import time
import hashlib
from urllib.parse import urlparse, unquote

try:
    import requests
except ImportError:
    print("کتابخانه‌ی requests نصب نیست. اول این دستور رو اجرا کن:\n    pip install requests")
    sys.exit(1)

IMG_MD_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(\s+"[^"]*")?\)')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://dotnettutorials.net/",
}


def safe_filename(url: str) -> str:
    """از URL یک اسم فایل امن و کوتاه می‌سازه."""
    path = urlparse(url).path
    name = unquote(os.path.basename(path)) or "image"
    name = re.sub(r'[^\w.\-]+', '_', name)
    # اگه اسم خیلی طولانی بود، کوتاهش کن و یک هش کوچیک بهش اضافه کن تا یکتا بمونه
    if len(name.encode("utf-8")) > 120:
        h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        ext = os.path.splitext(name)[1] or ".png"
        name = f"img_{h}{ext}"
    return name


def download_image(url: str, dest_path: str) -> bool:
    if os.path.exists(dest_path):
        return True
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"    [خطا] دانلود نشد: {url}\n          دلیل: {e}")
        return False


def process_md_file(md_path: str, stats: dict):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = list(IMG_MD_PATTERN.finditer(content))
    external = [m for m in matches if m.group(2).startswith("http")]
    if not external:
        return

    md_dir = os.path.dirname(md_path)
    images_dir = os.path.join(md_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    print(f"\n📄 {md_path}  ({len(external)} تصویر)")

    new_content = content
    seen = {}
    for m in external:
        full_match = m.group(0)
        alt_text = m.group(1)
        url = m.group(2)
        title_part = m.group(3) or ""

        if url in seen:
            local_rel = seen[url]
        else:
            fname = safe_filename(url)
            dest = os.path.join(images_dir, fname)
            ok = download_image(url, dest)
            stats["total"] += 1
            if ok:
                stats["success"] += 1
                local_rel = f"images/{fname}"
                seen[url] = local_rel
                print(f"    ✅ {fname}")
            else:
                stats["failed"].append(url)
                continue  # لینک اصلی دست‌نخورده می‌مونه

        new_full = f"![{alt_text}]({local_rel}{title_part})"
        new_content = new_content.replace(full_match, new_full)

    if new_content != content:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(new_content)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        print(f"پوشه‌ی '{root}' پیدا نشد.")
        sys.exit(1)

    print(f"شروع پردازش پوشه: {root}")
    stats = {"total": 0, "success": 0, "failed": []}

    md_files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".md"):
                md_files.append(os.path.join(dirpath, fn))

    print(f"تعداد فایل‌های MD پیدا شده: {len(md_files)}")

    for md_path in md_files:
        process_md_file(md_path, stats)
        time.sleep(0.05)  # کمی مکث برای رعایت ادب با سرور

    print("\n================ گزارش پایانی ================")
    print(f"کل تصاویر پردازش‌شده: {stats['total']}")
    print(f"دانلود موفق: {stats['success']}")
    print(f"دانلود ناموفق: {len(stats['failed'])}")
    if stats["failed"]:
        print("\nلینک‌هایی که دانلود نشدن:")
        for u in stats["failed"]:
            print(f"  - {u}")


if __name__ == "__main__":
    main()