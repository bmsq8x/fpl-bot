import os
import requests
import streamlit as st
from openai import OpenAI

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
    padding: 6px 10px; border-radius: 8px; text-align: center; font-size: 12px; min-width: 85px;
}
.player-card span { display: block; font-size: 10px; color: #00ff87; font-weight: bold; }
.player-card .price { font-size: 10px; color: #02efff; }
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


# إدراج المفتاح الخاص بك بشكل افتراضي ومضمون
DEFAULT_KEY = "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"

secrets_openai = (
    get_secret("OPENAI_API_KEY")
    or get_secret("openai_key")
    or get_secret("OPENAI_KEY")
    or DEFAULT_KEY
)
secrets_fpl_id = get_secret("FPL_ID") or get_secret("fpl_id")

# ---------------------------------------------------------
# 3. القائمة الجانبية (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
  st.title("⚙️ الإعدادات والربط")

  user_openai_key = st.text_input(
      "مفتاح OpenAI API:",
      value=secrets_openai,
      type="password",
      placeholder="sk-proj-...",
  )

  user_fpl_id = st.text_input(
      "معرف فريقك (FPL Team ID):",
      value=secrets_fpl_id,
      placeholder="مثال: 3427112",
  )

  if user_openai_key:
    secrets_openai = user_openai_key
  if user_fpl_id:
    secrets_fpl_id = user_fpl_id

  st.markdown("---")
  st.caption("موسم 2026/2027 ⚽ | ربط حسي ببيانات FPL المباشرة")


# ---------------------------------------------------------
# 4. وظائف جلب بيانات FPL المباشرة وصعوبة المباريات (FDR)
# ---------------------------------------------------------
def get_json(url):
  try:
    res = requests.get(url, timeout=5)
    return res.json() if res.status_code == 200 else None
  except Exception:
    return None


@st.cache_data(ttl=60)
def fetch_live_fpl_data():
  """جلب البيانات الأساسية الرسمية للاعبين والأندية بأسعارهم الحالية الدقيقة"""
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


@st.cache_data(ttl=120)
def fetch_top_fpl_players_data():
  """جلب قائمة بأهم 50 لاعباً حالياً في الفانتسي مع أنديتهم وأسعارهم الرسمية"""
  players, teams, _, _ = fetch_live_fpl_data()
  if not players:
    return ""
  top_p = sorted(
      players.values(),
      key=lambda x: float(x.get("selected_by_percent", 0) or 0),
      reverse=True,
  )[:50]
  info = [
      f"- {p['web_name']} ({teams.get(p['team'])}): Price £{p['now_cost']/10}M,"
      f" Selected {p['selected_by_percent']}%"
      for p in top_p
  ]
  return "\n".join(info)


@st.cache_data(ttl=120)
def fetch_fixtures_difficulty():
  """جلب صعوبة المباريات القادمة (FDR) لكل الأندية"""
  fixtures = get_json("https://fantasy.premierleague.com/api/fixtures/")
  if not fixtures:
    return ""

  upcoming = [f for f in fixtures if not f.get("finished", False)][:30]
  fdr_summary = []
  for f in upcoming:
    h_team = f.get("team_h")
    a_team = f.get("team_a")
    h_diff = f.get("team_h_difficulty", 3)
    a_diff = f.get("team_a_difficulty", 3)
    gw = f.get("event", 1)
    fdr_summary.append(
        f"GW {gw}: Team {h_team} (Difficulty: {h_diff}/5) vs Team {a_team}"
        f" (Difficulty: {a_diff}/5)"
    )
  return "\n".join(fdr_summary[:15])


@st.cache_data(ttl=60)
def fetch_manager_info(manager_id):
  return get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/")


@st.cache_data(ttl=60)
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
    exact_price = round(p_info.get("now_cost", 0) / 10.0, 1)

    squad.append({
        "name": p_info.get("web_name", "لاعب"),
        "team": teams.get(p_info.get("team"), ""),
        "pos": types.get(p_info.get("element_type"), "GKP"),
        "is_captain": pick.get("is_captain", False),
        "is_vice": pick.get("is_vice_captain", False),
        "position": pick.get("position", 1),
        "price": exact_price,
        "selected_by": p_info.get("selected_by_percent", "0.0"),
        "status": p_info.get("status", "a"),
        "news": p_info.get("news", ""),
    })
  return squad, None


# ---------------------------------------------------------
# 5. التوجيه ودوال الاتصال بـ OpenAI مع حظر الهلوسة
# ---------------------------------------------------------
SYSTEM_PROMPT = """
أنت المستشار والخبير الرئيسي لـ FPL الدوري الإنجليزي الممتاز لموسم 2026/2027.
تعتمد تحليلاتك حواً وحصرياً على البيانات المباشرة المرفقة في الطلب.

قواعد صارمة جداً لمنع الهلوسة ومعلومات الذاكرة القديمة:
1. يمنع منعاً باتاً ذكر أي لاعب غادر الدوري الإنجليزي الممتاز (مثل هاري كين) أو تغيير أندية اللاعبين (مثل ادعاء انتقال محمد صلاح لطرابزون).
2. يجب التقيُّد التام والكامل بالأسعار الرسمية المرفقة معك في نص الطلب (مثال: سعر هالاند وصلاح وبرونو المذكور بالطلب فقط).
3. آراء واستراتيجيات الخبراء العرب للاسترشاد بها: (@ali7amer, @adelculer, @fplab17, @arabsfpl, @fpljoker1, @fpl_ucf, @kluivertq8).
4. أخرج التقرير باللغة العربية الفصحى الواضحة والاحترافية.
"""


def ask_openai(prompt_text, extra_context=""):
  if not secrets_openai:
    return "⚠️ يرجى إدخال مفتاح OpenAI API في القائمة الجانبية."

  try:
    client = OpenAI(api_key=secrets_openai)
    fdr_data = fetch_fixtures_difficulty()
    live_players = fetch_top_fpl_players_data()

    full_prompt = (
        f"{prompt_text}\n\n"
        f"📊 [قائمة أهم لاعبي الفانتسي بالدوري الإنجليزي بالأسعار الحقيقية والأندية الحالية]:\n{live_players}\n\n"
        f"📅 [بيانات جدول صعوبة المباريات FDR]:\n{fdr_data}"
    )
    if extra_context:
      full_prompt += f"\n\n📌 [تغريدات وتحليلات الخبراء المرفقة]:\n{extra_context}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.1,  # تقليل الحرارة لأدنى درجة لمنع الابتكار الخاطئ
        max_tokens=2000,
    )

    if response.choices and response.choices[0].message.content:
      return response.choices[0].message.content.strip()

  except Exception as e:
    return f"⚠️ خطأ في الاتصال بـ OpenAI: {str(e)}"

  return "⚠️ تعذر الحصول على رد من OpenAI."


# ---------------------------------------------------------
# 6. الواجهة الرئيسية والتنقل
# ---------------------------------------------------------
st.title("⚽ مدير الفانتسي الذكي المباشر (2026/2027)")

category = st.selectbox(
    "اختر القسم المطلوب 📍",
    [
        "🏠 الصفحة الرئيسية (نقاطي والدوريات)",
        "📊 تحليل التشكيلة والتقرير اليومي",
        "🔄 مخطط التبديلات الموصى بها للجولة",
        "💬 المساعد الصوتي والدردشة",
        "👑 مصفوفة الكابتن ومستوى المباريات",
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
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    entry_data = fetch_manager_info(secrets_fpl_id)
    if not entry_data:
      st.error("تعذر جلب البيانات. أعد التأكد من رقم الفريق.")
    else:
      pts = entry_data.get("summary_overall_points", 0)
      rank = entry_data.get("summary_overall_rank", 0)
      gw_pts = entry_data.get("summary_event_points", 0)
      team_name = entry_data.get("name", "")
      f_name = entry_data.get("player_first_name", "")
      l_name = entry_data.get("player_last_name", "")

      col1, col2, col3, col4 = st.columns(4)
      with col1:
        st.markdown(
            f'<div class="metric-box"><h3>{pts}</h3><p>إجمالي النقاط</p></div>',
            unsafe_allow_html=True,
        )
      with col2:
        st.markdown(
            f'<div class="metric-box"><h3>{rank:,}</h3><p>الترتيب'
            " العام</p></div>",
            unsafe_allow_html=True,
        )
      with col3:
        st.markdown(
            f'<div class="metric-box"><h3>{gw_pts}</h3><p>نقاط الجولة'
            " الأخيرة</p></div>",
            unsafe_allow_html=True,
        )
      with col4:
        st.markdown(
            f'<div class="metric-box"><h3>{team_name}</h3><p>{f_name}'
            f" {l_name}</p></div>",
            unsafe_allow_html=True,
        )

      st.markdown("---")
      st.subheader("🏆 الدوريات الخاصة المسجل بها (Classic Leagues)")

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

# ---------------------------------------------------------
# 📊 تحليل التشكيلة والتقرير اليومي
# ---------------------------------------------------------
elif category == "📊 تحليل التشكيلة والتقرير اليومي":
  st.header("📊 تحليل التشكيلة بالأسعار والدقة الحية")

  expert_tweets = st.text_area(
      "📥 لصق تغريدات الخبراء للدمج مع التقرير (اختياري):",
      placeholder="ضع هنا تغريدات الخبراء لمطابقتها مع تشكيلتك...",
      height=80,
  )

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🚀 جلب وتحليل التشكيلة بـ ID"):
      with st.spinner("جاري جلب أسعار اللاعبين وتشكيلتك الحية من FPL API..."):
        squad, err = fetch_manager_squad(secrets_fpl_id)
        if err:
          st.error(err)
        else:
          st.session_state["squad_data"] = squad
          squad_txt = ", ".join([
              f"{p['name']} (فريق: {p['team']} - سعر حقيقي: £{p['price']}M - "
              f"ملكية: {p['selected_by']}%)"
              for p in squad
          ])
          ai_prompt = (
              "تشكيلة المستخدم الرسمية والحية لموسم 2026/2027 بالأسعار"
              f" المحددة هي: [{squad_txt}].\nقدم تحليلاً شاملاً للتشكيلة،"
              " واقتراح البدلاء والكابتن بناءً على صعوبة المواجهات القادمة"
              " والأسعار المرفقة حصراً."
          )

          with st.spinner("جاري التنسيق مع OpenAI وتحليل البيانات الحية..."):
            st.session_state["cached_analysis"] = ask_openai(
                ai_prompt, extra_context=expert_tweets
            )

    if "squad_data" in st.session_state:
      squad = st.session_state["squad_data"]
      st.subheader("🟢 التشكيلة الأساسية والأسعار الرسمية")
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
              " (C)" if p["is_captain"] else (" (V)" if p["is_vice"] else "")
          )
          p_name = p["name"]
          p_team = p["team"]
          p_price = p["price"]
          st.markdown(
              f'<div class="player-card">{p_name}{cap_tag}<span>{p_team}</span><div'
              f' class="price">£{p_price}M</div></div>',
              unsafe_allow_html=True,
          )
        st.markdown("</div>", unsafe_allow_html=True)
      st.markdown("</div>", unsafe_allow_html=True)

      st.write("**دكة البدلاء والأسعار:**")
      bench_names = [f"{p['name']} (£{p['price']}M)" for p in bench]
      st.info(" | ".join(bench_names))

      st.markdown("---")
      st.subheader("🤖 تقرير الخبير المباشر ومستوى صعوبة المباريات")
      if "cached_analysis" in st.session_state:
        st.markdown(st.session_state["cached_analysis"])

# ---------------------------------------------------------
# 🔄 مخطط التبديلات الموصى بها
# ---------------------------------------------------------
elif category == "🔄 مخطط التبديلات الموصى بها للجولة":
  st.header("🔄 قسم التبديلات الموصى بها ومواجهات المباريات")

  expert_input = st.text_area(
      "📥 لصق تغريدات الخبراء للتبديلات (اختياري):",
      placeholder="ضع هنا تغريدات الخبراء لمراعاتها عند حساب التبديل...",
      height=80,
  )

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🔍 حساب أفضل 2 تبديلات بالجولة"):
      with st.spinner("جاري مقارنة الأسعار ومستويات الصعوبة..."):
        squad, err = fetch_manager_squad(secrets_fpl_id)
        if err:
          st.error(err)
        else:
          squad_txt = ", ".join([
              f"{p['name']} ({p['pos']} - {p['team']} - £{p['price']}M)"
              for p in squad
          ])
          transfer_prompt = f"""
                    تشكيلة المستخدم الحالية وأسعارها الرسمية: [{squad_txt}].
                    
                    بناءً على الأسعار المرفقة وجدول الصعوبة المباشر:
                    1. رشح أفضل تبديل ضروري (اللاعب الخروج والبديل والسعر ومستوى صعوبة المباراة).
                    2. رشح تبديل تفاضلي اختياري.
                    """
          st.session_state["cached_transfers"] = ask_openai(
              transfer_prompt, extra_context=expert_input
          )

    if "cached_transfers" in st.session_state:
      st.markdown(st.session_state["cached_transfers"])

# ---------------------------------------------------------
# 👑 مصفوفة الكابتن ومستوى المباريات
# ---------------------------------------------------------
elif category == "👑 مصفوفة الكابتن ومستوى المباريات":
  st.header("👑 أفضل خيارات الكابتن بناءً على صعوبة المواجهة")
  if st.button("🚀 تحليل خيارات الكابتن للجولة"):
    with st.spinner("جاري تحليل مواجهات النجوم وصعوبة المباريات..."):
      res = ask_openai(
          "من هم أفضل 3 مرشحين لشارة الكابتن للجولة القادمة بناءً على قائمة"
          " نجوم الدوري المرفقة بالأسعار المحددة حصراً؟ اعرض الكابتن مع توضيح"
          " سعره وخياره الآمن والتفاضلي."
      )
      st.markdown(res)

# ---------------------------------------------------------
# باقي الأقسام
# ---------------------------------------------------------
elif category == "💬 المساعد الصوتي والدردشة":
  st.header("🗣️ الدردشة مع مستشار الفانتسي")
  if "messages" not in st.session_state:
    st.session_state.messages = []

  for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
      st.write(msg["content"])

  user_query = st.chat_input("اسأل عن أي لاعب أو خيار كابتن...")
  if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
      st.write(user_query)

    with st.chat_message("assistant"):
      with st.spinner("جاري التحليل..."):
        answer = ask_openai(user_query)
        st.write(answer)
        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

elif category == "🚑 رادار الإصابات والغيابات":
  st.header("🚑 رادار الإصابات والغيابات")
  if st.button("🚀 جلب تقرير الغيابات الرسمية"):
    with st.spinner("جاري فحص حالة اللاعبين حياً..."):
      res = ask_openai(
          "اعرض لي أهم اللاعبين المصابين أو المشكوك بمشاركتهم للجولة القادمة من"
          " فرق الدوري الإنجليزي الحالية."
      )
      st.markdown(res)

elif category == "🛡️ (EO) مؤشر الملكية المؤثرة":
  st.header("🛡️ المؤشر المؤثر للملكية (Effective Ownership)")
  player_input = st.text_input("ادخل اسم اللاعب:")
  if player_input:
    res = ask_openai(
        f"ما هي نسبة خطورة عدم امتلاك اللاعب {player_input} ومستوى صعوبة"
        " مبارياته القادمة بناءً على البيانات الرسمية المرفقة؟"
    )
    st.markdown(res)
