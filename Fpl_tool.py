import datetime
import os
import requests
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم العصري الفاخر (CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="BMS bot FPL 26/27",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
/* التصميم العام الداكن الفاخر */
.stApp { background: linear-gradient(135deg, #090014 0%, #150024 100%); color: #ffffff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }

/* شريط القائمة الجانبية العصري */
section[data-testid="stSidebar"] { 
    background: rgba(22, 0, 38, 0.95) !important; 
    border-right: 1px solid rgba(0, 255, 135, 0.2); 
    backdrop-filter: blur(10px);
}

/* الأزرار العصرية بنمط Neon */
div.stButton > button {
    background: linear-gradient(135deg, #00ff87 0%, #60efff 100%);
    color: #0d0118 !important; font-weight: 800 !important; font-size: 15px !important;
    border-radius: 12px !important; border: none !important; padding: 12px 24px !important;
    transition: all 0.3s ease; box-shadow: 0 4px 20px rgba(0, 255, 135, 0.35);
}
div.stButton > button:hover { 
    transform: translateY(-3px); 
    box-shadow: 0 6px 25px rgba(96, 239, 255, 0.6); 
}

/* حقول الإدخال والقوائم المنسدلة */
.stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
    background-color: rgba(36, 0, 56, 0.7) !important; 
    color: #ffffff !important; 
    border: 1px solid rgba(0, 255, 135, 0.4) !important; 
    border-radius: 10px !important;
}

/* صناديق الإحصائيات الفخمة */
.metric-box {
    background: linear-gradient(145deg, rgba(36, 0, 56, 0.8), rgba(20, 0, 35, 0.9)); 
    border: 1px solid rgba(0, 255, 135, 0.3); 
    border-radius: 16px;
    padding: 18px; text-align: center; margin-bottom: 12px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    backdrop-filter: blur(4px);
}
.metric-box h3 { color: #00ff87; margin: 0; font-size: 26px; font-weight: 700; }
.metric-box p { color: #b1c1d8; margin: 5px 0 0 0; font-size: 13px; font-weight: 600; }

/* الملعب وتصميم التشكيلة */
.pitch-container {
    background: linear-gradient(180deg, #165b33 0%, #0d3820 100%);
    border: 2px solid rgba(0, 255, 135, 0.5); 
    border-radius: 20px; padding: 25px 10px; margin-bottom: 20px;
    box-shadow: inset 0 0 30px rgba(0,0,0,0.5);
}
.pitch-row { display: flex; justify-content: space-evenly; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
.player-card {
    background: rgba(13, 1, 24, 0.92); color: #ffffff; 
    border: 1px solid rgba(0, 255, 135, 0.6);
    padding: 8px 12px; border-radius: 12px; text-align: center; font-size: 13px; min-width: 90px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
.player-card:hover { transform: scale(1.05); }
.player-card span { display: block; font-size: 10px; color: #00ff87; font-weight: bold; margin-top: 2px; }
.player-card .price { font-size: 10px; color: #60efff; font-weight: 600; }

/* عداد الديدلاين العصري */
.deadline-badge {
    background: linear-gradient(90deg, #ff4b4b, #ff7676);
    color: white; padding: 8px 16px; border-radius: 20px;
    font-weight: bold; display: inline-block; font-size: 14px;
    box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
    margin-bottom: 15px;
}
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


secrets_openai = (
    get_secret("OPENAI_API_KEY")
    or get_secret("openai_key")
    or get_secret("OPENAI_KEY")
)
secrets_fpl_id = get_secret("FPL_ID") or get_secret("fpl_id")

# ---------------------------------------------------------
# 3. القائمة الجانبية (Sidebar) العصرية
# ---------------------------------------------------------
with st.sidebar:
  st.markdown(
      "<h2 style='color: #00ff87; text-align: center;'>⚡ BMS bot</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #aaa; font-size: 12px;'>FPL"
      " Assistant 26/27</p>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

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
  st.markdown(
      "<div style='text-align: center; color: #60efff; font-size: 12px;'>تم"
      " تطوير النظام لأعلى معايير الدقة 🚀</div>",
      unsafe_allow_html=True,
  )


# ---------------------------------------------------------
# 4. وظائف جلب البيانات الحية من FPL API
# ---------------------------------------------------------
def get_json(url):
  try:
    res = requests.get(url, timeout=5)
    return res.json() if res.status_code == 200 else None
  except Exception:
    return None


@st.cache_data(ttl=60)
def fetch_live_fpl_data():
  static_data = get_json(
      "https://fantasy.premierleague.com/api/bootstrap-static/"
  )
  if not static_data:
    return None, None, None, None, None
  players = {p["id"]: p for p in static_data["elements"]}
  teams = {t["id"]: t["name"] for t in static_data["teams"]}
  types = {
      et["id"]: et["singular_name_short"] for et in static_data["element_types"]
  }

  # البحث عن الجولة القادمة وموعد الديدلاين
  events = static_data.get("events", [])
  next_deadline = None
  for ev in events:
    if ev.get("is_current") or ev.get("is_next"):
      next_deadline = ev.get("deadline_time")
      if ev.get("is_next"):
        break

  return players, teams, types, static_data, next_deadline


@st.cache_data(ttl=120)
def fetch_top_fpl_players_data():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return ""
  top_p = sorted(
      players.values(),
      key=lambda x: float(x.get("selected_by_percent", 0) or 0),
      reverse=True,
  )[:60]
  info = [
      f"- {p['web_name']} ({teams.get(p['team'])}): Price £{p['now_cost']/10}M,"
      f" Selected {p['selected_by_percent']}%"
      for p in top_p
  ]
  return "\n".join(info)


@st.cache_data(ttl=120)
def fetch_fixtures_difficulty():
  fixtures = get_json("https://fantasy.premierleague.com/api/fixtures/")
  if not fixtures:
    return ""
  upcoming = [f for f in fixtures if not f.get("finished", False)][:25]
  fdr_summary = []
  for f in upcoming:
    h_team = f.get("team_h")
    a_team = f.get("team_a")
    h_diff = f.get("team_h_difficulty", 3)
    a_diff = f.get("team_a_difficulty", 3)
    gw = f.get("event", 1)
    fdr_summary.append(
        f"GW {gw}: Team {h_team} (FDR: {h_diff}/5) vs Team {a_team} (FDR:"
        f" {a_diff}/5)"
    )
  return "\n".join(fdr_summary[:15])


@st.cache_data(ttl=60)
def fetch_manager_info(manager_id):
  return get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/")


@st.cache_data(ttl=60)
def fetch_manager_squad(manager_id):
  players, teams, types, _, _ = fetch_live_fpl_data()
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
        "pos": types.get(
            p_info.get("element_type"), "MID"
        ),  # GKP, DEF, MID, FWD
        "element_type": p_info.get("element_type", 3),
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
# 5. دوال الاتصال بـ OpenAI مع حظر الهلوسة وإلزام المراكز الحقيقية
# ---------------------------------------------------------
SYSTEM_PROMPT = """
أنت مدير ومنصة الذكاء الاصطناعي الاحترافية BMS bot FPL 26/27 لموسم 2026/2027.
تعتمد تحليلاتك حصرياً على البيانات المباشرة والواقعية لـ FPL API.

قواعد صارمة جداً:
1. ممنوع منعاً باتاً اقتراح تبديل لاعب بغير مركزه (مثلاً: استبدال مهاجم بلاعب وسط أو العكس غير مسموح؛ المدافع يُبدل بمدافع، والوسط بوسط، والمهاجم بمهاجم).
2. لا توجد أي إصابات وهمية؛ تعامل حصرياً مع حالة اللاعبين الحقيقية في الـ API.
3. التزم بالأندية والأسعار الرسمية المرفقة في السياق (منع تام لهاري كين أو انتقال صلاح لطرابزون وما شابه).
4. استخدم خيارات الخبراء العرب للاسترشاد الاستراتيجي: (@ali7amer, @adelculer, @fplab17, @arabsfpl, @fpljoker1, @fpl_ucf, @kluivertq8).
5. اكتب الردود بأسلوب احترافي وعصري باللغة العربية الفصحى.
"""


def ask_openai(prompt_text, extra_context=""):
  if not secrets_openai:
    return (
        "⚠️ يرجى إدخال مفتاح OpenAI API في القائمة الجانبية أو في متغيرات"
        " Railway."
    )

  try:
    client = OpenAI(api_key=secrets_openai)
    fdr_data = fetch_fixtures_difficulty()
    live_players = fetch_top_fpl_players_data()

    full_prompt = (
        f"{prompt_text}\n\n"
        f"📊 [قائمة أهم لاعبي الفانتسي بالأسعار والأندية الحقيقية]:\n{live_players}\n\n"
        f"📅 [بيانات صعوبة المباريات FDR]:\n{fdr_data}"
    )
    if extra_context:
      full_prompt += f"\n\n📌 [تحليلات الخبراء المرفقة]:\n{extra_context}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )

    if response.choices and response.choices[0].message.content:
      return response.choices[0].message.content.strip()

  except Exception as e:
    return f"⚠️ خطأ في الاتصال بـ OpenAI: {str(e)}"

  return "⚠️ تعذر الحصول على رد من النظام."


# ---------------------------------------------------------
# 6. الواجهة الرئيسية والتنقل العصري
# ---------------------------------------------------------
st.markdown(
    "<h1 style='text-align: center; color: #00ff87; margin-bottom: 0;'>⚽ BMS"
    " bot FPL 26/27</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #b1c1d8; font-size: 16px; margin-top:"
    " 5px;'>المنصة الذكية المتقدمة لإدارة وفحص فريق الفانتسي بلحظيتها</p>",
    unsafe_allow_html=True,
)

# عرض عداد الديدلاين التنازلي تحت العنوان
_, _, _, _, deadline_str = fetch_live_fpl_data()
if deadline_str:
  try:
    # صيغة الديدلاين من API مثل: 2026-08-29T10:30:00Z
    dl_dt = datetime.datetime.strptime(
        deadline_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S"
    )
    now_dt = datetime.datetime.utcnow()
    diff = dl_dt - now_dt
    if diff.total_seconds() > 0:
      days = diff.days
      hours = divmod(diff.seconds, 3600)[0]
      minutes = divmod(divmod(diff.seconds, 3600)[1], 60)[0]
      st.markdown(
          "<div style='text-align: center;'><div"
          f" class='deadline-badge'>⏳ المتبقي للديدلاين القادم: {days} أيام,"
          f" {hours} ساعات، {minutes} دقائق</div></div>",
          unsafe_allow_html=True,
      )
  except Exception:
    pass

st.markdown("---")

category = st.selectbox(
    "📍 اختر قسم العمل المطلوب:",
    [
        "🏠 لوحة التحكم الرئيسية والدوريات",
        "📊 تحليل التشكيلة وحالة الفريق الحية",
        "🔄 مخطط التبديلات الذكي (بالمراكز الدقيقة)",
        "👑 مصفوفة الكابتن الاستراتيجية",
        "💬 المساعد الذكي والدردشة الفورية",
        "🚑 تقرير الإصابات والغيابات الموثوق",
        "🛡️ (EO) مؤشر الملكية المؤثرة",
    ],
)

# ---------------------------------------------------------
# 🏠 الصفحة الرئيسية: نقاطي والدوريات
# ---------------------------------------------------------
if category == "🏠 لوحة التحكم الرئيسية والدوريات":
  st.header("🏠 لوحة التحكم الشخصية")

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID الخاص بك في القائمة الجانبية.")
  else:
    entry_data = fetch_manager_info(secrets_fpl_id)
    if not entry_data:
      st.error("تعذر جلب بيانات الفريق. تأكد من صحة رقم ID.")
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
            f'<div class="metric-box"><h3>{gw_pts}</h3><p>نقاط الجولة</p></div>',
            unsafe_allow_html=True,
        )
      with col4:
        st.markdown(
            f'<div class="metric-box"><h3>{team_name}</h3><p>{f_name}'
            f' {l_name}</p></div>',
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
      else:
        st.info("لا توجد دوريات خاصة مسجلة لهذا الحساب.")

# ---------------------------------------------------------
# 📊 تحليل التشكيلة والتقرير اليومي
# ---------------------------------------------------------
elif category == "📊 تحليل التشكيلة وحالة الفريق الحية":
  st.header("📊 تحليل التشكيلة المعروضة في الملعب")

  expert_tweets = st.text_area(
      "📥 لصق تغريدات الخبراء للدمج التحليلي (اختياري):",
      placeholder="ضع هنا تغريدات الخبراء لمطابقتها مع تشكيلتك...",
      height=80,
  )

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🚀 جلب وتحليل التشكيلة الحية"):
      with st.spinner("جاري جلب تفاصيل التشكيلة والأسعار والجاهزية البدنية..."):
        squad, err = fetch_manager_squad(secrets_fpl_id)
        if err:
          st.error(err)
        else:
          st.session_state["squad_data"] = squad
          squad_txt = ", ".join([
              f"{p['name']} ({p['pos']} - فريق: {p['team']} - £{p['price']}M - الحالة:"
              f" {p['status']})"
              for p in squad
          ])
          ai_prompt = (
              "تشكيلة المستخدم الرسمية والحية لموسم 2026/2027 هي:"
              f" [{squad_txt}].\nقدم تحليلاً تكتيكياً شاملاً لأداء الفريق,"
              " وجهوزية اللاعبين الحقيقية، واقترح التعديلات والبدلاء بناءً على"
              " صعوبة المباريات والأسعار حصراً."
          )

          with st.spinner("جاري إعداد التقرير المتقدم عبر BMS bot..."):
            st.session_state["cached_analysis"] = ask_openai(
                ai_prompt, extra_context=expert_tweets
            )

    if "squad_data" in st.session_state:
      squad = st.session_state["squad_data"]
      st.subheader("🟢 التشكيلة الأساسية على الملعب الافتراضي")
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

      st.write("**دكة البدلاء:**")
      bench_names = [
          f"{p['name']} ({p['pos']} - £{p['price']}M)" for p in bench
      ]
      st.info(" | ".join(bench_names))

      st.markdown("---")
      st.subheader("🤖 تقرير الخبير والتحليل التكتيكي الشامل")
      if "cached_analysis" in st.session_state:
        st.markdown(st.session_state["cached_analysis"])

# ---------------------------------------------------------
# 🔄 مخطط التبديلات الذكي (بالمراكز الدقيقة)
# ---------------------------------------------------------
elif category == "🔄 مخطط التبديلات الذكي (بالمراكز الدقيقة)":
  st.header("🔄 قسم التبديلات الذكية (مع مراعاة مطابقة المراكز بدقة)")

  expert_input = st.text_area(
      "📥 ملاحظات وتحليلات الخبراء للتبديلات (اختياري):",
      placeholder="ضع هنا التغريدات أو الأخبار لمراعاتها في حساب التبديل...",
      height=80,
  )

  if not secrets_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🔍 حساب أفضل التبديلات المتاحة"):
      with st.spinner("جاري فحص الميزانية ومطابقة المراكز..."):
        squad, err = fetch_manager_squad(secrets_fpl_id)
        if err:
          st.error(err)
        else:
          squad_txt = ", ".join([
              f"{p['name']} ({p['pos']} - فريق: {p['team']} - £{p['price']}M)"
              for p in squad
          ])
          transfer_prompt = f"""
                    تشكيلة المستخدم الحالية وأسعارها ومراكزها: [{squad_txt}].
                    
                    تنبيه صارم: التبديل يجب أن يكون حصرياً داخل نفس المركز (مهاجم بمهاجم، وسط بوسط، مدافع بمدافع، حارس بحارس). لا تقم أبداً بتبديل مهاجم بلاعب وسط أو العكس.
                    بناءً على جدول صعوبة المباريات المباشر:
                    1. حدد أفضل تبديل ضروري مع ذكر اسم اللاعب المغادر، واللاعب البديل بدقة في نفس المركز، وسعره، ومستوى صعوبة مباراته القادمة.
                    2. حدد تبديل تفاضلي اختياري بنفس المركز.
                    """
          st.session_state["cached_transfers"] = ask_openai(
              transfer_prompt, extra_context=expert_input
          )

    if "cached_transfers" in st.session_state:
      st.markdown(st.session_state["cached_transfers"])

# ---------------------------------------------------------
# 👑 مصفوفة الكابتن الاستراتيجية
# ---------------------------------------------------------
elif category == "👑 مصفوفة الكابتن الاستراتيجية":
  st.header("👑 أفضل خيارات الشارة (الكابتن) للجولة القادمة")
  if st.button("🚀 تحليل خيارات الكابتن المتاحة"):
    with st.spinner("جاري تحليل المواجهات وصعوبة الخصوم..."):
      res = ask_openai(
          "من هم أفضل 3 مرشحين لشارة الكابتن للجولة القادمة بناءً على جدول"
          " صعوبة المباريات (FDR) ومستويات النجوم الحالية؟ وضح خياراً آمناً"
          " وخياراً تفاضلياً باللغة العربية الفصحى."
      )
      st.markdown(res)

# ---------------------------------------------------------
# 💬 المساعد الذكي والدردشة الفورية
# ---------------------------------------------------------
elif category == "💬 المساعد الذكي والدردشة الفورية":
  st.header("🗣️ الدردشة الفورية مع BMS bot")
  if "messages" not in st.session_state:
    st.session_state.messages = []

  for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
      st.write(msg["content"])

  user_query = st.chat_input("اسأل عن أي لاعب، مقارنة، أو خطة تبديل...")
  if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
      st.write(user_query)

    with st.chat_message("assistant"):
      with st.spinner("جاري معالجة السؤال..."):
        answer = ask_openai(user_query)
        st.write(answer)
        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

# ---------------------------------------------------------
# 🚑 رادار الإصابات والغيابات الموثوق
# ---------------------------------------------------------
elif category == "🚑 تقرير الإصابات والغيابات الموثوق":
  st.header("🚑 رادار الإصابات والغيابات الرسمية")
  if st.button("🚀 فحص الغيابات وحالة اللاعبين"):
    with st.spinner("جاري جلب التقارير الطبية الرسمية من FPL..."):
      res = ask_openai(
          "اعرض لي قائمة بأهم اللاعبين المصابين أو المشكوك بمشاركتهم (الذين"
          " لديهم حالة غير جاهزة في الـ API) للجولة القادمة مع توضيح تأثير"
          " غيابهم تكتيكياً."
      )
      st.markdown(res)

# ---------------------------------------------------------
# 🛡️ (EO) مؤشر الملكية المؤثرة
# ---------------------------------------------------------
elif category == "🛡️ (EO) مؤشر الملكية المؤثرة":
  st.header("🛡️ المؤشر المؤثر للملكية (Effective Ownership)")
  player_input = st.text_input("أدخل اسم اللاعب لفحص نسبة ملكيته ومخاطرته:")
  if player_input:
    res = ask_openai(
        f"ما هي نسبة ملكية اللاعب {player_input} وما هو تأثير عدم امتلاكه"
        " على الترتيب العام والعوائد الهجومية?"
    )
    st.markdown(res)
