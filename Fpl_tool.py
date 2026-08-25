import datetime
import os
from PIL import Image
import google.generativeai as genai
import requests
import streamlit as st

# 1. إعدادات الصفحة والتصميم البصري (CSS)
st.set_page_config(
    page_title="مدير الفانتسي الذكي 2026/2027",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.stApp { background-color: #0d0118; color: #ffffff; }
div.stButton > button {
    background: linear-gradient(135deg, #00ff87 0%, #02efff 100%);
    color: #37003c !important; font-weight: bold !important; font-size: 16px !important;
    border-radius: 12px !important; border: none !important; padding: 10px 24px !important;
    transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(0, 255, 135, 0.3);
}
div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 255, 135, 0.5); }
section[data-testid="stSidebar"] { background-color: #1a002c !important; border-right: 1px solid #37003c; }
.stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
    background-color: #240038 !important; color: #ffffff !important; border: 1px solid #00ff87 !important; border-radius: 8px;
}
.pitch-container {
    background: linear-gradient(180deg, #1e7145 0%, #114b2d 100%);
    border: 2px solid #00ff87; border-radius: 15px; padding: 20px 10px; margin-bottom: 15px;
}
.pitch-row { display: flex; justify-content: space-evenly; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
.player-card {
    background: rgba(36, 0, 56, 0.95); color: #ffffff; border: 1px solid #00ff87;
    padding: 6px 10px; border-radius: 8px; text-align: center; font-size: 12px; min-width: 75px;
}
.player-card span { display: block; font-size: 10px; color: #00ff87; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)


# 2. الحفظ التلقائي للمفاتيح (دعم Railway و Streamlit Secrets)
def get_secret(key_name, default=""):
    if key_name in os.environ:
        return os.environ[key_name]
    try:
        if key_name in st.secrets:
            return str(st.secrets[key_name])
    except Exception:
        pass
    return default


secrets_gemini = get_secret("GEMINI_API_KEY") or get_secret("gemini_key")
secrets_fpl_id = get_secret("FPL_ID") or get_secret("fpl_id")

# 3. القائمة الجانبية (Sidebar)
with st.sidebar:
    st.title("⚙️ الإعدادات والربط")
    user_gemini_key = st.text_input(
        "مفتاح Gemini API:",
        value=secrets_gemini,
        type="password",
        help="المفتاح مفعل تلقائياً من الإعدادات",
    )
    user_fpl_id = st.text_input(
        "معرف فريقك (FPL Team ID):",
        value=secrets_fpl_id,
        placeholder="مثال: 3427112",
    )

    if user_gemini_key:
        secrets_gemini = user_gemini_key
    if user_fpl_id:
        secrets_fpl_id = user_fpl_id

    st.markdown("---")
    st.caption("تغطية حية لموسم 2026/2027 ⚽")

# 4. إعداد واستدعاء الذكاء الاصطناعي (Gemini)
if secrets_gemini:
    try:
        genai.configure(api_key=secrets_gemini)
    except Exception:
        pass


def ask_gemini(prompt_text):
    if not secrets_gemini:
        return "⚠️ يرجى إدخال مفتاح Gemini API في القائمة الجانبية أو في متغيرات Railway."

    last_error = ""
    # تجربة أحدث موديلات Gemini بالترتيب
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            continue

    return f"⚠️ خطأ من Google API: {last_error}"

# 5. وظائف جلب البيانات المباشرة من FPL API
def get_json(url):
    try:
        res = requests.get(url, timeout=8)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None


@st.cache_data(ttl=3600)
def fetch_live_fpl_data():
    static_data = get_json(
        "https://fantasy.premierleague.com/api/bootstrap-static/"
    )
    if not static_data:
        return None, None, None
    players = {p["id"]: p for p in static_data["elements"]}
    teams = {t["id"]: t["name"] for t in static_data["teams"]}
    types = {
        et["id"]: et["singular_name_short"]
        for et in static_data["element_types"]
    }
    return players, teams, types


def fetch_manager_squad(manager_id):
    players, teams, types = fetch_live_fpl_data()
    if not players:
        return None, "تعذر جلب بيانات الفانتسي العامة حالياً."

    entry_data = get_json(
        f"https://fantasy.premierleague.com/api/entry/{manager_id}/"
    )
    if not entry_data:
        return None, "رقم الفريق غير صحيح أو يتعذر الوصول له."

    current_gw = entry_data.get("current_event", 1)
    picks_data = get_json(
        f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{current_gw}/picks/"
    )
    if not picks_data:
        return None, "تعذر جلب تشكيلة الجولة الحالية."

    squad = []
    for pick in picks_data.get("picks", []):
        p_info = players.get(pick["element"], {})
        squad.append({
            "name": p_info.get("web_name", "لاعب"),
            "team": teams.get(p_info.get("team"), ""),
            "pos": types.get(p_info.get("element_type"), "GKP"),
            "is_captain": pick.get("is_captain", False),
            "is_vice": pick.get("is_vice_captain", False),
            "position": pick.get("position", 1),
        })
    return squad, None


# 6. الواجهة الرئيسية والتنقل (مخففة ومسرعة)
st.title("⚽ بوت الفانتسي الذكي المباشر")

category = st.selectbox(
    "اختر القسم المطلوب 📍",
    [
        "💬 المساعد الصوتي والدردشة",
        "📊 تحليل التشكيلة والتقرير اليومي",
        "🛡️ (EO) مؤشر الملكية المؤثرة",
        "🎯 (Chips) مخطط الخصائص",
        "🚨 مخطط التهديدات الـ 3 القادمة",
        "🚑 رادار الإصابات والغيابات",
        "👑 مصفوفة الكابتن",
    ],
)

# ---------------------------------------------------------
# القسم الأول: المساعد الصوتي والدردشة
# ---------------------------------------------------------
if category == "💬 المساعد الصوتي والدردشة":
    st.header("🗣️ الدردشة والاستفسارات المباشرة")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_query = st.chat_input("اسأل عن أي لاعب، مؤتمر، أو تبديل...")
    if user_query:
        st.session_state.messages.append(
            {"role": "user", "content": user_query}
        )
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            with st.spinner("جاري التفكير..."):
                answer = ask_gemini(
                    f"بصفتك خبير فانتسي البريميرليج، أجب باختصار واحترافية: {user_query}"
                )
                st.write(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

# ---------------------------------------------------------
# القسم الثاني: تحليل التشكيلة والتقرير اليومي
# ---------------------------------------------------------
elif category == "📊 تحليل التشكيلة والتقرير اليومي":
    st.header("📊 تحليل التشكيلة وحالة الفريق")

    if not secrets_fpl_id:
        st.warning("⚠️ يرجى أدخال رقم FPL Team ID في القائمة الجانبية.")
    else:
        if st.button("🚀 جلب وتحليل التشكيلة بـ ID"):
            with st.spinner("جاري جلب البيانات ورسم الملعب..."):
                squad, err = fetch_manager_squad(secrets_fpl_id)
                if err:
                    st.error(err)
                else:
                    st.subheader("🟢 التشكيلة الأساسية على الملعب")

                    # تقسيم اللاعبين أساسيين وبدلاء
                    starting_11 = [p for p in squad if p["position"] <= 11]
                    bench = [p for p in squad if p["position"] > 11]

                    gk = [p for p in starting_11 if p["pos"] == "GKP"]
                    defenders = [p for p in starting_11 if p["pos"] == "DEF"]
                    midfielders = [
                        p for p in starting_11 if p["pos"] == "MID"
                    ]
                    forwards = [p for p in starting_11 if p["pos"] == "FWD"]

                    # رسم الملعب
                    st.markdown(
                        '<div class="pitch-container">', unsafe_allow_html=True
                    )

                    for row_players in [gk, defenders, midfielders, forwards]:
                        st.markdown(
                            '<div class="pitch-row">', unsafe_allow_html=True
                        )
                        for p in row_players:
                            cap_tag = (
                                " (C)"
                                if p["is_captain"]
                                else (" (VC)" if p["is_vice"] else "")
                            )
                            st.markdown(
                                f'<div class="player-card">{p["name"]}{cap_tag}<span>{p["team"]}</span></div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    # البدلاء
                    st.write("**دكة البدلاء:**")
                    bench_names = [
                        f"{p['name']} ({p['team']})" for p in bench
                    ]
                    st.info(" | ".join(bench_names))

                    # تقرير الذكاء الاصطناعي
                    st.markdown("---")
                    st.subheader("🤖 تقرير الخبير والبدائل الموصى بها")
                    squad_txt = ", ".join([
                        f"{p['name']} ({p['team']})" for p in squad
                    ])
                    ai_prompt = f"حلل تشكيلة الفانتسي التالية وقدم أفضل نصيحة تبديل واختيار كابتن للجولة القادمة: {squad_txt}"
                    analysis = ask_gemini(ai_prompt)
                    st.write(analysis)

                    # ملخص للواتساب
                    st.subheader("📱 ملخص للنسخ (WhatsApp)")
                    wa_summary = (
                        f"📊 *تقرير تشكيلة الفانتسي*\n\n{analysis[:300]}..."
                    )
                    st.code(wa_summary, language="text")

# ---------------------------------------------------------
# باقي الأقسام الخفيفة السريعة
# ---------------------------------------------------------
elif category == "🛡️ (EO) مؤشر الملكية المؤثرة":
    st.header("🛡️ المؤشر المؤثر للملكية (Effective Ownership)")
    st.info(
        "يساعدك هذا المؤشر على معرفة تأثير تألق اللاعب على ترتيبك في الدوري."
    )
    player_input = st.text_input("ادخل اسم اللاعب لمعاينة نسبة مخاطرته:")
    if player_input:
        res = ask_gemini(
            f"ما هي نسبة الملكية الكلية والمؤثرة المقدرة للاعب {player_input} وما هي خطورة عدم امتلاكه؟"
        )
        st.write(res)

elif category == "🎯 (Chips) مخطط الخصائص":
    st.header("🎯 التخطيط لاستخدام الخصائص (Chips)")
    st.write("أفضل الفترات المقترحة لاستخدام (Wildcard, Free Hit, Bench Boost):")
    res = ask_gemini(
        "أعطني استراتيجية سريعة ومختصرة لاستخدام خواص الفانتسي هذا الموسم."
    )
    st.write(res)

elif category == "🚨 مخطط التهديدات الـ 3 القادمة":
    st.header("🚨 التهديدات وصعوبة المواجهات القادمة")
    res = ask_gemini(
        "اذكر لي أصعب 3 فرق لديها جدول مواجهات معقد في الجولات الثلاث القادمة."
    )
    st.write(res)

elif category == "🚑 رادار الإصابات والغيابات":
    st.header("🚑 أهم الغيابات والإصابات المؤكدة")
    res = ask_gemini(
        "يلخص لي قائمة بـ 5 لاعبين مهمين مصابين أو مشكوك بمشاركتهم للجولة القادمة بالفانتسي."
    )
    st.write(res)

elif category == "👑 مصفوفة الكابتن":
    st.header("👑 أفضل 3 خيارات للكابتن")
    res = ask_gemini(
        "من هم أفضل 3 لاعبين مرشحين لارتداء شارة الكابتن بالجولة القادمة مع نسبة المخاطرة؟"
    )
    st.write(res)
