# -*- coding: utf-8 -*-
"""
2_categorize.py
===============
المرحلة 2 من مشروع "نبض الإنماء".
الهدف: تصنيف التقييمات إلى مواضيع ألم (Pain Themes) وحساب درجة أولوية لكل تقييم.

المدخلات : data/alinma_reviews_raw.csv
المخرجات : data/alinma_reviews_categorized.csv

الطريقة الافتراضية: تصنيف بالكلمات المفتاحية (سريع جدًا، بدون إنترنت، بدون تكلفة).
ترقية اختيارية مجانية بالتعلّم الآلي (تعمل محليًا بدون أي تكلفة):
    python 2_categorize.py --ml
(تحتاج تثبيت: pip install sentence-transformers)

طريقة التشغيل العادية:
    python 2_categorize.py
"""

import os
import re
import sys
import argparse
import pandas as pd

# ملفات المدخلات والمخرجات
DATA_DIR = "data"
INPUT_CSV = os.path.join(DATA_DIR, "alinma_reviews_raw.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "alinma_reviews_categorized.csv")


# ==================== تطبيع النص العربي ====================
# نزيل التشكيل ونوحّد أشكال الحروف حتى تتطابق الكلمات المفتاحية بسهولة.
_TASHKEEL = re.compile(r"[ؗ-ًؚ-ْـ]")  # تشكيل + تطويل


def normalize(text):
    """توحيد النص: حروف صغيرة + إزالة التشكيل + توحيد الألف والتاء المربوطة."""
    t = str(text).lower()
    t = _TASHKEEL.sub("", t)
    t = (t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
           .replace("ة", "ه").replace("ى", "ي")
           .replace("ؤ", "و").replace("ئ", "ي"))
    return t


# ==================== قواميس الكلمات المفتاحية ====================
# كل موضوع ألم وله قائمة كلمات (عربية + إنجليزية) بصيغتها بعد التطبيع.
# الترتيب مهم: عند تساوي عدد التطابقات يفوز الموضوع الأعلى في القائمة.
PROBLEM_KEYWORDS = {
    "تحويلات عالقة": [
        "تحويل", "تحويلات", "حواله", "حوالات", "تحويله", "عالق", "معلق",
        "علق", "تاخر", "تاخير", "ماوصل", "ما وصل", "لم تصل", "لم يصل",
        "ما وصلت", "مو واصل", "ايبان",
        "transfer", "transaction", "remittance", "didn't arrive",
        "not arrive", "pending", "stuck money", "sent money",
    ],
    "مشاكل تسجيل الدخول": [
        "تسجيل الدخول", "تسجيل دخول", "الدخول", "ما يفتح", "لا يفتح",
        "مايفتح", "رمز التحقق", "كلمه المرور", "كلمه السر", "الرمز",
        "بصمه", "نسيت", "ما اقدر ادخل", "لا استطيع الدخول", "تسجيل",
        "login", "log in", "sign in", "password", "otp", "can't log",
        "cannot log", "can't open", "cannot open", "won't open",
        "face id", "fingerprint", "verification code",
    ],
    "أعطال تقنية": [
        "يتوقف", "توقف", "يعلق", "يهنق", "يهنج", "تحديث", "خطا",
        "يطلع خطا", "مشكله تقنيه", "لا يعمل", "ما يعمل", "مايشتغل",
        "ما يشتغل", "يقفل", "يسكر", "ثقيل", "يعلق التطبيق", "لا يحمل",
        "crash", "bug", "error", "not working", "doesn't work",
        "does not work", "freeze", "glitch", "keeps closing",
        "force close", "laggy",
    ],
    "دعم بطيء": [
        "خدمه العملاء", "الدعم", "دعم", "لا يردون", "ما يردون", "ما يرد",
        "لا يرد", "ما احد يرد", "تجاوب", "لا تجاوب", "اتصلت", "بطيء الرد",
        "انتظار", "الكول سنتر", "تواصلت", "ما في رد",
        "customer service", "support", "no response", "no reply",
        "slow response", "call center", "never answer", "no answer",
        "contact them",
    ],
    "رسوم مرتفعة": [
        "رسوم", "رسم", "عموله", "عمولات", "خصم", "خصمو", "خصمت",
        "خصومات", "غاليه", "غالي", "مرتفعه", "مرتفع", "اشتراك", "تكلفه",
        "fee", "fees", "charge", "charges", "commission", "expensive",
        "deducted", "hidden fee", "subscription",
    ],
}

# كلمات إيجابية (للثناء والرضا)
POSITIVE_KEYWORDS = [
    "ممتاز", "رائع", "شكرا", "افضل", "احسن", "جميل", "سهل", "حلو",
    "تمام", "سريع", "راقي", "يعطيكم العافيه", "مشكورين", "تسلمون",
    "بنك ممتاز", "تطبيق ممتاز",
    "great", "excellent", "good", "love", "easy", "perfect",
    "awesome", "nice", "best bank", "thank you", "amazing", "smooth",
]

CAT_POSITIVE = "إيجابي"
CAT_OTHER = "أخرى"


def categorize(text, rating):
    """
    تصنيف تقييم واحد إلى موضوع ألم أو إيجابي أو أخرى.
    المنطق:
      1) نحسب عدد الكلمات المطابقة لكل موضوع مشكلة.
      2) إن لم تظهر أي كلمة مشكلة → إيجابي (لو التقييم عالٍ أو فيه ثناء) وإلا أخرى.
      3) إن ظهرت كلمات مشكلة → نأخذ الموضوع الأكثر تطابقًا،
         إلا إذا كان التقييم عاليًا والثناء أوضح من الشكوى فيكون إيجابيًا.
    """
    t = normalize(text)

    # عدد التطابقات لكل موضوع مشكلة
    scores = {cat: sum(1 for kw in kws if kw in t)
              for cat, kws in PROBLEM_KEYWORDS.items()}
    best_cat = max(scores, key=scores.get)
    best_score = scores[best_cat]

    # عدد الكلمات الإيجابية
    pos_score = sum(1 for kw in POSITIVE_KEYWORDS if kw in t)

    if best_score == 0:
        # لا توجد شكوى واضحة: نعتبره إيجابيًا فقط إذا كان التقييم جيدًا (4 أو 5)
        if rating >= 4:
            return CAT_POSITIVE
        return CAT_OTHER

    # توجد كلمات شكوى — لكن قد يكون تقييمًا عاليًا مع ثناء أقوى
    if rating >= 4 and pos_score > best_score:
        return CAT_POSITIVE
    return best_cat


def compute_priority(row):
    """
    درجة الأولوية = (6 - التقييم) × (معامل عدم الرد) × (تأثير الإعجابات)
      - كلما قلّ التقييم زادت الأولوية.
      - التقييم غير المُجاب عليه أهم بخمس مرات من المُجاب عليه.
      - كل إعجاب (thumbs up) يرفع الأهمية قليلًا (يعني الناس توافق الشكوى).
    """
    rating = row["rating"]
    not_replied_factor = 1.0 if not row["replied"] else 0.2
    thumbs = row.get("thumbs_up", 0) or 0
    return (6 - rating) * not_replied_factor * (1 + thumbs * 0.1)


def load_data():
    """قراءة ملف التقييمات الخام مع ضبط عمود replied ليكون قيمة منطقية."""
    if not os.path.exists(INPUT_CSV):
        print(f"⚠️  لم يتم العثور على {INPUT_CSV}. شغّل أولًا: python 1_scrape_reviews.py")
        sys.exit(1)
    df = pd.read_csv(INPUT_CSV)
    # ضمان أن replied قيمة منطقية (True/False) مهما كان شكلها في الملف
    df["replied"] = (df["replied"].astype(str).str.lower()
                     .isin(["true", "1", "yes"]))
    df["thumbs_up"] = pd.to_numeric(df["thumbs_up"], errors="coerce").fillna(0)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(3)
    df["text"] = df["text"].fillna("")
    return df


def add_semantic_clusters(df, n_clusters=6):
    """
    ترقية اختيارية مجانية: تجميع دلالي بنموذج يعمل محليًا (بدون تكلفة).
    نضيف عمود semantic_cluster. نبقي عمود category (الكلمات المفتاحية) كما هو.
    """
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.cluster import KMeans
    except ImportError:
        print("ℹ️  وضع التعلّم الآلي يتطلب: pip install sentence-transformers")
        print("    سيتم التخطي والاكتفاء بالتصنيف بالكلمات المفتاحية.")
        return df

    print("🧠 تحميل النموذج المحلي المجاني (قد يستغرق أول مرة دقيقة)...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    texts = df["text"].astype(str).tolist()
    print("🔢 حساب التمثيلات الدلالية (embeddings)...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)

    print(f"🧩 تجميع إلى {n_clusters} مجموعات دلالية (KMeans)...")
    km = KMeans(n_clusters=n_clusters, random_state=0, n_init=10)
    df["semantic_cluster"] = km.fit_predict(embeddings)

    # طباعة أمثلة من كل مجموعة ليفهم الفريق موضوعها
    print("\nأمثلة من كل مجموعة دلالية:")
    for c in range(n_clusters):
        sample = df[df["semantic_cluster"] == c]["text"].head(2).tolist()
        print(f"  المجموعة {c} ({(df['semantic_cluster'] == c).sum()} تقييم):")
        for s in sample:
            print(f"    - {str(s)[:70]}")
    return df


def main():
    parser = argparse.ArgumentParser(description="تصنيف تقييمات الإنماء وحساب الأولوية")
    parser.add_argument("--ml", action="store_true",
                        help="تفعيل التجميع الدلالي المجاني بالتعلّم الآلي")
    args = parser.parse_args()

    df = load_data()

    print("=" * 64)
    print("  نبض الإنماء — تصنيف التقييمات وحساب الأولوية")
    print("=" * 64)

    # 1) التصنيف بالكلمات المفتاحية (الافتراضي)
    df["category"] = df.apply(lambda r: categorize(r["text"], r["rating"]), axis=1)

    # 2) درجة الأولوية
    df["priority_score"] = df.apply(compute_priority, axis=1).round(2)

    # 3) ترتيب تنازلي حسب الأولوية
    df = df.sort_values("priority_score", ascending=False).reset_index(drop=True)

    # 4) الترقية الاختيارية بالتعلّم الآلي
    if args.ml:
        df = add_semantic_clusters(df)

    # حفظ الناتج
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # ==================== الملخص ====================
    print("\nتوزيع المواضيع (Pain Themes):")
    print(df["category"].value_counts().to_string())

    print("\nأعلى 10 تقييمات أولوية (طابور المعالجة):")
    top = df.head(10)
    for _, r in top.iterrows():
        flag = "لم يُرد عليه" if not r["replied"] else "تم الرد"
        print(f"  [{r['priority_score']:.2f}] {r['rating']}★ {r['category']} "
              f"| {flag} | {str(r['text'])[:55]}")

    print(f"\n✅ تم الحفظ في: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
