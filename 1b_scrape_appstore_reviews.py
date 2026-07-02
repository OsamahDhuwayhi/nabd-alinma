# -*- coding: utf-8 -*-
"""
1b_scrape_appstore_reviews.py
==============================
سحب تقييمات تطبيقات الإنماء الأربعة من Apple App Store، عبر خلاصة (RSS Feed)
مراجعات آبل الرسمية والعامة — نفس فكرة 1_scrape_reviews.py لكن لمنصة iOS.

المصدر: https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/...
هذه خلاصة عامة وموثّقة من آبل نفسها، بدون مفتاح API وبدون بيانات سرية.

⚠️ ملاحظة مهمة وصادقة: خلاصة آبل هذه لا تكشف ما إذا كان المطوّر قد ردّ على
التقييم أم لا (لا يوجد حقل "رد المطوّر" في هذه الواجهة العامة، بعكس جوجل بلاي).
لذلك نضع عمود replied = False لكل الصفوف افتراضيًا مع توضيح أنه "غير معروف"
وليس تأكيدًا فعليًا لعدم الرد — للأمانة العلمية الكاملة.

المخرجات: data/alinma_reviews_appstore_raw.csv
الأعمدة: platform, app, app_id, play_store_url, review_id, user_name, rating,
         text, language, date, thumbs_up, replied

طريقة التشغيل:
    python 1b_scrape_appstore_reviews.py
"""

import os
import re
from datetime import datetime
import sys
import time
import json
import urllib.request
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ARABIC_RE = re.compile(r"[؀-ۿ]")
LATIN_RE = re.compile(r"[A-Za-z]")

DATA_DIR = "data"
OUTPUT_CSV = os.path.join(DATA_DIR, "alinma_reviews_appstore_raw.csv")
COUNTRY = "sa"          # نفس سوق جوجل بلاي (السعودية) لثبات المقارنة
PAGES_PER_APP = 10      # خلاصة آبل تدعم حتى 10 صفحات (~50 مراجعة كحد أقصى غالبًا)
SLEEP_BETWEEN = 1.5

# معرّفات آبل الرقمية الحقيقية (App Store IDs) — تم التحقق منها فعليًا
ALINMA_APPS_IOS = {
    "Alinma App (Main)":       "1668637683",
    "AlinmaPay (Wallet)":      "1492900777",
    "Alinma Business":         "6478849458",
    "Alinma Capital (Invest)": "1550503215",
}


def detect_language(text, fallback="ar"):
    if not text or not text.strip():
        return fallback
    if ARABIC_RE.search(text):
        return "ar"
    if LATIN_RE.search(text):
        return "en"
    return fallback


def fetch_page(app_id, page):
    """يجلب صفحة واحدة من خلاصة مراجعات آبل الرسمية (JSON عام، بدون مفتاح)."""
    url = (f"https://itunes.apple.com/{COUNTRY}/rss/customerreviews/"
           f"id={app_id}/sortby=mostrecent/page={page}/json")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("feed", {}).get("entry", [])


def scrape_one_app(app_name, app_id, live=True):
    """سحب تقييمات تطبيق واحد من App Store عبر عدة صفحات من الخلاصة."""
    rows = []
    seen_ids = set()
    for page in range(1, PAGES_PER_APP + 1):
        try:
            entries = fetch_page(app_id, page)
        except Exception as e:
            print(f"      ❌ فشل في الصفحة {page}: {e}")
            break

        if not entries or (len(entries) == 1 and "im:name" in entries[0]):
            # أول عنصر في أول صفحة أحيانًا يكون معلومات التطبيق نفسه لا مراجعة
            entries = [e for e in entries if "im:rating" in e]

        new_count = 0
        for e in entries:
            if "im:rating" not in e:
                continue
            review_id = e.get("id", {}).get("label", "")
            if review_id in seen_ids:
                continue
            seen_ids.add(review_id)
            new_count += 1

            title = e.get("title", {}).get("label", "") or ""
            content = e.get("content", {}).get("label", "") or ""
            full_text = (title + " — " + content).strip(" —") if title else content
            rating = int(e.get("im:rating", {}).get("label", 0) or 0)
            thumbs = int(e.get("im:voteCount", {}).get("label", 0) or 0)
            user_name = e.get("author", {}).get("name", {}).get("label", "")
            # نوحّد صيغة التاريخ لتطابق صيغة جوجل بلاي (بدون منطقة زمنية في
            # النص) — دمج صيغتين مختلفتين في نفس العمود يُفسد قراءة pandas
            # للتاريخ لاحقًا (خطأ حقيقي واجهناه واكتشفناه أثناء الدمج).
            raw_date = e.get("updated", {}).get("label", "")
            try:
                date = datetime.fromisoformat(raw_date).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                date = raw_date

            rows.append({
                "platform":       "App Store",
                "app":            app_name,
                "app_id":         app_id,
                "play_store_url": f"https://apps.apple.com/{COUNTRY}/app/id{app_id}",
                "review_id":      review_id,
                "user_name":      user_name,
                "rating":         rating,
                "text":           full_text,
                "language":       detect_language(full_text),
                "date":           date,
                "thumbs_up":      thumbs,
                # آبل لا تكشف حالة رد المطوّر عبر هذه الخلاصة العامة — غير معروف
                "replied":        False,
            })
            if live:
                snippet = " ".join(full_text.split())[:60]
                stars = "★" * rating
                print(f"      [{len(rows):>3}] id={review_id:<12} {stars:<5} "
                      f"👍{thumbs:<3} | {snippet}")

        if new_count == 0:
            break  # لا مزيد من المراجعات الجديدة، توقف
        time.sleep(SLEEP_BETWEEN)

    print(f"      ✅ تم سحب {len(rows)} تقييم حقيقي من App Store")
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description="سحب تقييمات تطبيقات الإنماء من Apple App Store")
    parser.add_argument("--quiet", action="store_true", help="عدم طباعة كل تقييم على حدة")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 64)
    print("  نبض الإنماء — سحب تقييمات تطبيقات الإنماء من Apple App Store")
    print("=" * 64)

    all_rows = []
    for app_name, app_id in ALINMA_APPS_IOS.items():
        print(f"\n🍎 {app_name}  (App Store ID: {app_id})")
        all_rows.extend(scrape_one_app(app_name, app_id, live=not args.quiet))

    if not all_rows:
        print("\n⚠️  لم يتم سحب أي تقييمات من App Store.")
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.drop_duplicates(subset=["review_id"]).reset_index(drop=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 64)
    print("  الملخص")
    print("=" * 64)
    print(f"\nإزالة التكرار: {before} ← {len(df)} تقييم فريد")
    print("\nعدد التقييمات لكل تطبيق:")
    print(df["app"].value_counts().to_string())
    print(f"\nمتوسط التقييم: {df['rating'].mean():.2f} / 5")
    print(f"\n✅ تم الحفظ في: {OUTPUT_CSV}")
    print("\n⚠️ ملاحظة: عمود replied لهذه البيانات = False دائمًا لأن خلاصة آبل")
    print("   العامة لا تكشف حالة رد المطوّر — وهذا حد حقيقي من واجهة آبل نفسها.")


if __name__ == "__main__":
    main()
