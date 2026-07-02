# -*- coding: utf-8 -*-
"""
theme.py — طبقة الهوية البصرية لمصرف الإنماء
==============================================
ثوابت الألوان والخطوط + دوال جاهزة لبناء واجهة تشبه تطبيقات الإنماء
("خطوة للأمام" — النسخة 2025 من الهوية)، بدون استخدام الشعار الحقيقي
(نستخدم wordmark نصي "نبض الإنماء" بدلاً منه لتفادي أي إشكال بالعلامة التجارية).

هذه أداة CX داخلية لهاكاثون أَمَد — وليست منتجًا رسميًا من مصرف الإنماء.

الاستخدام:
    import theme
    theme.apply()                 # يحقن CSS الهوية في الصفحة كاملة
    theme.top_bar("نبض الإنماء")  # شريط علوي بلون الهوية
    theme.kpi_card(...)           # بطاقة مؤشر واحدة
"""

import streamlit as st

# ==================== الألوان الرسمية للهوية (مُستخرجة فعليًا) ====================
# هذه القيم مُستخرجة مباشرة من ملف CSS الحي لموقع مصرف الإنماء الرسمي
# (alinma-portal-style.css على www.alinma.com، تاريخ الفحص: يوليو 2026)
# وليست تقديرًا. أهم النتائج التي غيّرت خطتنا الأولى:
#   - اللون الأساسي الحقيقي لأزرار العمل (.btn-primary) هو بنفسجي فاتح #837FD8،
#     وليس أزرق داكن كما افترضنا مبدئيًا.
#   - شريط الرأس الحقيقي (.header--top-wrapper) خلفيته كحلي داكن جدًا #002134
#     (وهو أيضًا لون النص الافتراضي على الصفحة بأكملها)، وليس #0B2C4D.
#   - لون التمييز الدافئ الحقيقي (.btn-fourth) هو تراكوتا/وردي غامق #CD907E
#     (مع درجة أغمق #A36544 تُستخدم في التظليل)، وليس نحاسي #B87A4B.
#   - خلفية الصفحة الحقيقية كريمية دافئة #FDF8F5، وليست رمادية باردة.
DEEP_BLUE = "#002134"       # الأساسي الداكن الحقيقي — شريط الرأس، النص الافتراضي، الأزرار الثانوية
PURPLE = "#837FD8"          # اللون الأساسي الحقيقي لأزرار العمل (.btn-primary) في الموقع الرسمي
PURPLE_LIGHT = "#ACA8FF"    # درجة بنفسجية أفتح (تستخدمها الإنماء لحالات hover/dropdown)
COPPER = "#CD907E"          # لون التمييز الدافئ الحقيقي (.btn-fourth) — شارات الأولوية
COPPER_DARK = "#A36544"     # درجة أغمق من التمييز (تستخدم في الظلال/الحالات النشطة)
LAVENDER = PURPLE_LIGHT      # يُستخدم كخلفيات ناعمة ووسوم (اسم قديم محفوظ للتوافق)
WHITE = "#FFFFFF"
OFF_WHITE = "#FDF8F5"        # خلفية الصفحة الحقيقية (كريمية دافئة وليست رمادية)
TEXT_DARK = "#002134"        # لون النص الحقيقي على الخلفيات الفاتحة (مطابق لموقع الإنماء)

# تدرّج للرسوم البيانية بألوان الهوية الحقيقية (من الكحلي الداكن إلى التراكوتا عبر البنفسجي)
CHART_SCALE = [DEEP_BLUE, PURPLE, PURPLE_LIGHT, COPPER]

# ملاحظة مهمة عن الخط: الخط الحقيقي لموقع الإنماء هو خط مخصص محمي
# (AlinmaTextTT / sarfont) مُستضاف ذاتيًا وغير متاح للاستخدام العام أو الترخيص لنا،
# لذلك نستخدم بديلاً عربيًا مجانيًا مشابهًا في الشكل (Tajawal) بدلاً من إعادة إنتاج
# ملفات الخط الحقيقية — لتفادي أي إشكال في الترخيص/الملكية.
FONT_FAMILY = "'Tajawal', 'IBM Plex Sans Arabic', sans-serif"
FONT_CDN = "https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap"

RADIUS = "12px"   # قيمة حقيقية شائعة في بطاقات/أزرار موقع الإنماء (إلى جانب 20-32px للعناصر الكبيرة)
SHADOW = "0 2px 10px rgba(0,33,52,0.08)"   # ظل خفيف بلون الكحلي الحقيقي


def apply():
    """
    حقن CSS الهوية كاملًا في صفحة Streamlit الحالية.
    يُستدعى مرة واحدة في بداية كل صفحة/سكربت.
    """
    # ملاحظة مهمة: يجب ألا يحتوي هذا النص على أي سطر فارغ داخل وسم <style>،
    # لأن Streamlit يعالج st.markdown بمحلل Markdown الذي يقطّع كتلة HTML
    # عند أي سطر فارغ، فيظهر بعدها CSS كنص عادي بدل أن يُطبَّق كتنسيق.
    css = "".join([
        f":root{{--deep-blue:{DEEP_BLUE};--purple:{PURPLE};--copper:{COPPER};--lavender:{LAVENDER};--off-white:{OFF_WHITE};}}",
        f".stApp{{direction:rtl;background:{OFF_WHITE};font-family:{FONT_FAMILY};}}",
        '[data-testid="stMetricValue"],[data-testid="stMetricDelta"]{direction:ltr;}',
        f"html,body,[class*='css']{{font-family:{FONT_FAMILY};}}",
        "#MainMenu{visibility:hidden;}",
        "footer{visibility:hidden;}",
        # التدرّج يطابق شريط رأس موقع الإنماء الحقيقي (كحلي داكن مع حد سفلي كحلي أفتح قليلًا)
        f".nabd-topbar{{background:linear-gradient(90deg,{DEEP_BLUE} 0%,#033957 100%);color:{WHITE};padding:22px 32px;border-radius:{RADIUS};margin-bottom:22px;box-shadow:{SHADOW};display:flex;align-items:center;justify-content:space-between;}}",
        f".nabd-wordmark{{font-size:1.7rem;font-weight:900;color:{WHITE};letter-spacing:0.5px;margin:0;}}",
        f".nabd-wordmark span{{color:{PURPLE};}}",
        f".nabd-tagline{{color:{PURPLE_LIGHT};font-size:0.95rem;margin-top:4px;font-weight:400;}}",
        f".nabd-badge{{background:rgba(255,255,255,0.12);color:{WHITE};border:1px solid rgba(255,255,255,0.25);padding:6px 14px;border-radius:20px;font-size:0.8rem;white-space:nowrap;}}",
        f".nabd-kpi{{background:{DEEP_BLUE};color:{WHITE};border-radius:{RADIUS};padding:18px 20px;box-shadow:{SHADOW};height:100%;}}",
        f".nabd-kpi .kpi-label{{color:{PURPLE_LIGHT};font-size:0.85rem;margin-bottom:6px;}}",
        ".nabd-kpi .kpi-value{font-size:2rem;font-weight:900;direction:ltr;display:inline-block;color:#ffffff;}",
        f".nabd-kpi.accent{{background:{COPPER};}}",
        ".nabd-kpi.accent .kpi-label{color:rgba(255,255,255,0.9);}",
        ".nabd-kpi .kpi-sub{font-size:0.78rem;color:rgba(255,255,255,0.75);margin-top:4px;}",
        f".nabd-card{{background:{WHITE};border-radius:{RADIUS};padding:18px 20px;box-shadow:{SHADOW};margin-bottom:14px;color:{TEXT_DARK};}}",
        f".nabd-alert{{background:#fdecea;border-right:4px solid #c0392b;color:#7a1f14;border-radius:{RADIUS};padding:14px 18px;margin:10px 0 18px 0;font-size:0.95rem;line-height:1.8;}}",
        f".review-box{{background:{WHITE};color:{TEXT_DARK};border-right:4px solid {DEEP_BLUE};padding:14px 18px;border-radius:{RADIUS};margin:8px 0;line-height:1.9;font-size:1.02rem;box-shadow:{SHADOW};}}",
        f".reply-box{{background:#f8f0ed;color:{TEXT_DARK};border-right:4px solid {COPPER};padding:14px 18px;border-radius:{RADIUS};line-height:1.9;box-shadow:{SHADOW};}}",
        f".nabd-priority-badge{{display:inline-block;background:{COPPER};color:{WHITE};border-radius:20px;padding:3px 12px;font-size:0.8rem;font-weight:700;}}",
        # جدول مخصص بالهوية (بديل عن st.dataframe الذي لا يمكن تلوينه عبر CSS
        # لأن Streamlit يرسمه بمكتبة JS خاصة (glide-data-grid) وليس HTML عادي)
        f".nabd-table{{width:100%;border-collapse:collapse;border-radius:{RADIUS};overflow:hidden;box-shadow:{SHADOW};font-size:0.92rem;}}",
        f".nabd-table th{{background:{DEEP_BLUE};color:{WHITE} !important;padding:10px 14px;text-align:right;font-weight:700;}}",
        f".nabd-table td{{background:{WHITE};color:{TEXT_DARK} !important;padding:9px 14px;border-bottom:1px solid #f0e8e2;}}",
        f".nabd-table tr:last-child td{{border-bottom:none;}}",
        f".nabd-table tr.zero-row td{{background:#fdecea;color:#7a1f14 !important;font-weight:700;}}",
        # نستخدم !important + محددات خاصة بـ Streamlit لأن محدد h2/h3 العادي
        # كان يُهزَم بأنماط Streamlit الداخلية الأعلى تخصيصًا (تظهر الإيموجي فقط بدون النص).
        # لا نطبّق هذا على nabd-topbar / nabd-kpi حتى لا نكسر النص الأبيض هناك.
        f".stApp [data-testid='stMarkdownContainer'] h1,.stApp [data-testid='stMarkdownContainer'] h2,.stApp [data-testid='stMarkdownContainer'] h3,.stApp h1,.stApp h2,.stApp h3{{color:{DEEP_BLUE} !important;font-weight:700 !important;}}",
        f".stApp [data-testid='stCaptionContainer']{{color:#5a6472 !important;}}",
        f"section[data-testid='stSidebar']{{background:{WHITE};border-left:1px solid #e6e6ea;}}",
        f"section[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] h1,section[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] h2,section[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] h3{{color:{DEEP_BLUE} !important;}}",
        f"section[data-testid='stSidebar'] label,section[data-testid='stSidebar'] label p{{color:{TEXT_DARK} !important;}}",
        # وسوم الاختيار المتعدد (multiselect) وتسميات المنزلقات في الشريط الجانبي
        # كانت رمادية باهتة على أبيض — نجعلها بلون الهوية بتباين واضح
        f"section[data-testid='stSidebar'] [data-baseweb='tag']{{background-color:{DEEP_BLUE} !important;}}",
        f"section[data-testid='stSidebar'] [data-baseweb='tag'] span{{color:{WHITE} !important;}}",
        f"section[data-testid='stSidebar'] [data-testid='stTickBarMin'],section[data-testid='stSidebar'] [data-testid='stTickBarMax']{{color:{TEXT_DARK} !important;}}",
        f"section[data-testid='stSidebar'] [data-testid='stSliderThumbValue']{{color:{DEEP_BLUE} !important;font-weight:700 !important;}}",
        f".stButton>button{{background:{PURPLE};color:{WHITE};border:none;border-radius:8px;font-family:{FONT_FAMILY};font-weight:600;padding:8px 18px;}}",
        f".stButton>button:hover{{background:{DEEP_BLUE};color:{WHITE};}}",
    ])
    st.markdown(
        f'<link rel="preconnect" href="https://fonts.googleapis.com">'
        f'<link href="{FONT_CDN}" rel="stylesheet">'
        f'<style>{css}</style>',
        unsafe_allow_html=True,
    )


def top_bar(word1="نبض", word2="الإنماء", tagline="", badge=""):
    """
    شريط علوي بهوية الإنماء (أزرق داكن) يحتوي wordmark نصي (وليس الشعار الحقيقي).
    الكلمة الأولى تُعرض باللون النحاسي (تمييز) والثانية بالأبيض.
    """
    badge_html = f'<div class="nabd-badge">{badge}</div>' if badge else ""
    st.markdown(f"""
    <div class="nabd-topbar">
        <div>
            <p class="nabd-wordmark"><span>{word1}</span> {word2}</p>
            {f'<p class="nabd-tagline">{tagline}</p>' if tagline else ''}
        </div>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label, value, sub="", accent=False):
    """بطاقة مؤشر واحدة (KPI) بلون الهوية. accent=True تستخدم اللون النحاسي."""
    cls = "nabd-kpi accent" if accent else "nabd-kpi"
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="{cls}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def styled_table(df, zero_col=None):
    """
    جدول HTML مخصص بألوان الهوية، بديل عن st.dataframe.
    السبب: st.dataframe في Streamlit الحديث يُرسم عبر مكتبة JS خاصة
    (glide-data-grid على عنصر canvas) ولا يمكن تغيير ألوانه عبر CSS إطلاقًا،
    لذلك أي تنسيق نضيفه لا يظهر — من هنا جاء تقرير "التنسيق ما تغيّر".
    zero_col: اسم عمود رقمي، إن كانت قيمته 0 في صف ما يُلوَّن الصف بالأحمر التنبيهي.
    """
    thead = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        is_zero = zero_col is not None and r[zero_col] == 0
        cls = " class='zero-row'" if is_zero else ""
        tds = "".join(f"<td>{r[c]}</td>" for c in df.columns)
        rows.append(f"<tr{cls}>{tds}</tr>")
    html = f"<table class='nabd-table'><thead><tr>{thead}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


def plotly_layout_kwargs():
    """
    إعدادات موحّدة لرسوم Plotly بألوان الهوية الحقيقية.
    مهم: تحديد font.color صراحة إلزامي — font_family وحدها لا تُغيّر لون النص،
    وPlotly يستخدم رماديًا باهتًا افتراضيًا لا يظهر بوضوح، وهذا سبب شكوى
    "الأرقام والتسميات على الرسم البياني رمادية وصعبة القراءة".
    """
    return dict(
        font=dict(family=FONT_FAMILY, color=TEXT_DARK, size=13),
        xaxis=dict(color=TEXT_DARK, title_font=dict(color=TEXT_DARK), tickfont=dict(color=TEXT_DARK)),
        yaxis=dict(color=TEXT_DARK, title_font=dict(color=TEXT_DARK), tickfont=dict(color=TEXT_DARK)),
        plot_bgcolor=WHITE,
        paper_bgcolor=WHITE,
    )
