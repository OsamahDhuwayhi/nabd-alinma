# -*- coding: utf-8 -*-
"""
reply_engine.py
===============
محرّك توليد الردود المشترك (يستخدمه 3_generate_reply.py ولوحة app.py معًا).

ثلاث طبقات، تُختار تلقائيًا حسب المتاح:
  الطبقة 1: Groq API (مجاني)   — إذا وُجد GROQ_API_KEY.
  الطبقة 2: Google Gemini (مجاني) — إذا وُجد GEMINI_API_KEY.
  الطبقة 3: قوالب جاهزة (بدون إنترنت/مفتاح) — موجودة دائمًا حتى لا ينكسر العرض.

القاعدة الذهبية: لا نَعِد أبدًا باسترداد أموال، ونوجّه العميل لقناة الشكاوى الرسمية.
"""

import os
import re
import sys
import time

# نحمّل GROQ_API_KEY / GEMINI_API_KEY تلقائيًا من ملف .env المحلي إن وُجد،
# حتى لا تحتاج لضبط متغيرات البيئة يدويًا في كل جلسة طرفية جديدة.
# الملف .env نفسه مُستبعد من git عبر .gitignore فلا يُرفع أي مفتاح بالخطأ.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==================== معلومات قناة الشكاوى الرسمية ====================
COMPLAINTS_PHONE = "8001208000"
COMPLAINTS_EMAIL = "complaints@alinma.com"

# ==================== توجيهات النموذج (System Prompt) ====================
SYSTEM_PROMPT = f"""أنت موظف خدمة عملاء محترف في مصرف الإنماء (بنك سعودي إسلامي متوافق مع الشريعة).
مهمتك كتابة رد رسمي ومهذّب على تقييم عميل نُشر في متجر التطبيقات.

التزم بالقواعد التالية بدقة:
- اكتب بنفس لغة العميل. إذا كان التقييم بالعربية فاكتب بلهجة سعودية مهذّبة ومحترمة.
- ابدأ باعتذار صادق (للشكاوى) أو بشكر لطيف (للثناء) يناسب نبرة التقييم.
- النبرة إسلامية راقية ومحترمة بلا مبالغة.
- ممنوع منعًا باتًا الوعد بأي استرداد للأموال أو تعويض مالي.
- وجّه العميل للقناة الرسمية للشكاوى: الرقم الموحّد {COMPLAINTS_PHONE} أو البريد {COMPLAINTS_EMAIL}.
- اجعل الرد من جملتين إلى ثلاث جمل فقط، مختصرًا ومباشرًا.
- أخرج نص الرد الجاهز للنشر فقط، دون أي مقدمات أو تعليقات أو علامات اقتباس.
- استخدم فقط حروفًا عربية أو إنجليزية أو أرقامًا؛ ممنوع منعًا باتًا إدراج أي حرف
  من أي لغة أخرى (كالصينية أو اليابانية أو الكورية أو الروسية) تحت أي ظرف."""

# نمط يكتشف حروفًا من لغات غير متوقعة (صينية/يابانية/كورية/سيريلية/هندية).
# سبب وجوده: النماذج المجانية أحيانًا "تُلوِّث" الرد العربي بحرف أو كلمة عشوائية
# من لغة أخرى (خلل معروف عند بعض النماذج مفتوحة المصدر عند حرارة توليد أعلى)،
# وهذا كفيل بأن يُفسد عرضًا مباشرًا أمام الحكام لو ظهر دون فحص.
FOREIGN_SCRIPT_RE = re.compile(
    r"[一-鿿぀-ヿ가-힯Ѐ-ӿऀ-ॿ]"
)


def _is_clean(text):
    """يتحقق أن نص الرد خالٍ من حروف لغات غير متوقعة."""
    return bool(text) and not FOREIGN_SCRIPT_RE.search(text)


def _clean_ai_reply(fetch_fn):
    """
    ينفّذ fetch_fn (تُرجع نص رد من نموذج AI) ويتحقق من سلامته.
    عند التلوّث يعيد المحاولة مرة واحدة فقط؛ إن فشلت أيضًا يرفع استثناءً
    لينتقل المستدعي تلقائيًا للطبقة التالية (أو للقالب الجاهز في النهاية).
    """
    text = fetch_fn()
    if _is_clean(text):
        return text
    text2 = fetch_fn()
    if _is_clean(text2):
        return text2
    raise ValueError("تكرر ظهور حروف من لغة غير متوقعة في رد النموذج")


# ==================== الطبقة 3: القوالب الجاهزة (fallback) ====================
# ردود مكتوبة مسبقًا لكل تصنيف، بالعربية والإنجليزية، متوافقة مع الشريعة
# ولا تَعِد باسترداد أموال، وتوجّه دائمًا لقناة الشكاوى.
TEMPLATE_REPLIES = {
    "تحويلات عالقة": {
        "ar": (f"نعتذر إليك عن تأخر تحويلك ونقدّر ثقتك بمصرف الإنماء. "
               f"نأمل تزويدنا بتفاصيل العملية عبر الرقم الموحّد {COMPLAINTS_PHONE} "
               f"أو البريد {COMPLAINTS_EMAIL} لمتابعتها ومعالجتها في أسرع وقت بإذن الله."),
        "en": (f"We sincerely apologize for the delay in your transfer and value your trust in Alinma. "
               f"Please share the transaction details via {COMPLAINTS_PHONE} or "
               f"{COMPLAINTS_EMAIL} so we can follow up and resolve it promptly."),
    },
    "مشاكل تسجيل الدخول": {
        "ar": (f"نأسف لما واجهته في تسجيل الدخول ونشكر لك صبرك. "
               f"يسعدنا مساعدتك والتحقق من حسابك عبر الرقم الموحّد {COMPLAINTS_PHONE} "
               f"أو البريد {COMPLAINTS_EMAIL} لحل المشكلة بإذن الله. تجربتك تهمّنا."),
        "en": (f"We're sorry for the trouble signing in and appreciate your patience. "
               f"Kindly reach us at {COMPLAINTS_PHONE} or {COMPLAINTS_EMAIL} so we can "
               f"verify your account and resolve this for you. Your experience matters to us."),
    },
    "أعطال تقنية": {
        "ar": (f"نعتذر عن العطل الذي واجهك في التطبيق ونقدّر ملاحظتك القيّمة. "
               f"رفعنا الأمر للفريق التقني، ونرجو تزويدنا بنوع جهازك والتفاصيل عبر "
               f"{COMPLAINTS_PHONE} أو {COMPLAINTS_EMAIL} لخدمتك على أكمل وجه."),
        "en": (f"We apologize for the technical issue and truly value your feedback. "
               f"We've raised it with our technical team; please send your device type and "
               f"details to {COMPLAINTS_PHONE} or {COMPLAINTS_EMAIL} so we can assist you fully."),
    },
    "دعم بطيء": {
        "ar": (f"نعتذر عن أي تأخير في الرد، وتجربتك محل اهتمامنا. "
               f"يسعدنا خدمتك مباشرة عبر الرقم الموحّد {COMPLAINTS_PHONE} أو البريد "
               f"{COMPLAINTS_EMAIL}، وسنتابع طلبك حتى إغلاقه بإذن الله."),
        "en": (f"We apologize for any delay in our response; your experience is important to us. "
               f"We'd be glad to assist you directly via {COMPLAINTS_PHONE} or {COMPLAINTS_EMAIL} "
               f"and will follow your request through to resolution."),
    },
    "رسوم مرتفعة": {
        "ar": (f"نشكر لك ملاحظتك بخصوص الرسوم، ونحرص دائمًا على الشفافية والوضوح. "
               f"يسعدنا توضيح تفاصيل أي رسوم على حسابك عبر الرقم الموحّد {COMPLAINTS_PHONE} "
               f"أو البريد {COMPLAINTS_EMAIL}. رضاك غايتنا."),
        "en": (f"Thank you for your note regarding fees; we're committed to full transparency. "
               f"We'd be happy to clarify any charges on your account via {COMPLAINTS_PHONE} "
               f"or {COMPLAINTS_EMAIL}. Your satisfaction is our goal."),
    },
    "إيجابي": {
        "ar": ("سعدنا كثيرًا بكلماتك الطيبة ونشكرك على ثقتك بمصرف الإنماء. "
               "دعمك يحفّزنا لتقديم الأفضل دائمًا، ونسعد بخدمتك على الدوام. دمت بخير."),
        "en": ("Thank you so much for your kind words and your trust in Alinma. "
               "Your support motivates us to keep delivering our best, and we're always happy to serve you."),
    },
    "أخرى": {
        "ar": (f"نشكر لك تواصلك ومشاركتك رأيك، فآراء عملائنا محل اهتمامنا. "
               f"يسعدنا استقبال تفاصيل ملاحظتك عبر الرقم الموحّد {COMPLAINTS_PHONE} "
               f"أو البريد {COMPLAINTS_EMAIL} لخدمتك بأفضل صورة."),
        "en": (f"Thank you for reaching out and sharing your feedback; our customers' opinions matter to us. "
               f"We'd be glad to receive more details via {COMPLAINTS_PHONE} or {COMPLAINTS_EMAIL} "
               f"so we can serve you better."),
    },
}


def template_reply(category, language):
    """الطبقة 3: إرجاع رد جاهز حسب التصنيف واللغة (يعمل دائمًا بلا إنترنت)."""
    lang = "ar" if str(language).startswith("ar") else "en"
    block = TEMPLATE_REPLIES.get(category, TEMPLATE_REPLIES["أخرى"])
    return block[lang]


def _user_prompt(review_text, category, language):
    """رسالة المستخدم التي تُرسل للنموذج."""
    return (f"التصنيف: {category}\n"
            f"لغة العميل: {language}\n"
            f"نص التقييم: {review_text}\n"
            f"اكتب الرد المناسب الجاهز للنشر:")


def groq_reply(review_text, category, language):
    """الطبقة 1: توليد الرد عبر Groq المجاني (llama-3.3-70b) — بدون بث، مع تحقق من السلامة."""
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def fetch():
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(review_text, category, language)},
            ],
            # حرارة منخفضة نسبيًا لتقليل احتمال تلوّث الرد بحروف من لغة أخرى
            temperature=0.4,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()

    return _clean_ai_reply(fetch)


def gemini_reply(review_text, category, language):
    """الطبقة 2: توليد الرد عبر Google Gemini المجاني (gemini-1.5-flash) — بدون بث، مع تحقق من السلامة."""
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

    def fetch():
        resp = model.generate_content(
            _user_prompt(review_text, category, language),
            generation_config={"temperature": 0.4},
        )
        return resp.text.strip()

    return _clean_ai_reply(fetch)


def groq_reply_stream(review_text, category, language):
    """الطبقة 1 (بث حي): يُرجع مولّدًا (generator) يبثّ الرد كلمة بكلمة فور توليدها فعليًا من النموذج."""
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(review_text, category, language)},
        ],
        temperature=0.4,
        max_tokens=300,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def gemini_reply_stream(review_text, category, language):
    """الطبقة 2 (بث حي): يُرجع مولّدًا يبثّ الرد تدريجيًا من Gemini فور توليده فعليًا."""
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
    stream = model.generate_content(_user_prompt(review_text, category, language), stream=True)
    for chunk in stream:
        if chunk.text:
            yield chunk.text


def template_reply_stream(category, language, delay=0.045):
    """
    الطبقة 3 (عرض تدريجي): القالب جاهز فورًا (بلا إنترنت)، لكننا نعرضه
    كلمة بكلمة بمهلة بسيطة فقط لأغراض العرض المرئي أثناء التسجيل —
    النص نفسه ثابت ومُعدّ مسبقًا، وليس توليدًا آنيًا من نموذج.
    """
    text = template_reply(category, language)
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


def active_tier_name():
    """اسم الطبقة التي ستُستخدم حاليًا (لعرضها في الواجهة)."""
    if os.getenv("GROQ_API_KEY"):
        return "Groq (llama-3.3-70b)"
    if os.getenv("GEMINI_API_KEY"):
        return "Gemini (1.5-flash)"
    return "قالب جاهز (بدون مفتاح)"


def generate_reply(review_text, category, language="ar"):
    """
    الدالة الرئيسية (صامتة، بلا طباعة) — تستخدمها لوحة app.py.
    تختار أفضل طبقة متاحة تلقائيًا وتُرجع (نص_الرد, اسم_الطبقة_المستخدمة).
    عند فشل أي طبقة (خطأ شبكة، حد المعدل...) ننتقل للطبقة التالية بأمان.
    """
    # الطبقة 1: Groq
    if os.getenv("GROQ_API_KEY"):
        try:
            return groq_reply(review_text, category, language), "Groq (llama-3.3-70b)"
        except Exception as e:
            print(f"   ⚠️ فشل Groq، ننتقل للطبقة التالية: {e}")

    # الطبقة 2: Gemini
    if os.getenv("GEMINI_API_KEY"):
        try:
            return gemini_reply(review_text, category, language), "Gemini (1.5-flash)"
        except Exception as e:
            print(f"   ⚠️ فشل Gemini، ننتقل للقوالب: {e}")

    # الطبقة 3: القوالب الجاهزة (تعمل دائمًا)
    return template_reply(category, language), "قالب جاهز (بدون إنترنت)"


def _typing_stream(text, delay=0.035):
    """يعرض نصًا جاهزًا ككلمات متتالية بمهلة بسيطة — تأثير كتابة حية للعرض المرئي."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


def generate_reply_live(review_text, category, language="ar"):
    """
    نسخة العرض الحي للطرفية (تُستخدم في 3_generate_reply.py):
    تطبع أثرًا تفصيليًا لاختيار الطبقة، ثم تطبع الرد وهو "يُكتب" أمامك.

    ملاحظة تقنية مهمة: نجلب الرد الكامل من النموذج أولًا (مع التحقق من
    خلوّه من أي تلوّث بلغة أخرى عبر _clean_ai_reply)، ثم نعرضه بتأثير
    كتابة تدريجية — بدل بث كل رمز (token) فور وصوله مباشرة. السبب: لو
    عرضنا كل رمز فور وصوله، وتوقّف النموذج في منتصف كلمة ملوَّثة بلغة
    أخرى (خلل نادر لكن حقيقي في النماذج المجانية)، سيظهر ذلك مباشرة أمام
    الكاميرا قبل أن نتمكن من اكتشافه. بهذه الطريقة نضمن أن كل ما يُعرض
    تم فحصه والتأكد من سلامته قبل ظهوره على الشاشة — لكن المحتوى نفسه
    يبقى توليدًا حقيقيًا 100% من النموذج، وليس نصًا مُعدًّا مسبقًا.
    تُرجع (نص_الرد الكامل, اسم_الطبقة_المستخدمة) بعد انتهاء الطباعة.
    """
    def check(env_var, label):
        found = bool(os.getenv(env_var))
        mark = "✅ موجود" if found else "❌ غير موجود"
        print(f"🔍 التحقق من {env_var} ({label})... {mark}")
        return found

    has_groq = check("GROQ_API_KEY", "Groq")
    text = None
    tier_name = None

    if has_groq:
        try:
            print("🚀 استخدام الطبقة 1: Groq (llama-3.3-70b) — توليد حقيقي عبر الإنترنت ...", end=" ", flush=True)
            text = groq_reply(review_text, category, language)
            tier_name = "Groq (llama-3.3-70b)"
            print("تم ✅")
        except Exception as e:
            print(f"فشل ⚠️ ({e})")

    if text is None:
        has_gemini = check("GEMINI_API_KEY", "Gemini")
        if has_gemini:
            try:
                print("🚀 استخدام الطبقة 2: Gemini (1.5-flash) — توليد حقيقي عبر الإنترنت ...", end=" ", flush=True)
                text = gemini_reply(review_text, category, language)
                tier_name = "Gemini (1.5-flash)"
                print("تم ✅")
            except Exception as e:
                print(f"فشل ⚠️ ({e})")

    if text is None:
        print("✅ استخدام الطبقة 3: قالب جاهز مُعدّ مسبقًا (بدون إنترنت — أضمن طبقة للعرض)")
        tier_name = "قالب جاهز (بدون إنترنت)"
        text = template_reply(category, language)

    print(f"\n📝 الرد يُكتب الآن ({tier_name}):\n   ", end="", flush=True)
    for chunk in _typing_stream(text):
        print(chunk, end="", flush=True)
    print("\n")
    return text.strip(), tier_name
