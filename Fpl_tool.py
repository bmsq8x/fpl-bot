import os
import re
import google.generativeai as genai
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم البصري (CSS)
# ---------------------------------------------------------
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
.metric-box {
    background: rgba(36, 0, 56, 0.8); border: 1px solid #00ff87; border-radius: 12px;
    padding: 15px; text-align: center; margin-bottom: 10px;
}
.metric-box h3 { color: #00ff87; margin: 0; font-size: 24px; }
.metric-box p { color: #ffffff; margin: 5px 0 0 0; font-size: 14px; }
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


# ---------------------------------------------------------
# 2. قراءة المفاتيح (Secrets & Environment)
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 3. القائمة الجانبية (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
  st.title("⚙️ الإعدادات والربط")
  user_gemini_key = st.text_input(
      "مفتاح Gemini API:",
      value=secrets_gemini,
      type="password",
      help="المفتاح مفعل تلقائياً من الحساب المدفوع",
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
  st.caption("تغطية حية ومباشرة لموسم 2026/2027 ⚽")


# ---------------------------------------------------------
# 4. دالة التنظيف المتقدمة ودالة الاتصال بالذكاء الاصطناعي
# ---------------------------------------------------------
def extract_arabic_content(text):
  """استخراج النص العربي الصافي وإلغاء أي مسودات تفكير إنجليزية بنسبة 100%"""
  if not text:
    return ""

  lines = text.split("\n")
  clean_lines = []

  for line in lines:
    l_str = line.strip()
    if not l_str:
      clean_lines.append("")
      continue

    # استبعاد أي أسطر تحتوي على كلمات التفكير والمسودات الإنجليزية
    l_lower = l_str.lower()
    if any(
        kw in l_lower
        for kw in [
            "drafting",
            "self-correction",
            "reviewing",
            "thinking",
            "note on",
            "rule 1",
            "rule 2",
            "rule 3",
            "arabic text",
            "final output",
            "let's check",
            "checking",
        ]
    ):
      continue

    # التأكد من أن السطر يحتوي على أسطر عربية أو تنسيق markdown
    has_arabic = bool(re.search(r"[\u0600-\u06FF]", l_str))
    is_markdown_symbol = l_str.startswith(("#", "*", "-", "1.", "2.", "3.", "4."))

    if has_arabic or is_markdown_symbol:
      clean_lines.append(l_str)

  result = "\n".join(clean_lines).strip()
  return (
      result
      if result
      else "⚠️ جاري معالجة الرد، يرجى إعادة الضغط على الزر مرة أخرى."
  )


SYSTEM_PROMPT = """
أنت مستشار وخبير فانتسي الدوري الإنجليزي الممتاز (FPL) لموسم 2026/2027.
تعتمد على دمج بيانات FPL المباشرة مع آراء كبار الخبراء العرب: (@ali7amer, @adelculer, @fplab17, @arabsfpl, @fpljoker1, @fpl_ucf, @kluivertq8).

قواعد صارمة جداً:
1. الإجابة تكون باللغة العربية الفصحى المباشرة والمكتملة فقط.
2. ممنوع منعاً باتاً كتابة أي أفكار جانبية أو مسودات تفكير باللغة الإنجليزية.
3. التزم بأسماء اللاعبين وأنديتهم الرسمية المرفقة في البيانات (موسم 2026/2027). لا تغير أندية اللاعبين بناءً على ذاكرتك القديمة.
4. ابدأ بالتحليل مباشرة وبدون أي مقدمات إنجليزية أو إنشائية.
"""


def ask_gemini(prompt_text, extra_context=""):
  if not secrets_gemini:
    return (
        "⚠️ يرجى إدخال مفتاح Gemini API في القائمة الجانبية أو في متغيرات"
        " Railway."
    )

  try:
    genai.configure(api_key=secrets_gemini)

    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n[الطلب والمُعطيات الحية]:\n{prompt_text}"
    )
    if extra_context:
      full_prompt += f"\n\n[تغريدات وتقارير إضافية]:\n{extra_context}"

    # استخدام الموديل المستقر المباشر دون تعقيد
    model = genai.GenerativeModel("gemini-1.5-flash")

    # إعدادات بسيطة متوافقة مع كل إصدارات المكتبة
    config = {"temperature": 0.2, "max_output_tokens": 2048}

    response = model.generate_content(full_prompt, generation_config=config)

    if response and response.text:
      return extract_arabic_content(response.text)

  except Exception as e:
    # محاولة بديلة بموديل gemini-1.5-pro في حال وجود أي ضغط
    try:
      model_alt = genai.GenerativeModel("gemini-1.5-pro")
      response_alt = model_alt.generate_content(
          full_prompt, generation_config={"temperature": 0.2}
      )
      if response_alt and response_alt.text:
        return extract_arabic_content(response_alt.text)
    except Exception:
      pass
    return f"⚠️ خطأ في الاتصال: {str(e)}"

  return "⚠️ تعذر الحصول على رد، يرجى المحاولة لاحقاً."


# ---------------------------------------------------------
# 5. وظائف جلب بيانات FPL المباشرة والسريعة (Cached)
# ---------------------------------------------------------
def get_json(url):
  try:
    res = requests.get(url, timeout=5)
    return res.json() if res.status_code == 200 else None
  except Exception:
    return None


@st.cache_data(ttl=600)
def fetch_live_fpl_data():
  static_data = get_json(
      "https://fantasy.premierleague.com/api/bootstrap-static/"
  )
  if not static_data:
    return None, None, None, None
  players = {p["id"]: p for p in static_data["elements"]}
  teams = {t["id"]: t["name"] for t in static_data["teams"]}
  types = {
      et["id"]: et["singular_name_short"] for et in static_data["element_types"]
  }
  return players, teams, types, static_data


@st.cache_data(ttl=300)
def fetch_manager_info(manager_id):
  return get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/")


@st.cache_data(ttl=300)
def fetch_manager_squad(manager_id):
  players, teams, types, _ = fetch_live_fpl_data()
  if not players:
    return None, "تعذر جلب بيانات الفانتسي العامة حالياً."

  entry_data = fetch_manager_info(manager_id)
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
        "price": p_info.get("now_cost", 0) / 10,
    })
  return squad, None


# ---------------------------------------------------------
# 6. الواجهة الرئيسية والتنقل
# ---------------------------------------------------------
st.title("⚽ بوت الفانتسي الذكي المباشر (2026/2027)")

category = st.selectbox(
    "اختر القسم المطلوب 📍",
    [
        "🏠 الصفحة الرئيسية (نقاطي والدوريات)",
        "📊 تحليل التشكيلة والتقرير اليومي",
        "🔄 مخطط التبديلات الموصى بها للجولة",
        "💬 المساعد الصوتي والدردشة",
        "👑 مصفوفة الكابتن",
        "🚑 رادار الإصابات والغيابات",
        "🛡️ (EO) مؤشر الملكية المؤثرة",
    ],
)

# ---------------------------------------------------------
# 🏠 الصفحة الرئيسية: نقاطي المباشرة والدوريات
# ---------------------------------------------------------
if category == "🏠 الصفحة الرئيسية (نقاطي والدوريات)":
  st.header("🏠 لوحة التحكم الشخصية والدوريات")

  if not secrets_fpl_id:
    st.warning(
        "⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية لعرض نقاطك ودورياتك."
    )
  else:
    entry_data = fetch_manager_info(secrets_fpl_id)
    if not entry_data:
      st.error("تعذر جلب البيانات. أعد التأكد من رقم الفريق.")
    else:
      col1, col2, col3, col4 = st.columns(4)
      with col1:
        st.markdown(
            f'<div'
            ' class="metric-box"><h3>{entry_data.get("summary_overall_points",'
            " 0)}</h3><p>إجمالي النقاط</p></div>",
            unsafe_allow_html=True,
        )
      with col2:
        st.markdown(
            f'<div'
            ' class="metric-box"><h3>{entry_data.get("summary_overall_rank",'
            " 0):,}</h3><p>الترتيب العام</p></div>",
            unsafe_allow_html=True,
        )
      with col3:
        st.markdown(
            f'<div'
            ' class="metric-box"><h3>{entry_data.get("summary_event_points",'
            " 0)}</h3><p>نقاط الجولة الأخيرة</p></div>",
            unsafe_allow_html=True,
        )
      with col4:
        st.markdown(
            f'<div class="metric-box"><h3>{entry_data.get("name",'
            ' "")}</h3><p>{entry_data.get("player_first_name",'
            ' "")} {entry_data.get("player_last_name", "")}</p></div>',
            unsafe_allow_html=True,
        )

      st.markdown("---")
      st.subheader("🏆 الدوريات الخاصة المنسق بها (Classic Leagues)")

      classic_leagues = entry_data.get("leagues", {}).get("classic", [])
      if classic_leagues:
        league_data = []
        for lg in classic_leagues:
          league_data.append({
              "اسم الدوري": lg.get("name"),
              "ترتيبك الحالي": lg.get("entry_rank"),
              "الترتيب السابق": lg.get("entry_last_rank"),
          })
        st.table(league_data)
      else:
        st.info("لا توجد دوريات خاصة مسجلة لهذا الحساب.")

# ---------------------------------------------------------
# 📊 تحليل التشكيلة والتقرير اليومي
# ---------------------------------------------------------
elif category == "📊 تحليل التشكيلة والتقرير اليومي":
  st.header("📊 تحليل التشكيلة وحالة الفريق")

  expert_tweets = st.text_area(
      "📥 لصق تغريدات الخبراء للدمج مع التقرير (اختياري):",
      placeholder="ضع هنا تغريدات الخبراء لمطابقتها مع تشكيلتك...",
      height=90,
  )

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🚀 جلب وتحليل التشكيلة بـ ID"):
      with st.spinner("جاري جلب البيانات من FPL API..."):
        squad, err = fetch_manager_squad(secrets_fpl_id)
        if err:
          st.error(err)
        else:
          st.session_state["squad_data"] = squad
          squad_txt = ", ".join([f"{p['name']} ({p['team']})" for p in squad])
          ai_prompt = (
              "تشكيلة المستخدم المحدثة لموسم 2026/2027 هي:"
              f" [{squad_txt}].\nقدم تحليلاً كاملاً وتوصية بالبدلاء وقائد الفريق"
              " للجولة القادمة بالعربية الفصحى فقط."
          )

          with st.spinner("جاري إعداد التقرير التكتيكي..."):
            st.session_state["cached_analysis"] = ask_gemini(
                ai_prompt, extra_context=expert_tweets
            )

    if "squad_data" in st.session_state:
      squad = st.session_state["squad_data"]
      st.subheader("🟢 التشكيلة الأساسية على الملعب")
      starting_11 = [p for p in squad if p["position"] <= 11]
      bench = [p for p in squad if p["position"] > 11]

      gk = [p for p in starting_11 if p["pos"] == "GKP"]
      defenders = [p for p in starting_11 if p["pos"] == "DEF"]
      midfielders = [p for p in starting_11 if p["pos"] == "MID"]
      forwards = [p for p in starting_11 if p["pos"] == "FWD"]

      st.markdown('<div class="pitch-container">', unsafe_allow_html=True)
      for row_players in [gk, defenders, midfielders, forwards]:
        st.markdown('<div class="pitch-row">', unsafe_allow_html=True)
        for p in row_players:
          cap_tag = (
              " (كابتن)"
              if p["is_captain"]
              else (" (نائب)" if p["is_vice"] else "")
          )
          st.markdown(
              f'<div class="player-card">{p["name"]}{cap_tag}<span>{p["team"]}</span></div>',
              unsafe_allow_html=True,
          )
        st.markdown("</div>", unsafe_allow_html=True)
      st.markdown("</div>", unsafe_allow_html=True)

      st.write("**دكة البدلاء:**")
      bench_names = [f"{p['name']} ({p['team']})" for p in bench]
      st.info(" | ".join(bench_names))

      st.markdown("---")
      st.subheader("🤖 تقرير الخبير والبدائل الموصى بها")
      if "cached_analysis" in st.session_state:
        st.markdown(st.session_state["cached_analysis"])

# ---------------------------------------------------------
# 🔄 قسم التبديلات الموصى بها
# ---------------------------------------------------------
elif category == "🔄 مخطط التبديلات الموصى بها للجولة":
  st.header("🔄 قسم التبديلات المخصصة لكل جولة")

  expert_input = st.text_area(
      "📥 لصق تغريدات أو تحليلات الخبراء المباشرة (اختياري):",
      placeholder="انسخ هنا آخر التغريدات الخاصة بالتبديلات والتسريبات...",
      height=90,
  )

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🔍 حساب أفضل 2 تبديلات للجولة القادمة"):
      with st.spinner("جاري حساب أفضل خيارات التبديل..."):
        squad, err = fetch_manager_squad(secrets_fpl_id)
        if err:
          st.error(err)
        else:
          squad_txt = ", ".join([
              f"{p['name']} ({p['pos']} - {p['team']} - السعر: {p['price']}"
              " مليون)"
              for p in squad
          ])
          transfer_prompt = f"""
                    تشكيلة المستخدم الحالية لموسم 2026/2027: [{squad_txt}].
                    
                    قدم توصيتين للتبديل للجولة القادمة باللغة العربية الفصحى فقط:
                    1. التبديل الأول (الأولوية القصوى): اسم المغادر والبديل ونظرة تكتيكية.
                    2. التبديل الثاني (اختياري/تفاضلي): اسم المغادر والبديل ونسبة المخاطرة.
                    """
          st.session_state["cached_transfers"] = ask_gemini(
              transfer_prompt, extra_context=expert_input
          )

    if "cached_transfers" in st.session_state:
      st.markdown(st.session_state["cached_transfers"])

# ---------------------------------------------------------
# باقي الأقسام
# ---------------------------------------------------------
elif category == "💬 المساعد الصوتي والدردشة":
  st.header("🗣️ الدردشة واستفسارات الفانتسي")
  if "messages" not in st.session_state:
    st.session_state.messages = []

  for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
      st.write(msg["content"])

  user_query = st.chat_input("اسأل عن أي لاعب، مؤتمر، أو تبديل...")
  if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
      st.write(user_query)

    with st.chat_message("assistant"):
      with st.spinner("جاري التفكير..."):
        answer = ask_gemini(user_query)
        st.write(answer)
        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

elif category == "👑 مصفوفة الكابتن":
  st.header("👑 أفضل خيارات الكابتن للجولة")
  if st.button("🚀 عرض ترشيحات الكابتن"):
    with st.spinner("جاري التحليل..."):
      res = ask_gemini(
          "من هم أفضل 3 لاعبين مرشحين لشارة الكابتن للجولة القادمة مع توضيح"
          " خيار آمن وخيار تفاضلي باللغة العربية الفصحى؟"
      )
      st.write(res)

elif category == "🚑 رادار الإصابات والغيابات":
  st.header("🚑 أهم الغيابات والإصابات المؤكدة")
  if st.button("🚀 عرض قائمة الغيابات"):
    with st.spinner("جاري جلب القائمة..."):
      res = ask_gemini(
          "يلخص لي قائمة بأهم 5 لاعبين مصابين أو مشكوك بمشاركتهم للجولة"
          " القادمة في فانتسي الدوري الإنجليزي."
      )
      st.write(res)

elif category == "🛡️ (EO) مؤشر الملكية المؤثرة":
  st.header("🛡️ المؤشر المؤثر للملكية")
  player_input = st.text_input("ادخل اسم اللاعب لمعاينة نسبة مخاطرته:")
  if player_input:
    res = ask_gemini(
        f"ما هي خطورة عدم امتلاك اللاعب {player_input} وما هو تأثيره على"
        " الترتيب العام؟"
    )
    st.write(res)
