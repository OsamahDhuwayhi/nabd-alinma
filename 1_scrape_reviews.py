# -*- coding: utf-8 -*-
"""
1_scrape_reviews.py
===================
المرحلة 1 من مشروع "نبض الإنماء".
الهدف: سحب تقييمات تطبيقات مصرف الإنماء الأربعة من متجر جوجل بلاي (مجانًا 100%).

- المصدر: بيانات عامة من Google Play (لا توجد بيانات سرية أو خاضعة لاتفاقية).
- المخرجات: ملف alinma_reviews_raw.csv داخل مجلد data/.
- الأعمدة: app, app_id, play_store_url, review_id, user_name, rating, text,
  language, date, thumbs_up, replied
  (app_id و play_store_url يتيحان التحقق اليدوي من أي تقييم عبر فتح صفحة
  التطبيق الحقيقية على جوجل بلاي والبحث عن نص التقييم فيها)

طريقة التشغيل:
    python 1_scrape_reviews.py
"""

import os
import re
import sys
import time
import pandas as pd
from google_play_scraper import Sort, reviews

# نجبر الطرفية على استخدام UTF-8 دائمًا، بغض النظر عن ترميز النظام الافتراضي
# (على ويندوز غالبًا cp1252/cp1256)، حتى تظهر النصوص العربية بشكل صحيح أثناء
# التسجيل المباشر لعملية السحب.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# نمط للتعرف على الحروف العربية (النطاق اليونيكودي للعربية 0600-06FF)
ARABIC_RE = re.compile(r"[؀-ۿ]")
LATIN_RE = re.compile(r"[A-Za-z]")


# ========================= الإعدادات =========================
COUNTRY = "sa"                 # السوق المستهدف: السعودية
LANGS = ["ar", "en"]           # اللغتان: العربية والإنجليزية
REVIEWS_PER_APP_LANG = 300     # عدد التقييمات لكل تطبيق ولكل لغة (~300)
SLEEP_BETWEEN = 2              # مهلة بالثواني بين كل طلب (لتجنب الحظر)

# مجلد ومسار الحفظ
DATA_DIR = "data"
OUTPUT_CSV = os.path.join(DATA_DIR, "alinma_reviews_raw.csv")

# تطبيقات الإنماء الأربعة (معرفات جوجل بلاي الحقيقية والموثقة)
ALINMA_APPS = {
    "Alinma App (Main)":       "com.alinma.retail.mobile.v4",
    "AlinmaPay (Wallet)":      "com.alinma.pay.consumer",
    "Alinma Business":         "com.alinma.cib.mobile",
    "Alinma Capital (Invest)": "com.alinma.investment.mobile",
}


def detect_language(text, fallback):
    """
    تحديد لغة التقييم: عربي (ar) أو إنجليزي (en).
    نعتمد على نوع الحروف (عربية أم لاتينية) لأنه أدق بكثير من مكتبات
    كشف اللغة مع النصوص القصيرة، والتي كثيرًا ما تخلط بين العربية
    والفارسية والأردية وغيرها. عند عدم وجود حروف واضحة نُرجع لغة الطلب.
    """
    if not text or not text.strip():
        return fallback
    # إذا احتوى النص على أي حرف عربي نعتبره عربيًا
    if ARABIC_RE.search(text):
        return "ar"
    # إذا احتوى على حروف لاتينية نعتبره إنجليزيًا
    if LATIN_RE.search(text):
        return "en"
    return fallback


def scrape_one_app(app_name, app_id, live=True):
    """
    سحب تقييمات تطبيق واحد بكل اللغات المطلوبة، وإرجاع قائمة صفوف.
    live=True: يطبع كل تقييم فور استلامه (معرّفه الحقيقي من جوجل + نص مختصر)
    ليكون السحب مرئيًا بالكامل أثناء التسجيل المباشر — دليل تقني أن البيانات حقيقية.
    """
    rows = []
    for lang in LANGS:
        print(f"   ↳ اللغة {lang} ...")
        try:
            # نطلب أحدث التقييمات (NEWEST) بعدد محدد
            result, _ = reviews(
                app_id,
                lang=lang,
                country=COUNTRY,
                sort=Sort.NEWEST,
                count=REVIEWS_PER_APP_LANG,
            )
            for i, r in enumerate(result, 1):
                text = r.get("content") or ""
                review_id = r.get("reviewId")
                rating = r.get("score")
                thumbs = r.get("thumbsUpCount", 0)
                rows.append({
                    "platform":   "Google Play",
                    "app":        app_name,
                    # معرّف التطبيق الحقيقي على جوجل بلاي (package name) — يُستخدم
                    # للتحقق اليدوي من أي تقييم عبر فتح صفحة التطبيق الفعلية.
                    "app_id":     app_id,
                    "play_store_url": f"https://play.google.com/store/apps/details?id={app_id}",
                    "review_id":  review_id,
                    "user_name":  r.get("userName"),
                    "rating":     rating,
                    "text":       text,
                    "language":   detect_language(text, lang),
                    "date":       r.get("at"),
                    "thumbs_up":  thumbs,
                    # يُعتبر "مُجاب عليه" إذا كان هناك رد رسمي من المصرف
                    "replied":    (r.get("repliedAt") is not None) or bool(r.get("replyContent")),
                })
                if live:
                    snippet = " ".join(text.split())[:60] or "(بدون نص)"
                    stars = "★" * int(rating or 0)
                    # نطبع معرّف المراجعة الحقيقي الصادر من جوجل (وليس مولَّدًا محليًا)
                    print(f"      [{i:>3}] id={review_id[:18]}... {stars:<5} "
                          f"👍{thumbs:<3} | {snippet}")
            print(f"      ✅ تم سحب {len(result)} تقييم حقيقي للغة {lang}")
        except Exception as e:
            # نتعامل مع كل خطأ (مثل حظر المعدل) دون إيقاف البرنامج
            print(f"      ❌ فشل: {e}")
        time.sleep(SLEEP_BETWEEN)   # مهلة قصيرة لتجنب حظر المعدل
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description="سحب تقييمات تطبيقات الإنماء من جوجل بلاي")
    parser.add_argument("--quiet", action="store_true",
                        help="عدم طباعة كل تقييم على حدة أثناء السحب (وضع مختصر)")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 64)
    print("  نبض الإنماء — سحب تقييمات تطبيقات مصرف الإنماء من جوجل بلاي")
    print("=" * 64)
    if not args.quiet:
        print("  (وضع العرض الحي مفعّل: سيظهر كل تقييم فور استلامه من جوجل بلاي)")

    all_rows = []
    for app_name, app_id in ALINMA_APPS.items():
        print(f"\n📱 {app_name}  ({app_id})")
        all_rows.extend(scrape_one_app(app_name, app_id, live=not args.quiet))

    # إذا لم نحصل على أي بيانات (مثلاً لا يوجد إنترنت)، نوقف بوضوح
    if not all_rows:
        print("\n⚠️  لم يتم سحب أي تقييمات. تحقق من الاتصال بالإنترنت ثم أعد المحاولة.")
        sys.exit(1)

    df = pd.DataFrame(all_rows)

    # إزالة التكرار (قد يظهر نفس التقييم في طلبَي العربية والإنجليزية)
    before = len(df)
    df = df.drop_duplicates(subset=["review_id"]).reset_index(drop=True)
    print(f"\n🧹 إزالة التكرار: {before} ← {len(df)} تقييم فريد")

    # الحفظ بترميز utf-8-sig ليظهر العربي بشكل صحيح في Excel
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # ========================= الملخص =========================
    print("\n" + "=" * 64)
    print("  الملخص")
    print("=" * 64)

    print("\nعدد التقييمات لكل تطبيق:")
    print(df["app"].value_counts().to_string())

    print("\nعدد التقييمات لكل لغة:")
    print(df["language"].value_counts().to_string())

    replied_rate = df["replied"].mean() * 100
    avg_rating = df["rating"].mean()

    print(f"\nإجمالي التقييمات الفريدة : {len(df)}")
    print(f"متوسط التقييم           : {avg_rating:.2f} / 5")
    print(f"نسبة الردود من المصرف    : {replied_rate:.1f}%   (كلما قلّت زادت أهمية الأداة)")
    print(f"\n✅ تم الحفظ في: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
