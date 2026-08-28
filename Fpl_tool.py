import datetime
import os
import requests
import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------
# إعدادات الصفحة والتصميم (RTL)
# ---------------------------------------------------------
st.set_page_config(
    page_title="BMS bot FPL 2026/2027",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

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

.transfer-box {
    background: rgba(36, 0, 56, 0.8);
    border: 1px solid #00ff87;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# طبقة الاتصال وجلب البيانات الآمنة (API Client)
# ---------------------------------------------------------
def get_json(url):
  try:
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code == 200:
      return res.json()
    return {}
  except Exception:
    return {}


@st.cache_data(ttl=3600)
def fetch_live_fpl_data():
  static_data = get_json(
      "https://fantasy.premierleague.com/api/bootstrap-static/"
  )
  if not static_data or "elements" not in static_data:
    return {}, {}, {}, {}, None
  players = {p["id"]: p for p in static_data.get("elements", [])}
  teams = {t["id"]: t["name"] for t in static_data.get("teams", [])}
  types = {
      et["id"]: et["singular_name_short"]
      for et in static_data.get("element_types", [])
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
def fetch_manager_info(manager_id):
  data = get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/")
  return data if data and "id" in data else None


@st.cache_data(ttl=3600)
def fetch_classic_league_standings(league_id):
  data = get_json(
      f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
  )
  return data if data and "standings" in data else None


@st.cache_data(ttl=3600)
def fetch_manager_squad(manager_id):
  players, teams, types, static_data, _ = fetch_live_fpl_data()
  if not players:
    return None, "تعذر جلب بيانات الفانتسي العامة حالياً من سيرفر FPL."
  entry_data = fetch_manager_info(manager_id)
  if not entry_data:
    return None, "رقم الفريق غير صحيح أو يتعذر الوصول له."

  events = static_data.get("events", []) if static_data else []
  current_gw = 1
  for ev in events:
    if ev.get("is_current"):
      current_gw = ev.get("id")
      break
    elif ev.get("is_next"):
      current_gw = max(1, ev.get("id") - 1)
      break

  picks_data = get_json(
      f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{current_gw}/picks/"
  )

  if not picks_data or "picks" not in picks_data:
    for gw in range(current_gw, 0, -1):
      picks_data = get_json(
          f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{gw}/picks/"
      )
      if picks_data and "picks" in picks_data:
        break

  if not picks_data or "picks" not in picks_data:
    return None, "تعذر جلب تشكيلة الفريق. تأكد من صحة رقم FPL Team ID."

  squad = []
  for pick in picks_data.get("picks", []):
    p_info = players.get(pick["element"], {})
    exact_price = round(p_info.get("now_cost", 0) / 10.0, 1)
    status = p_info.get("status", "a")
    p_name = p_info.get("web_name", "لاعب")
    team_name = teams.get(p_info.get("team"), "الدوري الإنجليزي")

    total_pts = int(p_info.get("total_points", 0) or 0)
    form_val = float(p_info.get("form", "0.0") or 0.0)
    math_score_val = total_pts + (form_val * 10)

    squad.append({
        "id": pick["element"],
        "name": p_name,
        "team": team_name,
        "pos": types.get(p_info.get("element_type"), "MID"),
        "element_type": p_info.get("element_type"),
        "is_captain": pick.get("is_captain", False),
        "is_vice": pick.get("is_vice_captain", False),
        "position": pick.get("position", 1),
        "price": exact_price,
        "selected_by": p_info.get("selected_by_percent", "0.0"),
        "status": status,
        "total_points": total_pts,
        "form": form_val,
        "math_score": math_score_val,
        "news": p_info.get("news", ""),
    })
  return squad, None


@st.cache_data(ttl=3600)
def fetch_price_changes_radar():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return [], [], {}
  rising = sorted(
      players.values(),
      key=lambda x: int(x.get("cost_change_event", 0) or 0),
      reverse=True,
  )[:5]
  falling = sorted(
      players.values(),
      key=lambda x: int(x.get("cost_change_event", 0) or 0),
  )[:5]
  return rising, falling, teams


@st.cache_data(ttl=3600)
def fetch_differential_finders():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return []
  differentials = []
  for p in players.values():
    try:
      sel = float(p.get("selected_by_percent", "0") or 0)
      pts = int(p.get("total_points", 0) or 0)
      if 0.5 < sel < 8.0 and pts > 10:
        differentials.append({
            "name": p.get("web_name"),
            "team": teams.get(p.get("team"), "غير معروف"),
            "sel": sel,
            "pts": pts,
            "price": round(p.get("now_cost", 0) / 10.0, 1),
        })
    except Exception:
      continue
  return sorted(differentials, key=lambda x: x["pts"], reverse=True)[:10]


@st.cache_data(ttl=3600)
def fetch_injured_players_from_api():
  players, teams, _, _, _ = fetch_live_fpl_data()
  if not players:
    return []
  injured_list = []
  for p in players.values():
    status = p.get("status", "a")
    if status != "a":
      injured_list.append({
          "اللاعب": p.get("web_name", "لاعب"),
          "الفريق": teams.get(p.get("team"), ""),
          "السعر": f"£{round(p.get('now_cost', 0) / 10.0, 1)}M",
          "الحالة": status,
          "نسبة المشاركة": f"{p.get('chance_of_playing_next_round', 0)}%",
          "السبب": p.get("news", "") or "غير متوفر",
      })
  return injured_list


# ---------------------------------------------------------
# الذكاء الاصطناعي للاستشارات وتحليل التبديلات بناءً على الخبراء
# ---------------------------------------------------------
SYSTEM_PROMPT = """
أنت مستشار فانتسي محترف وخبير في تحليلات نخبة خبراء الفانتسي العرب والأجانب (مثل FPL Raptor, Let's Talk FPL, وغيرهم). 
تقدم تحليلاً تكتيكياً دقيقاً ومبسطاً وتشرح دائماً الأسباب (لماذا) وراء كل مقترح تبديل أو خيار استراتيجي بناءً على البيانات الحية للسيرفر الرسمي.
"""


def ask_openai(prompt_text, squad_context=""):
  api_key = os.environ.get("OPENAI_API_KEY", "")
  if not api_key:
    return "⚠️ تنبيه: يرجى إضافة مفتاح OPENAI_API_KEY في متغيرات البيئة."
  try:
    client = OpenAI(api_key=api_key)
    query = (
        f"تشكيلة المستخدم الرسمية من السيرفر:\n[{squad_context}]\n\nالطلب:"
        f" {prompt_text}"
    )
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0.2,
        max_tokens=1200,
    )
    return res.choices[0].message.content.strip()
  except Exception as e:
    return f"⚠️ خطأ في الاتصال: {str(e)}"


# ---------------------------------------------------------
# واجهة الاستخدام (Streamlit UI)
# ---------------------------------------------------------
st.markdown(
    "<h1 style='text-align: center; color: #00ff87; margin-bottom: 0;'>⚽ BMS"
    " bot FPL</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #b1c1d8; font-size: 15px; margin-top:"
    " 5px;'>المنصة الذكية لإدارة وفحص فريق الفانتسي مع متابعة الدوريات الحية"
    " وبونص اللاعبين</p>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 1])
with col1:
  user_fpl_id = st.text_input(
      "⚽ أدخل معرف فريقك (FPL Team ID):", value="", placeholder="مثال: 123456"
  )

with col2:
  _, _, _, _, deadline_str = fetch_live_fpl_data()
  if deadline_str:
    try:
      dl_dt = datetime.datetime.strptime(
          deadline_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S"
      )
      diff = dl_dt - datetime.datetime.utcnow()
      if diff.total_seconds() > 0:
        st.markdown(
            "<div style='text-align: center; padding-top: 25px;'><div"
            f" class='deadline-badge'>⏳ المتبقي للديدلاين: {diff.days} أيام,"
            f" {divmod(diff.seconds, 3600)[0]} ساعات</div></div>",
            unsafe_allow_html=True,
        )
    except Exception:
      pass

st.markdown("---")

current_squad_text = ""
squad_objects, squad_err = None, None
if user_fpl_id:
  squad_objects, squad_err = fetch_manager_squad(user_fpl_id)
  if squad_objects:
    current_squad_text = ", ".join([
        f"{p['name']} ({p['pos']} - النادي: {p['team']} - £{p['price']}M - مؤشر"
        f" الأداء: {p['math_score']})"
        for p in squad_objects
    ])

# تم دمج تبويب التبديلات مع التشكيلة المرئية وإضافة متابعة الدوريات لايف مع البونص
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏠 لوحة التحكم والدوريات الحية",
    "📊 التشكيلة المرئية وتحليل التبديلات",
    "👑 مستشار الكابتن",
    "💬 المساعد الذكي",
    "🚑 مرصد الإصابات",
    "📈 رادار الأسعار",
    "💎 كاشف التفاضليين",
    "🛡️ مؤشر الملكية EO",
])

with tab1:
  st.subheader(
      "🏠 لوحة التحكم ومتابعة الدوريات الخاصة الحية (Live Standings & Bonus)"
  )
  if not user_fpl_id:
    st.warning(
        "⚠️ يرجى إدخال رقم FPL Team ID الخاص بك في الأعلى (مثال: 123456)."
    )
  else:
    entry = fetch_manager_info(user_fpl_id)
    if not entry:
      st.error("رقم الفريق غير صحيح أو تعذر جلب البيانات.")
    else:
      c1, c2, c3, c4 = st.columns(4)
      c1.markdown(
          f'<div class="metric-box"><h3>{entry.get("summary_overall_points", 0)}</h3><p>إجمالي'
          " النقاط</p></div>",
          unsafe_allow_html=True,
      )
      c2.markdown(
          f'<div class="metric-box"><h3>{entry.get("summary_overall_rank", 0):,}</h3><p>الترتيب'
          " العام</p></div>",
          unsafe_allow_html=True,
      )
      c3.markdown(
          f'<div class="metric-box"><h3>{entry.get("summary_event_points", 0)}</h3><p>نقاط'
          " الجولة</p></div>",
          unsafe_allow_html=True,
      )
      c4.markdown(
          f'<div class="metric-box"><h3>{entry.get("name", "")}</h3><p>اسم'
          " الفريق</p></div>",
          unsafe_allow_html=True,
      )

      st.markdown("---")
      st.subheader("🏆 متابعة الدوريات الخاصة لايف (مع رصد النقاط وبونص الجولة)")
      classic_leagues = entry.get("leagues", {}).get("classic", [])
      if classic_leagues:
        league_options = {lg["name"]: lg["id"] for lg in classic_leagues}
        selected_league_name = st.selectbox(
            "اختر الدوري الخاص للمتابعة الحية:", list(league_options.keys())
        )
        if selected_league_name:
          chosen_league_id = league_options[selected_league_name]
          standings_data = fetch_classic_league_standings(chosen_league_id)
          if standings_data and "standings" in standings_data:
            results = standings_data["standings"].get("results", [])
            league_table = []
            for row in results:
              league_table.append({
                  "الترتيب الحقيقي": row.get("rank"),
                  "اسم المدرب": row.get("player_name"),
                  "اسم الفريق": row.get("entry_name"),
                  "نقاط الجولة الحية": row.get("event_total"),
                  "إجمالي النقاط": row.get("total"),
              })
            st.table(league_table)
            st.info(
                "💡 يتم تحديث جدول الدوري الحيي ونقاط البونص تباعاً فور انتهاء"
                " المباريات عبر سيرفر FPL."
            )
          else:
                st.info("جاري تحميل ترتيب الدوري...")
      else:
        st.info("لا توجد دوريات كلاسيكية مسجلة لهذا الفريق.")

with tab2:
  st.subheader("📊 التشكيلة المرئية وتحليل التبديلات (رأي الخبراء والذكاء الاصطناعي)")
  if not user_fpl_id:
    st.warning("⚠️ أدخل رقم FPL Team ID في الأعلى.")
  else:
    if squad_err:
      st.error(squad_err)
    elif squad_objects:
      starting_11 = [p for p in squad_objects if p["position"] <= 11]
      bench = [p for p in squad_objects if p["position"] > 11]
      st.markdown('<div class="pitch-container">', unsafe_allow_html=True)
      for pos_filter in ["GKP", "DEF", "MID", "FWD"]:
        row = [p for p in starting_11 if p["pos"] == pos_filter]
        if row:
          st.markdown('<div class="pitch-row">', unsafe_allow_html=True)
          for p in row:
            cap = " (C)" if p["is_captain"] else (" (V)" if p["is_vice"] else "")
            bc = "badge-green" if p["status"] == "a" else "badge-red"
            player_card_html = (
                f'<div class="player-card {bc}">{p["name"]}{cap}'
                f'<span>{p["team"]}</span>'
                f'<div class="price">£{p["price"]}M</div></div>'
            )
            st.markdown(player_card_html, unsafe_allow_html=True)
          st.markdown("</div>", unsafe_allow_html=True)
      st.markdown("</div>", unsafe_allow_html=True)
      st.write(
          "**دكة البدلاء:** "
          + " | ".join([f"{p['name']} ({p['team']} - £{p['price']}M)" for p in bench])
      )

      st.markdown("---")
      st.subheader("🔄 مقترحات التبديلات المستندة لخبراء الفانتسي (عرب وأجانب)")
      if st.button("🤖 توليد تحليل وتوصيات التبديلات مع شرح الأسباب"):
        if current_squad_text:
          ai_transfer_advice = ask_openai(
              "بناءً على توجهات ونقاشات خبراء الفانتسي النخبة (العرب والأجانب) وحالة اللاعبين الحالية، اقترح أفضل تبديلين (بيع و شراء) مع كتابة تحليل مبسط وشرح وافٍ (لماذا) تم اختيار هذا التبديل.",
              squad_context=current_squad_text,
          )
          st.markdown(ai_transfer_advice)
        else:
          st.warning("تعذر قراءة بيانات التشكيلة.")

with tab3:
  st.subheader("👑 مستشار الكابتن الذكي")
  if st.button("اختر أفضل كابتن"):
    if current_squad_text:
      st.markdown(
          ask_openai(
              "بناءً على توصيات خبراء الفانتسي، من هو أفضل مرشح لشارة الكابتن للجولة القادمة من تشكيلتي مع ذكر الأسباب؟",
              squad_context=current_squad_text,
          )
      )
    else:
      st.warning("أدخل رقم الفريق أولاً.")

with tab4:
  st.subheader("💬 المساعد الذكي")
  q = st.text_input("اطرح سؤالك الاستراتيجي...")
  if q:
    st.markdown(
        ask_openai(q, squad_context=current_squad_text)
        if current_squad_text
        else "أدخل رقم فريقك."
    )

with tab5:
  st.subheader("🚑 مرصد الإصابات")
  inj = fetch_injured_players_from_api()
  if inj:
    st.table(inj)
  else:
    st.success("لا توجد إصابات حالياً.")

with tab6:
  st.subheader("📈 رادار تغير الأسعار")
  rising, falling, teams_dict = fetch_price_changes_radar()
  col_r1, col_r2 = st.columns(2)
  with col_r1:
    st.markdown("#### 🔥 الأقرب لارتفاع السعر")
    for p in rising:
      st.write(
          f"- {p['web_name']} ({teams_dict.get(p.get('team'), '')} - £{p['now_cost']/10}M)"
      )
  with col_r2:
    st.markdown("#### ❄️ الأكثر عرضة لانخفاض السعر")
    for p in falling:
      st.write(
          f"- {p['web_name']} ({teams_dict.get(p.get('team'), '')} - £{p['now_cost']/10}M)"
      )

with tab7:
  st.subheader("💎 كاشف التفاضليين")
  diffs = fetch_differential_finders()
  if diffs:
    st.table(diffs)
  else:
    st.info("جاري التحميل...")

with tab8:
  st.subheader("🛡️ مؤشر الملكية EO")
  pn = st.text_input("اسم اللاعب لفحص خطورة عدم امتلاكه:")
  if pn and current_squad_text:
    st.markdown(
        ask_openai(
            f"ما مخاطر عدم امتلاك اللاعب {pn}؟", squad_context=current_squad_text
        )
    )
