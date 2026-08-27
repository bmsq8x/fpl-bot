import datetime
import os
import requests
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------
# 1. إعدادات الصفحة والدعم الكامل للغة العربية (RTL)
# ---------------------------------------------------------
st.set_page_config(
    page_title="BMS bot FPL 26/27",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.stApp { 
    background: linear-gradient(135deg, #090014 0%, #150024 100%) !important; 
    color: #ffffff !important; 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    direction: rtl; 
    text-align: right;
}
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="column"] { direction: rtl; text-align: right; }

div.stButton > button {
    background: linear-gradient(135deg, #00ff87 0%, #60efff 100%);
    color: #0d0118 !important; font-weight: 800 !important; font-size: 15px !important;
    border-radius: 14px !important; border: none !important; padding: 12px 24px !important;
    transition: all 0.3s ease; box-shadow: 0 4px 20px rgba(0, 255, 135, 0.4);
    width: 100%;
}
div.stButton > button:hover { 
    transform: translateY(-3px); 
    box-shadow: 0 6px 25px rgba(96, 239, 255, 0.7); 
}

.stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
    background-color: rgba(36, 0, 56, 0.6) !important; 
    color: #ffffff !important; 
    border: 1px solid rgba(0, 255, 135, 0.4) !important; 
    border-radius: 12px !important;
    text-align: right;
}

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
# 2. وظائف جلب البيانات الحية من سيرفر FPL الرسمي
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
      :10
  ]
  return differentials


@st.cache_data(ttl=3600)
def fetch_injured_players_from_api():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return []
  injured_list = []
  for p in players.values():
    status = p.get("status", "a")
    news = p.get("news", "")
    if status != "a":
      injured_list.append({
          "اللاعب": p.get("web_name", "لاعب"),
          "الفريق": teams.get(p.get("team"), ""),
          "السعر": f"£{round(p.get('now_cost', 0) / 10.0, 1)}M",
          "الحالة": status,
          "نسبة المشاركة": f"{p.get('chance_of_playing_next_round', 0)}%",
          "السبب": news if news else "غير متوفر",
      })
  return injured_list


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
# 3. عقل الذكاء الاصطناعي مع فرض قراءة تشكيلة المستخدم بدقة
# ---------------------------------------------------------
SYSTEM_PROMPT = """
أنت مدير ومنصة الذكاء الاصطناعي الاحترافية BMS bot FPL 26/27 لموسم 2026/2027.
قواعد صارمة جداً:
1. اعتمد حصرياً على تشكيلة المستخدم الفعلية التي يتم تمريرها في كل طلب. لا تفترض وجود لاعبين وهميين، ولا تقترح استبدال لاعب هو أصلاً موجود في تشكيلة المستخدم الحالية!
2. التزم بأندية الدوري الإنجليزي الممتاز الحقيقية فقط (مثل محمد صلاح في ليفربول، ولا تقترح أي أندية خارج البريميرليغ مثل الدوري التركي أو الألماني).
3. قدم تحليلاتك وتبديلاتك واختيارات الكابتن مبنية 100% على تشكيلة المستخدم الحالية وجدول المباريات الرسمي (FDR) والعوائد المتوقعة (xGI).
"""


def ask_openai(prompt_text, squad_context=""):
  secrets_openai = os.environ.get("OPENAI_API_KEY", "")
  if not secrets_openai:
    return "⚠️ تنبيه: يرجى إضافة مفتاح OPENAI_API_KEY في متغيرات البيئة على Railway."
  try:
    client = OpenAI(api_key=secrets_openai)
    full_query = prompt_text
    if squad_context:
      full_query = (
          f"تشكيلة المستخدم الفعلية الحالية هي:\n[{squad_context}]\n\nطلب"
          f" المستخدم:\n{prompt_text}"
      )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_query},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()
  except Exception as e:
    return f"⚠️ خطأ في الاتصال: {str(e)}"


# ---------------------------------------------------------
# 4. واجهة العرض الرئيسية المرتبة
# ---------------------------------------------------------
st.markdown(
    "<h1 style='text-align: center; color: #00ff87; margin-bottom: 0;'>⚽ BMS"
    " bot FPL 26/27</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #b1c1d8; font-size: 15px; margin-top:"
    " 5px;'>المنصة الذكية المتقدمة لإدارة وفحص فريق الفانتسي بناءً على تشكيلتك"
    " الحية</p>",
    unsafe_allow_html=True,
)

col_top1, col_top2 = st.columns([1, 1])
with col_top1:
  user_fpl_id = st.text_input("⚽ أدخل معرف فريقك (FPL Team ID):", value="3427112")

with col_top2:
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
            "<div style='text-align: center; padding-top: 25px;'><div"
            f" class='deadline-badge'>⏳ المتبقي للديدلاين القادم: {days} أيام,"
            f" {hours} ساعات، {minutes} دقائق</div></div>",
            unsafe_allow_html=True,
        )
    except Exception:
      pass

st.markdown("---")

# جلب تشكيلة المستخدم تلقائياً لتكون متاحة لكل الأقسام
current_squad_text = ""
squad_objects, squad_err = fetch_manager_squad(user_fpl_id)
if squad_objects:
  current_squad_text = ", ".join([
      f"{p['name']} ({p['pos']} - {p['team']} - £{p['price']}M - حالة: {p['status']})"
      for p in squad_objects
  ])

# ---------------------------------------------------------
# 5. التبويبات المتكاملة
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🏠 لوحة التحكم",
    "📊 التشكيلة المرئية",
    "🔄 تحليل التبديلات",
    "👑 مستشار الكابتن",
    "💬 المساعد الذكي",
    "🚑 مرصد الإصابات",
    "📈 رادار الأسعار",
    "💎 كاشف التفاضليين",
    "🛡️ مؤشر الملكية EO",
])

with tab1:
  st.subheader("🏠 لوحة التحكم الشخصية والدوريات الخاصة")
  if not user_fpl_id:
    st.warning("⚠️ يرجى إدخال رقم FPL Team ID الخاص بك في الأعلى.")
  else:
    entry_data = fetch_manager_info(user_fpl_id)
    if not entry_data:
      st.error("تعذر جلب بيانات الفريق.")
    else:
      pts = entry_data.get("summary_overall_points", 0)
      rank = entry_data.get("summary_overall_rank", 0)
      gw_pts = entry_data.get("summary_event_points", 0)
      team_name = entry_data.get("name", "")
      c1, c2, c3, c4 = st.columns(4)
      c1.markdown(
          f'<div class="metric-box"><h3>{pts}</h3><p>إجمالي النقاط</p></div>',
          unsafe_allow_html=True,
      )
      c2.markdown(
          f'<div class="metric-box"><h3>{rank:,}</h3><p>الترتيب العام</p></div>',
          unsafe_allow_html=True,
      )
      c3.markdown(
          f'<div class="metric-box"><h3>{gw_pts}</h3><p>نقاط الجولة</p></div>',
          unsafe_allow_html=True,
      )
      c4.markdown(
          f'<div class="metric-box"><h3>{team_name}</h3><p>اسم الفريق</p></div>',
          unsafe_allow_html=True,
      )

      st.markdown("---")
      st.subheader("🏆 جدول الدوريات الخاصة (Classic Leagues)")
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
        st.info("لا توجد دوريات مسجلة.")

with tab2:
  st.subheader("📊 التشكيلة المرئية وحالة الجاهزية على الملعب")
  expert_tweets = st.text_area(
      "📥 ملاحظاتك أو توجهات الخبراء (اختياري لتحليل التشكيلة):", height=70
  )
  if not user_fpl_id:
    st.warning("⚠️ أدخل رقم FPL Team ID في الأعلى.")
  else:
    if st.button("🚀 عرض وتحليل التشكيلة الحية"):
      if squad_err:
        st.error(squad_err)
      else:
        st.session_state["squad_data"] = squad_objects
        st.session_state["cached_squad_analysis"] = ask_openai(
            f"حلل هذه التشكيلة بدقة استراتيجية تكتيكية. ملاحظات إضافية:"
            f" [{expert_tweets}]",
            squad_context=current_squad_text,
        )

    if squad_objects:
      starting_11 = [p for p in squad_objects if p["position"] <= 11]
      bench = [p for p in squad_objects if p["position"] > 11]

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
          badge_class = "badge-green" if p["status"] == "a" else "badge-red"
          status_text = "🟢 جاهز" if p["status"] == "a" else f"🔴 {p['status']}"
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
          + " | ".join([f"{p['name']} ({p['team']} - £{p['price']}M)" for p in bench])
      )
      if "cached_squad_analysis" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["cached_squad_analysis"])

with tab3:
  st.subheader(
      "🔄 تحليل التبديلات الذكية بناءً على تشكيلتك الحية وجداول الصعوبة"
  )
  if st.button("🔍 اقترح أفضل التبديلات لتشكيلتك الحية"):
    if not current_squad_text:
      st.error("تعذر جلب التشكيلة الحية للفريق.")
    else:
      res = ask_openai(
          "بناءً على تشكيلتي الحالية وأداء اللاعبين وجداول المباريات، اقترح"
          " تبديلين دقيقين (في نفس المركز) للتحسين.",
          squad_context=current_squad_text,
      )
      st.markdown(res)

with tab4:
  st.subheader("👑 خيارات الكابتن الموصى بها بناءً على تشكيلتك والخصوم")
  if st.button("🚀 تقييم واختيار أفضل كابتن من لاعبي فريقي"):
    if not current_squad_text:
      st.error("تعذر جلب التشكيلة الحية للفريق.")
    else:
      res = ask_openai(
          "من هم أفضل 3 مرشحين لشارة الكابتن (من بين لاعبي فريقي الحاليين أو كخيار"
          " متاح) للجولة القادمة بناءً على الإحصائيات المتقدمة xGI وصعوبة مباريات"
          " الخصم؟",
          squad_context=current_squad_text,
      )
      st.markdown(res)

with tab5:
  st.subheader("💬 الدردشة الفورية مع مستشار فانتسي الذكي")
  query = st.text_input("اسأل عن أي لاعب في تشكيلتك، خطة، أو وايلدكارد...")
  if query:
    ans = ask_openai(query, squad_context=current_squad_text)
    st.markdown(f"**BMS bot:** {ans}")

with tab6:
  st.subheader("🚑 مرصد الإصابات والغيابات الحقيقي (محدث من السيرفر)")
  if st.button("🔄 تحديث وعرض الإصابات النشطة"):
    injured = fetch_injured_players_from_api()
    if injured:
      st.table(injured)
    else:
      st.success("🟢 لا توجد إصابات مؤثرة حالياً.")

with tab7:
  st.subheader("📈 رادار تغير الأسعار في السوق (أبرز الارتفاعات والانخفاضات)")
  rising, falling = fetch_price_changes_radar()
  col_r1, col_r2 = st.columns(2)
  with col_r1:
    st.markdown("#### 🔥 الأقرب لارتفاع السعر")
    for p in rising:
      st.write(
          f"- **{p['web_name']}** (السعر: £{p['now_cost']/10}M) - تغير حدث:"
          f" {p.get('cost_change_event', 0)}"
      )
  with col_r2:
    st.markdown("#### ❄️ الأكثر عرضة لانخفاض السعر")
    for p in falling:
      st.write(
          f"- **{p['web_name']}** (السعر: £{p['now_cost']/10}M) - تغير حدث:"
          f" {p.get('cost_change_event', 0)}"
      )

with tab8:
  st.subheader("💎 كاشف التفاضلي الذهبي (ملكية أقل من 8%)")
  diffs = fetch_differential_finders()
  if diffs:
    diff_table = []
    for d in diffs:
      diff_table.append({
          "اللاعب": d["name"],
          "الفريق": d["team"],
          "السعر": f"£{d['price']}M",
          "نسبة الملكية": f"{d['sel']}%",
          "إجمالي النقاط": d["pts"],
      })
    st.table(diff_table)
  else:
    st.info("جاري تحليل اللاعبين التفاضليين...")

with tab9:
  st.subheader("🛡️ تحليل تأثير ملكية اللاعبين (Effective Ownership - EO)")
  player_name = st.text_input("أدخل اسم اللاعب لفحص خطورة عدم امتلاكه:")
  if player_name:
    ans = ask_openai(
        f"ما هي المخاطر والتأثيرات الناتجة عن عدم امتلاك اللاعب {player_name}"
        f" بين النخبة والترتيب العام؟",
        squad_context=current_squad_text,
    )
    st.markdown(ans)
