# -*- coding: utf-8 -*-
"""
3_generate_reply.py
===================
المرحلة 3 من مشروع "نبض الإنماء" — عرض حي لتوليد الردود، مناسب للتسجيل المباشر.

المنطق الكامل (الطبقات الثلاث + القوالب) موجود في reply_engine.py
حتى تستخدمه اللوحة app.py أيضًا بدون تكرار.

هذا السكربت يستخدم generate_reply_live() التي تطبع:
  1) أثرًا تفصيليًا لفحص كل طبقة (هل مفتاح Groq/Gemini موجود؟)
  2) الرد وهو يُكتب كلمة بكلمة أمامك — بثّ حقيقي (token-by-token) من النموذج
     إن توفّر مفتاح مجاني، وإلا عرض تدريجي واضح المصدر للقالب الجاهز.

طريقة التشغيل (يولّد ردودًا حية لأعلى 3 تقييمات أولوية):
    python 3_generate_reply.py
"""

import os
import sys
import pandas as pd
from reply_engine import generate_reply_live, active_tier_name

# نجبر الطرفية على UTF-8 حتى تظهر العربية بشكل صحيح أثناء التسجيل
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _demo():
    """عرض حي: توليد ردود لأعلى 3 تقييمات أولوية من ملف التصنيف، مع بث الكتابة أمام الكاميرا."""
    path = os.path.join("data", "alinma_reviews_categorized.csv")
    if not os.path.exists(path):
        print("⚠️  شغّل أولًا: python 2_categorize.py")
        return

    df = pd.read_csv(path)
    top = df.head(3)

    print("=" * 64)
    print("  نبض الإنماء — توليد ردود مقترحة (متوافقة مع الشريعة)")
    print("=" * 64)
    print(f"الطبقة الافتراضية حاليًا: {active_tier_name()}\n")

    for i, (_, r) in enumerate(top.iterrows(), 1):
        print(f"═══ مثال {i} من {len(top)} " + "═" * 40)
        print(f"التطبيق   : {r['app']}")
        print(f"التقييم   : {r['rating']}★  |  التصنيف: {r['category']}  |  الأولوية: {r['priority_score']}")
        print(f"نص العميل : {str(r['text'])[:120]}")
        print()
        reply, source = generate_reply_live(r["text"], r["category"], r.get("language", "ar"))
        print(f"✅ اكتمل الرد ({len(reply)} حرفًا) عبر: {source}")
        print("-" * 64)
        print()


if __name__ == "__main__":
    _demo()
