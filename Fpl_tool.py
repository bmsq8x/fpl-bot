import datetime
import os
import requests
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------
# 1. إعدادات الصفحة والثيمات البصرية العصرية (Glassmorphism & Neon)
# ---------------------------------------------------------
st.set_page_config(
    page_title="BMS bot FPL 26/27",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
/* خلفيات وزجاج معمد عصري */
.stApp { background: linear-gradient(135deg, #090014 0%, #150024 100%) !important; color: #ffffff !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
section[data-testid="stSidebar"] { 
    background: rgba(22, 0, 38, 0.95) !important; 
    border-right: 1px solid rgba(0, 255, 135, 0.2); 
    backdrop-filter: blur(12px);
}

/* الأزرار العصرية بنمط التوهج النيون */
div.stButton > button {
    background: linear-gradient(135deg, #00ff87 0%, #60efff 100%);
    color: #0d0118 !important; font-weight: 800 !important; font-size: 15px !important;
    border-radius: 14px !important; border: none !important; padding: 12px 24px !important;
    transition: all 0.3s ease; box-shadow: 0 4px 20px rgba(0, 255, 135, 0.4);
}
div.stButton > button:hover { 
    transform: translateY(-3px); 
    box-shadow: 0 6px 25px rgba(96, 239, 255, 0.7); 
}

/* حقول الإدخال الزجاجية */
.stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
    background-color: rgba(36, 0, 56, 0.6) !important; 
    color: #ffffff !important; 
    border: 1px solid rgba(0, 255, 135, 0.4) !important; 
    border-radius: 12px !important;
}

/* صناديق الإحصائيات الفخمة */
.metric-box {
    background: linear-gradient(145deg, rgba(36, 0, 56, 0.85), rgba(20, 0, 35, 0.95)); 
    border: 1px solid rgba(0, 255, 135, 0.3); 
    border-radius: 16px;
    padding: 18px; text-align: center; margin-bottom: 12px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    backdrop-filter: blur(6px);
}
.metric-box h3 { color: #00ff87; margin: 0; font-size: 26px; font-weight: 700; }
.metric-box p { color: #b1c1d8; margin: 5px 0 0 0; font-size: 13px; font-weight: 600; }

/* الملعب وتصميم التشكيلة الزجاجي */
.pitch-container {
    background: linear-gradient(180deg, #165b33 0%, #0d3820 100%);
    border: 2px solid rgba(0, 255, 135, 0.5); 
    border-radius: 20px; padding: 25px 10px; margin-bottom: 20px;
    box-shadow: inset 0 0 35px rgba(0,0,0,0.6);
}
.pitch-row { display: flex; justify-content: space-evenly; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
.player-card {
    background: rgba(13, 1, 24, 0.92); color: #ffffff; 
    padding: 8px 12px; border-radius: 14px; text-align: center; font-size: 13px; min-width: 95px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    transition: transform 0.2s ease;
}
.player-card:hover { transform: scale(1.06); }
.player-card span { display: block; font-size: 10px; font-weight: bold; margin-top: 2px; }
.player-card .price { font-size: 10px; color: #60efff; font-weight: 600; }
.badge-green { border: 2px solid #00ff87; }
.badge-red { border: 2px solid #ff4b4b; }

/* شارة الديدلاين */
.deadline-badge {
    background: linear-gradient(90deg, #ff4b4b, #ff7676);
    color: white; padding: 8px 18px; border-radius: 20px;
    font-weight: bold; display: inline-block; font-size: 14px;
    box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
    margin-bottom: 15px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. وظائف جلب البيانات الحية (تتحدث تلقائياً كل ساعة ttl=3600)
# ---------------------------------------------------------
def get_json(url):
  try:
    res = requests.get(url, timeout=5)
    return res.json() if res.status_code == 200 else None
  except Exception:
    return None


@st.cache_data(ttl=3600)
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

  events = static_data.get("events", [])
  next_deadline = None
  for ev in events:
    if ev.get("is_current") or ev.get("is_next"):
      next_deadline = ev.get("deadline_time")
      if ev.get("is_next"):
        break

  return players, teams, types, static_data, next_deadline


@st.cache_data(ttl=3600)
def fetch_price_changes_radar():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return [], []
  rising = sorted(
      players.values(),
      key=lambda x: int(x.get("cost_change_event", 0)),
      reverse=True,
  )[:5]
  falling = sorted(
      players.values(), key=lambda x: int(x.get("cost_change_event", 0))
  )[:5]
  return rising, falling


@st.cache_data(ttl=3600)
def fetch_differential_finders():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return []

  differentials = []
  for p in players.values():
    try:
      sel = float(p.get("selected_by_percent", "0") or 0)
      pts = int(p.get("total_points", 0))
      if 0.5 < sel < 8.0 and pts > 10:
        differentials.append({
            "name": p.get("web_name"),
            "team": teams.get(p.get("team")),
            "sel": sel,
            "pts": pts,
            "price": round(p.get("now_cost", 0) / 10.0, 1),
        })
    except Exception:
      continue

  differentials = sorted(differentials, key=lambda x: x["pts"], reverse=True)[
      :8
  ]
  return differentials


@st.cache_data(ttl=3600)
def fetch_injured_players_from_api():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return "لا توجد بيانات متاحة حالياً."
  injured_list = []
  for p in players.values():
    status = p.get("status", "a")
    news = p.get("news", "")
    if status != "a":
      name = p.get("web_name", "لاعب")
      team_name = teams.get(p.get("team"), "")
      price = round(p.get("now_cost", 0) / 10.0, 1)
      chance = p.get("chance_of_playing_next_round", 0)
      injured_list.append(
          f"- {name} ({team_name}) - السعر: £{price}M - الحالة: {status}"
          f" (نسبة المشاركة: {chance}%) - السبب: {news}"
      )
  if not injured_list:
    return "🟢 لا توجد أي إصابات أو غيابات مؤثرة مسجلة حالياً في السيرفر الرسمي."
  return "\n".join(injured_list)


@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=3600)
def fetch_manager_info(manager_id):
  return get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/")


@st.cache_data(ttl=3600)
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
    status = p_info.get("status", "a")
    squad.append({
        "name": p_info.get("web_name", "لاعب"),
        "team": teams.get(p_info.get("team"), ""),
        "pos": types.get(p_info.get("element_type"), "MID"),
        "is_captain": pick.get("is_captain", False),
        "is_vice": pick.get("is_vice_captain", False),
        "position": pick.get("position", 1),
        "price": exact_price,
        "selected_by": p_info.get("selected_by_percent", "0.0"),
        "status": status,
        "news": p_info.get("news", ""),
    })
  return squad, None


# ---------------------------------------------------------
# 3. القائمة الجانبية (Sidebar) الآمنة
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

  user_fpl_id = st.text_input(
      "معرف فريقك (FPL Team ID):", placeholder="مثال: 3427112"
  )

  st.markdown("---")
  st.markdown(
      "<div style='text-align: center; color: #60efff; font-size: 12px;'>النظام"
      " آمن ويتحدث تلقائياً كل ساعة 🚀</div>",
      unsafe_allow_html=True,
  )


# ---------------------------------------------------------
# 4. الاتصال بـ OpenAI مع دمج تحليل الفرق العشرين واستراتيجيات النخبة وحسابات إكس الجديدة
# ---------------------------------------------------------
SYSTEM_PROMPT = """
أنت مدير ومنصة الذكاء الاصطناعي الاحترافية BMS bot FPL 26/27 لموسم 2026/2027.
تعتمد تحليلاتك على قاعدة بيانات تكتيكية شاملة لكل فرق الدوري الإنجليزي الـ 20 وسلوكيات نخبة الـ 100 مدرب:

أولاً: التحليل التكتيكي للفرق الـ 20:
- مانشستر سيتي (بيب جوارديولا): استحواذ، ضغط عكسي، وتواجد هالاند الدائم في قلب الصندوق (أعلى xG).
- أرسنال (ميكل أرتيتا): تنظيم دفاعي صلب، خطورة كرات ثابتة، اختراق الأطراف عبر ساكا ونقاط نظافة شباك عالية للمدافعين.
- ليفربول (أرني سلوت): تحولات عمودية، لُعب مباشر، ومحمد صلاح محور المساهمات الهجومية وصناعة الفرص (xGI).
- أندية المربع الذهبي (تشيلسي، توتنهام، أستون فيلا، نيوكاسل): إيقاع هجومي مفتوح وتواجد عناصر مثل بالمر وسون وإيساك بين خطوط الخصم.
- أندية الوسط والكتل المنخفضة والمتوسطة: إغلاق المساحات، استغلال المرتدات، والاعتماد على مدافعي الاعتراضات والشتت (Clearances/Blocks).
- أندية معركة البقاء: دفاع متأخر، كرات طويلة، وخط دفاع وحراس بمعدلات تصديات عالية.

ثانياً: استراتيجيات نخبة الـ 100 مدرب (آخر 5 مواسم):
1. التخطيط طويل المدى بناءً على تحولات جدول الصعوبة (Fixture Swings).
2. الاعتماد على العوائد والأرقام المتوقعة (xGI) لا النقاط الماضية أو العاطفة.
3. تفادي الخصومات السالبة (-4/-8) إلا للضرورة القصوى.
4. التوقيت الدقيق لاقتناص اللاعبين التفاضليين (Differentials) ذوي الملكية المنخفضة (<8%).

قواعد صارمة جداً:
- منع تام لهلوسة الإصابات: اعتمد حصرياً على قائمة الإصابات الحقيقية الواردة من السيرفر.
- تبديلات دقيقة حصرياً في نفس المركز (مهاجم بمهاجم، وسط بوسط، مدافع بمدافع، حارس بحارس).
- الالتزام التام بالأسعار والأندية الرسمية المرفقة.
- الاسترشاد برؤى وتحليلات كبار الخبراء ومصادر منصة إكس: (@ali7amer, @adelculer, @fplab17, @arabsfpl, @fpljoker1, @fpl_ucf, @kluivertq8, @fantasypro__, @fpl_q8_, @FPLUPdates_Tips, @fplfocal, @FPL_brandon, @mark_FPL).
- أخرج التقرير باللغة العربية الفصحى الاحترافية والداعمة بالأرقام والتكتيك.
"""


def ask_openai(prompt_text, extra_context=""):
  secrets_openai = os.environ.get("OPENAI_API_KEY", "")
  if not secrets_openai:
    return "⚠️ تنبيه: يرجى إضافة مفتاح OPENAI_API_KEY في متغيرات البيئة على Railway."

  try:
    client = OpenAI(api_key=secrets_openai)
    fdr_data = fetch_fixtures_difficulty()
    live_players = fetch_top_fpl_players_data()
    injured_data = fetch_injured_players_from_api()

    full_prompt = (
        f"{prompt_text}\n\n[الإصابات الحقيقية]:\n{injured_data}\n\n[أبرز"
        f" اللاعبين]:\n{live_players}\n\n[صعوبة المباريات FDR]:\n{fdr_data}"
    )
    if extra_context:
      full_prompt += f"\n\n📌 [تحليلات الخبراء والمصادر]:\n{extra_context}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    return response.choices[0].message.content.strip()
  except Exception as e:
    return f"⚠️ خطأ في الاتصال: {str(e)}"


# ---------------------------------------------------------
# 5. واجهة العرض الرئيسية
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

_, _, _, _, deadline_str = fetch_live_fpl_data()
if deadline_str:
  try:
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
        "🚑 تقرير الإصابات والغيابات الحقيقي",
        "📈 رادار تغير الأسعار في السوق",
        "💎 كاشف التفاضلي الذهبي (Differential Finder)",
        "🛡️ (EO) مؤشر الملكية المؤثرة",
    ],
)

# ---------------------------------------------------------
# الأقسام والأدوات
# ---------------------------------------------------------
if category == "🏠 لوحة التحكم الرئيسية والدوريات":
  st.header("🏠 لوحة التحكم الشخصية")
  if not user_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID الخاص بك في القائمة الجانبية.")
  else:
    entry_data = fetch_manager_info(user_fpl_id)
    if not entry_data:
      st.error("تعذر جلب بيانات الفريق.")
    else:
      pts = entry_data.get("summary_overall_points", 0)
      rank = entry_data.get("summary_overall_rank", 0)
      gw_pts = entry_data.get("summary_event_points", 0)
      team_name = entry_data.get("name", "")
      col1, col2, col3, col4 = st.columns(4)
      col1.markdown(
          f'<div class="metric-box"><h3>{pts}</h3><p>إجمالي النقاط</p></div>',
          unsafe_allow_html=True,
      )
      col2.markdown(
          f'<div class="metric-box"><h3>{rank:,}</h3><p>الترتيب العام</p></div>',
          unsafe_allow_html=True,
      )
      col3.markdown(
          f'<div class="metric-box"><h3>{gw_pts}</h3><p>نقاط الجولة</p></div>',
          unsafe_allow_html=True,
      )
      col4.markdown(
          f'<div class="metric-box"><h3>{team_name}</h3><p>اسم الفريق</p></div>',
          unsafe_allow_html=True,
      )

elif category == "📊 تحليل التشكيلة وحالة الفريق الحية":
  st.header("📊 تحليل التشكيلة وحالة الجاهزية البصرية")
  expert_tweets = st.text_area(
      "📥 لصق تغريدات الخبراء ومصادر إكس (اختياري):", height=80
  )
  if not user_fpl_id:
    st.warning("⚠️ أدخل رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🚀 جلب وتحليل التشكيلة الحية"):
      squad, err = fetch_manager_squad(user_fpl_id)
      if err:
        st.error(err)
      else:
        st.session_state["squad_data"] = squad
        squad_txt = ", ".join([
            f"{p['name']} ({p['pos']} - £{p['price']}M - حالة: {p['status']})"
            for p in squad
        ])
        st.session_state["cached_analysis"] = ask_openai(
            f"حلل هذه التشكيلة بناءً على دراسة تكتيكات الفرق الـ 20 واستراتيجيات"
            f" النخبة: [{squad_txt}]",
            extra_context=expert_tweets,
        )

    if "squad_data" in st.session_state:
      squad = st.session_state["squad_data"]
      st.subheader("🟢 الملعب الافتراضي (مع مؤشرات الجاهزية البصرية)")
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
          badge_class = "badge-green"
          status_text = "🟢 جاهز"
          if p["status"] != "a":
            badge_class = "badge-red"
            status_text = f"🔴 {p['status']}"

          st.markdown(
              f'<div class="player-card {badge_class}">{p["name"]}{cap_tag}'
              f"<span>{status_text}</span><div"
              f' class="price">£{p["price"]}M</div></div>',
              unsafe_allow_html=True,
          )
        st.markdown("</div>", unsafe_allow_html=True)
      st.markdown("</div>", unsafe_allow_html=True)

      st.write(
          "**دكة البدلاء:** "
          + " | ".join([f"{p['name']} (£{p['price']}M)" for p in bench])
      )
      if "cached_analysis" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["cached_analysis"])

elif category == "🔄 مخطط التبديلات الذكي (بالمراكز الدقيقة)":
  st.header(
      "🔄 قسم التبديلات الذكية (بناءً على تكتيكات الفرق وجداول الصعوبة)"
  )
  if not user_fpl_id:
    st.warning("⚠️ أدخل رقم FPL Team ID في القائمة الجانبية.")
  else:
    if st.button("🔍 حساب أفضل التبديلات المتاحة"):
      squad, err = fetch_manager_squad(user_fpl_id)
      if err:
        st.error(err)
      else:
        squad_txt = ", ".join([
            f"{p['name']} ({p['pos']} - £{p['price']}M)" for p in squad
        ])
        res = ask_openai(
            f"اقترح تبديلين حصرياً في نفس المركز للتشكيلة مستنداً لتحليل تواجدهم"
            f" في مناطق الخصم وجداول المباريات: [{squad_txt}]"
        )
        st.markdown(res)

elif category == "👑 مصفوفة الكابتن الاستراتيجية":
  st.header("👑 أفضل خيارات الكابتن بمنهجية النخبة وتحليل الفرق")
  if st.button("🚀 تحليل خيارات الكابتن"):
    st.markdown(
        ask_openai(
            "من هم أفضل 3 مرشحين لشارة الكابتن بناءً على تحليل أسلوب دفاع وهجوم"
            " الخصوم القادمين ومؤشرات الأداء المتوقع xGI؟"
        )
    )

elif category == "💬 المساعد الذكي والدردشة الفورية":
  st.header("🗣️ الدردشة الفورية مع BMS bot")
  query = st.chat_input("اسأل عن أي لاعب أو خطة...")
  if query:
    st.write(f"**أنت:** {query}")
    ans = ask_openai(query)
    st.write(f"**BMS bot:** {ans}")

elif category == "🚑 تقرير الإصابات والغيابات الحقيقي":
  st.header("🚑 تقرير الإصابات الموثوق من السيرفر")
  if st.button("🚀 عرض الإصابات المؤكدة"):
    st.markdown(fetch_injured_players_from_api())

elif category == "📈 رادار تغير الأسعار في السوق":
  st.header("📈 رادار تغير الأسعار في سوق الفانتسي")
  rising, falling = fetch_price_changes_radar()
  col_1, col_2 = st.columns(2)
  with col_1:
    st.subheader("🔥 الأبرز احتمالية لارتفاع السعر")
    for p in rising:
      st.write(
          f"- {p['web_name']} (السعر الحالي: £{p['now_cost']/10}M) 🟢"
      )
  with col_2:
    st.subheader("❄️ الأكثر عرضة لانخفاض السعر")
    for p in falling:
      st.write(
          f"- {p['web_name']} (السعر الحالي: £{p['now_cost']/10}M) 🔴"
      )

elif category == "💎 كاشف التفاضلي الذهبي (Differential Finder)":
  st.header("💎 كاشف التفاضلي الذهبي (ملكية أقل من 8%)")
  st.markdown(
      "أبرز اللاعبين ذوي الملكية المنخفضة والذين يقدمون عوائد تهديفية ممتازة"
      " لرفع ترتيبك الصاروخي بناءً على دراسة تكتيكات الفرق:"
  )
  diffs = fetch_differential_finders()
  if diffs:
    diff_data = []
    for d in diffs:
      diff_data.append({
          "اللاعب": d["name"],
          "الفريق": d["team"],
          "السعر": f"£{d['price']}M",
          "نسبة الملكية": f"{d['sel']}%",
          "إجمالي النقاط": d["pts"],
      })
    st.table(diff_data)
  else:
    st.info("جاري تحديث بيانات اللاعبين التفاضليين...")

elif category == "🛡️ (EO) مؤشر الملكية المؤثرة":
  st.header("🛡️ المؤشر المؤثر للملكية (Effective Ownership)")
  p_in = st.text_input("أدخل اسم اللاعب:")
  if p_in:
    st.markdown(ask_openai(f"ما هو تأثير ومخاطر عدم امتلاك اللاعب {p_in}?"))
