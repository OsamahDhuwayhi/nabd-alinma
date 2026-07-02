# -*- coding: utf-8 -*-
"""
app.py — لوحة "نبض الإنماء" (المرحلة 4)
=======================================
لوحة تحكم تفاعلية لعرض تقييمات تطبيقات مصرف الإنماء،
تصنيفها، ترتيبها حسب الأولوية، وتوليد ردود مقترحة (مجانًا).

التشغيل:
    streamlit run app.py

ملاحظات:
- كل شيء مجاني: تعمل محليًا وتُستضاف مجانًا على Streamlit Community Cloud.
- لا نستخدم أي تخزين في المتصفح (localStorage/sessionStorage).
- الاعتمادات المصدَّرة تُحفظ في ملف CSV بسيط.
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px

import theme
from reply_engine import (generate_reply, active_tier_name,
                          COMPLAINTS_PHONE, COMPLAINTS_EMAIL)

# ==================== إعداد الصفحة وهوية الإنماء ====================
st.set_page_config(page_title="نبض الإنماء", page_icon="🩺", layout="wide",
                   initial_sidebar_state="expanded")
theme.apply()

# نحدد المسارات نسبةً لموقع هذا الملف حتى تعمل اللوحة من أي مجلد تشغيل
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "alinma_reviews_categorized.csv")
APPROVED_FILE = os.path.join(BASE_DIR, "data", "approved_replies.csv")


# ==================== تحميل البيانات ====================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)
    # ضمان أن replied قيمة منطقية
    df["replied"] = (df["replied"].astype(str).str.lower()
                     .isin(["true", "1", "yes"]))
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(3)
    df["priority_score"] = pd.to_numeric(df["priority_score"], errors="coerce").fillna(0)
    df["text"] = df["text"].fillna("")
    return df


if not os.path.exists(DATA_FILE):
    st.error("لم يتم العثور على ملف البيانات. شغّل أولًا: "
             "`python 1_scrape_reviews.py` ثم `python 2_categorize.py`")
    st.stop()

df = load_data()

# ==================== الشريط العلوي بهوية الإنماء ====================
theme.top_bar(
    word1="نبض",
    word2="الإنماء",
    tagline="رادار صوت العميل — تحويل تقييمات التطبيقات إلى أولويات وردود متوافقة مع الشريعة",
    badge="أداة CX داخلية · هاكاثون أَمَد",
)

# ==================== الشريط الجانبي: الفلاتر ====================
st.sidebar.header("🔎 الفلاتر")
all_platforms = sorted(df["platform"].unique()) if "platform" in df.columns else ["Google Play"]
all_apps = sorted(df["app"].unique())
all_cats = sorted(df["category"].unique())
sel_platforms = st.sidebar.multiselect("المنصة", all_platforms, default=all_platforms)
sel_apps = st.sidebar.multiselect("التطبيق", all_apps, default=all_apps)
sel_cats = st.sidebar.multiselect("التصنيف", all_cats, default=all_cats)
rmin, rmax = st.sidebar.slider("التقييم (نجوم)", 1, 5, (1, 5))
reply_filter = st.sidebar.radio("حالة الرد", ["الكل", "لم يُرد عليها", "تم الرد عليها"])

st.sidebar.markdown("---")
st.sidebar.info(f"طبقة توليد الردود النشطة:\n\n**{active_tier_name()}**\n\n"
                "أضف `GROQ_API_KEY` (مجاني) لتفعيل الذكاء الاصطناعي.")
st.sidebar.caption("⚠️ خلاصة Apple العامة لا تكشف حالة رد المطوّر، لذلك "
                   "نسبة الرد الرسمية تُحسب من Google Play فقط.")

# تطبيق الفلاتر
f = df[df["platform"].isin(sel_platforms) & df["app"].isin(sel_apps)
       & df["category"].isin(sel_cats) & df["rating"].between(rmin, rmax)].copy()
if reply_filter == "لم يُرد عليها":
    f = f[~f["replied"]]
elif reply_filter == "تم الرد عليها":
    f = f[f["replied"]]

# ==================== بطاقات المؤشرات (KPI) ====================
# نسبة الرد الرسمية تُحسب من Google Play فقط، لأن خلاصة Apple العامة لا تكشف
# حالة رد المطوّر — دمجها مع بيانات مجهولة الحالة يعطي رقمًا مضللًا.
gp_df = df[df["platform"] == "Google Play"]
total = len(df)
total_gp = len(gp_df)
total_ios = len(df[df["platform"] == "App Store"])
reply_rate = gp_df["replied"].mean() * 100 if len(gp_df) else 0
avg_rating = df["rating"].mean()
unreplied_neg = int(((~df["replied"]) & (df["rating"] <= 2)).sum())

k1, k2, k3, k4 = st.columns(4)
with k1:
    theme.kpi_card("إجمالي التقييمات", f"{total:,}",
                   sub=f"Google Play: {total_gp:,} · App Store: {total_ios:,}")
with k2:
    theme.kpi_card("نسبة ردود المصرف", f"{reply_rate:.1f}%", sub="Google Play فقط")
with k3:
    theme.kpi_card("متوسط التقييم", f"{avg_rating:.2f} / 5")
with k4:
    theme.kpi_card("شكاوى سلبية بلا رد", f"{unreplied_neg:,}",
                   sub="تحتاج معالجة عاجلة", accent=True)

# ==================== لقطة صادقة: نسبة الردود لكل تطبيق ====================
# مبنية على Google Play فقط — خلاصة Apple العامة لا تكشف حالة رد المطوّر،
# فإدراجها هنا كان سيجعل كل تطبيق يبدو 0% زورًا بدل "غير معروف".
st.subheader("📊 نسبة الردود لكل تطبيق (Google Play)")
app_stats = (gp_df.groupby("app")
             .agg(عدد_التقييمات=("review_id", "count"),
                  نسبة_الردود=("replied", lambda s: round(s.mean() * 100, 1)))
             .reset_index()
             .sort_values("نسبة_الردود"))

zero_apps = app_stats[app_stats["نسبة_الردود"] == 0]["app"].tolist()
if zero_apps:
    st.markdown(
        f"<div class='nabd-alert'>🔴 <b>{' و '.join(zero_apps)}</b> يردّان على "
        f"<b>0%</b> من التقييمات على Google Play — بينما يوجد <b>{unreplied_neg}</b> "
        f"شكوى سلبية بلا رد ظاهر (على المنصتين معًا) في السوق الآن.</div>",
        unsafe_allow_html=True)

cA, cB = st.columns([1, 1])
with cA:
    theme.styled_table(app_stats, zero_col="نسبة_الردود")
with cB:
    fig_app = px.bar(app_stats, x="نسبة_الردود", y="app", orientation="h",
                     text="نسبة_الردود", color="نسبة_الردود",
                     color_continuous_scale=[theme.COPPER, theme.DEEP_BLUE],
                     range_x=[0, 100])
    fig_app.update_traces(textfont_color=theme.TEXT_DARK, textposition="outside")
    fig_app.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0),
                          yaxis_title="", xaxis_title="نسبة الردود %",
                          coloraxis_showscale=False,
                          **theme.plotly_layout_kwargs())
    st.plotly_chart(fig_app, width="stretch")

# حجم التقييمات على App Store لكل تطبيق (عدد فقط، بدون نسبة رد مضللة)
ios_df = df[df["platform"] == "App Store"]
if len(ios_df):
    st.subheader("📱 حجم التقييمات لكل تطبيق (App Store)")
    st.caption("لا تتوفر حالة الرد عبر خلاصة Apple العامة — لهذا لا نعرض نسبة رد هنا.")
    ios_stats = (ios_df.groupby("app").size().reset_index(name="عدد_التقييمات")
                .sort_values("عدد_التقييمات", ascending=False))
    theme.styled_table(ios_stats)

# ==================== رسم توزيع المواضيع ====================
st.subheader("🗂️ توزيع مواضيع الألم (حسب الفلاتر)")
if len(f):
    cat_counts = f["category"].value_counts().reset_index()
    cat_counts.columns = ["category", "count"]
    fig_cat = px.bar(cat_counts, x="count", y="category", orientation="h",
                     text="count", color="count",
                     color_continuous_scale=theme.CHART_SCALE)
    fig_cat.update_traces(textfont_color=theme.TEXT_DARK, textposition="outside")
    fig_cat.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                          yaxis_title="", xaxis_title="عدد التقييمات",
                          coloraxis_showscale=False,
                          **theme.plotly_layout_kwargs())
    st.plotly_chart(fig_cat, width="stretch")
else:
    st.info("لا توجد تقييمات مطابقة للفلاتر الحالية.")

# ==================== طابور الأولوية + توليد الرد ====================
st.subheader("🚨 طابور الأولوية — الأعلى إلحاحًا أولًا")

queue = f.sort_values("priority_score", ascending=False).head(25)

if len(queue) == 0:
    st.info("لا توجد تقييمات مطابقة للفلاتر الحالية.")
else:
    def fmt(idx):
        r = queue.loc[idx]
        # لا نستطيع تأكيد "لم يُرد عليه" على App Store (خلاصة Apple لا تكشف
        # ذلك) — نعرضها كحالة غير معروفة بدل الجزم بعدم الرد.
        if r.get("platform") == "App Store":
            mark = "❔"
        else:
            mark = "🔴" if not r["replied"] else "✅"
        plat = f" [{r['platform']}]" if r.get("platform") == "App Store" else ""
        return f"{mark} [{r['priority_score']:.1f}] {int(r['rating'])}★ {r['app']}{plat} — {str(r['text'])[:45]}"

    sel_idx = st.selectbox("اختر تقييمًا لمعالجته", queue.index.tolist(), format_func=fmt)

    # عند تغيير الاختيار نمسح الرد القديم
    if st.session_state.get("sel_idx") != sel_idx:
        st.session_state["sel_idx"] = sel_idx
        st.session_state.pop("reply", None)
        st.session_state.pop("reply_src", None)

    row = queue.loc[sel_idx]

    if row.get("platform") == "App Store":
        status_text = "غير معروفة (Apple لا تكشف ذلك)"
    else:
        status_text = "لم يُرد عليها" if not row["replied"] else "تم الرد"

    # تفاصيل التقييم
    st.markdown(f"**المنصة:** {row.get('platform', 'Google Play')} &nbsp;|&nbsp; "
                f"**التطبيق:** {row['app']} &nbsp;|&nbsp; **التقييم:** {int(row['rating'])}★ "
                f"&nbsp;|&nbsp; **التصنيف:** {row['category']} &nbsp;|&nbsp; "
                f"<span class='nabd-priority-badge'>الأولوية {row['priority_score']:.1f}</span> "
                f"&nbsp;|&nbsp; **حالة الرد:** {status_text}",
                unsafe_allow_html=True)
    st.markdown(f"<div class='review-box'>{row['text']}</div>", unsafe_allow_html=True)

    # زر توليد الرد
    if st.button("✍️ توليد رد مقترح"):
        with st.spinner("جارٍ توليد الرد..."):
            reply, src = generate_reply(row["text"], row["category"],
                                        row.get("language", "ar"))
        st.session_state["reply"] = reply
        st.session_state["reply_src"] = src

    # صندوق الرد القابل للتعديل
    if "reply" in st.session_state:
        st.caption(f"المصدر: {st.session_state.get('reply_src', '')} "
                   "· يتطلب مراجعة بشرية قبل الإرسال الفعلي")
        edited = st.text_area("الرد المقترح (يمكن تعديله قبل الاعتماد):",
                              value=st.session_state["reply"], height=140)

        if st.button("✅ اعتماد وتصدير الرد"):
            record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "platform": row.get("platform", "Google Play"),
                "app": row["app"],
                "review_id": row.get("review_id", ""),
                "rating": int(row["rating"]),
                "category": row["category"],
                "review_text": row["text"],
                "approved_reply": edited,
                "tier": st.session_state.get("reply_src", ""),
            }
            out = pd.DataFrame([record])
            header = not os.path.exists(APPROVED_FILE)
            out.to_csv(APPROVED_FILE, mode="a", header=header,
                       index=False, encoding="utf-8-sig")
            st.success(f"✅ تم اعتماد الرد وحفظه في {APPROVED_FILE}")

# ==================== تذييل ====================
st.markdown("---")
st.caption(
    "⚠️ هذه أداة نموذجية داخلية لفريق تجربة العميل، بُنيت لهاكاثون أَمَد — "
    "**وليست منتجًا أو تطبيقًا رسميًا من مصرف الإنماء**، ولا ترسل أي رد فعليًا "
    "دون مراجعة واعتماد بشري. &nbsp;·&nbsp; "
    f"قناة الشكاوى الرسمية: {COMPLAINTS_PHONE} — {COMPLAINTS_EMAIL} &nbsp;·&nbsp; "
    "بيانات عامة من Google Play وApple App Store"
)
