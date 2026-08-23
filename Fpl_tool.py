import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import datetime

# 1. إعدادات الصفحة والتصميم البصري (CSS)
st.set_page_config(page_title="مدير الفانتسي الذكي 2026/2027", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
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
        background-color: #240038 !important; color: #ffffff !important; border: 1px solid #00ff87 !important; border-radius: 8px !important;
    }
    .pitch-container {
        background: linear-gradient(180deg, #1e7145 0%, #114b2d 100%);
        border: 2px solid #00ff87; border-radius: 15px; padding: 20px 10px; margin-bottom: 15px;
    }
    .pitch-row { display: flex; justify-content: space-evenly; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
    .player-card {
        background: rgba(36, 0, 56, 0.95); color: #ffffff; border: 1px solid #00ff87;
        padding: 6px 10px; border-radius: 8px; text-align: center; font-size: 12px; font-weight: bold; min-width: 90px; margin: 3px;
    }
    .player-card span { display: block; font-size: 10px; color: #00ff87; font-weight: normal; }
    .bench-container {
        background-color: #1a002c; padding: 12px; border-radius: 12px; display: flex;
        justify-content: space-evenly; border: 1px solid #37003c; flex-wrap: wrap; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 2. الحفظ التلقائي للمفاتيح
secrets_gemini = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("gemini_key", "")
secrets_fpl_id = str(st.secrets.get("FPL_ID") or st.secrets.get("fpl_id", ""))

# 3. وظائف جلب البيانات المباشرة
def get_json(url):
    try:
        res = requests.get(url, timeout=8)
        return res.json() if res.status_code == 200 else None
    except:
        return None

@st.cache_data(ttl=3600)
def fetch_manager_squad(manager_id):
    static_data = get_json("https://fantasy.premierleague.com/api/bootstrap-static/")
    if not static_data:
        return None, None, "تعذر جلب بيانات الفانتسي العامة."
        
    players = {p['id']: p for p in static_data['elements']}
    teams = {t['id']: t['name'] for t in static_data['teams']}
    types = {et['id']: et['singular_name_short'] for et in static_data['element_types']}

    current_gw = next((ev['id'] for ev in static_data.get('events', []) if ev.get('is_current')), 1)
    
    mdata = get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/") or {}
    mgr_info = f"الفريق: {mdata.get('name', '')} | النقاط: {mdata.get('summary_overall_points', 0)} | الترتيب: {mdata.get('summary_overall_rank', 0)}"

    picks_data = get_json(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{current_gw}/picks/")
    if not picks_data:
        return None, None, f"لم يتم العثور على تشكيلة للمعرف {manager_id}."

    bank = picks_data.get('entry_history', {}).get('bank', 0) / 10.0
    value = picks_data.get('entry_history', {}).get('value', 0) / 10.0

    starting_11, bench = [], []
    parsed_squad = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': [], 'Bench': []}

    for p in picks_data.get('picks', []):
        pinfo = players.get(p['element'], {})
        pname, tname = pinfo.get('web_name', 'Unknown'), teams.get(pinfo.get('team'), '')
        ptype = types.get(pinfo.get('element_type'), 'MID')
        cost = pinfo.get('now_cost', 0) / 10.0
        role = " 👑 (C)" if p.get('is_captain') else (" 🛡️ (VC)" if p.get('is_vice_captain') else "")

        line = f"- {pname} ({tname}) | المركز: {ptype} | السعر: £{cost}M{role}"
        card_html = f"<div class='player-card'>{pname}{role}<span>{tname} (£{cost}M)</span></div>"

        if p['position'] <= 11:
            starting_11.append(line)
            parsed_squad.get(ptype, parsed_squad['MID']).append(card_html)
        else:
            bench.append(line)
            parsed_squad['Bench'].append(card_html)

    squad_summary = f"=== بيانات الحساب ({manager_id}) ===\n{mgr_info}\nالميزانية: £{bank}M | القيمة: £{value}M\n\n=== التشكيلة الأساسية ===\n" + "\n".join(starting_11) + "\n\n=== البدلاء ===\n" + "\n".join(bench)
    return squad_summary, parsed_squad, None

@st.cache_data(ttl=1800)
def fetch_private_league_data(league_id):
    data = get_json(f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/")
    if data:
        name = data.get('league', {}).get('name', 'الدوري الخاص')
        standings = [f"- المرتبة {m.get('rank')}: {m.get('entry_name')} ({m.get('player_name')}) | النقاط: {m.get('total')}" for m in data.get('standings', {}).get('results', [])[:10]]
        return f"=== بيانات دوري: {name} ===\n" + "\n".join(standings), None
    return None, "تعذر الوصول لبيانات الدوري."

@st.cache_data(ttl=3600)
def fetch_live_fpl_data():
    data = get_json("https://fantasy.premierleague.com/api/bootstrap-static/")
    if not data: return "بيانات حية محدودة."
    teams = {t['id']: t['name'] for t in data.get('teams', [])}
    news = [f"- {p['web_name']} ({teams.get(p['team'])}): {p['news']}" for p in data.get('elements', []) if p.get('news')][:15]
    return "=== أحدث الإصابات والأخبار ===\n" + "\n".join(news)

# 4. توجيهات الذكاء الاصطناعي والدالة الموحدة المحدثة مع حل مشكلة NotFound
SYSTEM_INSTRUCTION = f"أنت خبير فانتسي الدوري الإنجليزي (FPL) لموسم 2026/2027. تاريخ اليوم: {datetime.date.today()}."

def run_fpl_ai(api_key, prompt, images=None):
    genai.configure(api_key=api_key)
    live_context = fetch_live_fpl_data()
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\n[المستجدات الحية]:\n{live_context}\n\n[الطلب]:\n{prompt}"
    
    contents = [full_prompt]
    if images:
        contents.extend(images if isinstance(images, list) else [images])

    # تجربة قائمة بالنماذج المتاحة لتفادي خطأ NotFound
    candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'gemini-pro']
    last_error = None

    for m_name in candidate_models:
        try:
            model = genai.GenerativeModel(m_name)
            res = model.generate_content(contents)
            return res.text
        except Exception as e:
            last_error = e
            continue
            
    raise Exception(f"تعذر الاتصال بـ Gemini API. الخطأ: {last_error}")

def render_ai_section(title, btn_text, prompt_text, desc=""):
    st.header(title)
    if desc: st.write(desc)
    if st.button(btn_text):
        with st.spinner("جاري التحليل..."):
            try:
                st.markdown(run_fpl_ai(gemini_key, prompt_text))
            except Exception as e:
                st.error(f"خطأ: {e}")

# 5. الشريط الجانبي والرأس
with st.sidebar:
    st.header("⚙️ الإعدادات والربط")
    gemini_key = st.text_input("مفتاح Gemini API:", value=secrets_gemini, type="password") or secrets_gemini
    saved_fpl_id = st.text_input("معرف فريقك (FPL Team ID):", value=secrets_fpl_id) or secrets_fpl_id
    st.caption("تغطية حية لموسم 2026/2027")

st.markdown("<h1 style='text-align: center; color: #FF1A1A;'>( حميدي مطلق ما تفوز علي )</h1>", unsafe_allow_html=True)
st.title("⚽ بوت الفانتسي الذكي المباشر")
st.markdown("---")

# 6. التوجيه وأقسام البوت
if gemini_key:
    page = st.selectbox("📌 اختر القسم المطلوب:", [
        "📊 تحليل التشكيلة والتقرير اليومي", "🎲 رادار المداورة (xMins)", "🃏 مخطط الخصائص (Chips)",
        "🛡️ مؤشر الملكية المؤثرة (EO)", "🏆 حاسبة الدوري الخاص", "📅 مخطط التبديلات الـ 3 القادمة",
        "🔥 رادار الدرافتات (3 أيام)", "🎙️ رادار المؤتمرات والإصابات", "🃏 مخطط الـ Wildcard",
        "📈 رادار الأسعار", "💬 المساعد الصوتي والدردشة", "⚔️ مقارنة التشكيلات (H2H)", 
        "👑 مصفوفة الكابتن", "🎯 استراتيجيات المغامرة", "📜 سجل وتقييم القرارات"
    ])
    st.markdown("---")

    if page == "📊 تحليل التشكيلة والتقرير اليومي":
        st.header("📊 تحليل التشكيلة وتوقع النقاط")
        method = st.radio("اختر طريقة الإدخال:", ["🔗 جلب تلقائي عبر ID", "📸 رفع صورة"])
        
        if method == "🔗 جلب تلقائي عبر ID":
            fpl_id_in = st.text_input("رقم FPL ID:", value=saved_fpl_id)
            if st.button("🚀 جلب وتحليل التشكيلة") and fpl_id_in:
                with st.spinner("جاري الجلب والتحليل..."):
                    squad_txt, parsed_squad, err = fetch_manager_squad(fpl_id_in)
                    if err: st.error(err)
                    else:
                        st.markdown(f"""
                        <div class="pitch-container">
                            <div class="pitch-row">{''.join(parsed_squad['FWD'])}</div>
                            <div class="pitch-row">{''.join(parsed_squad['MID'])}</div>
                            <div class="pitch-row">{''.join(parsed_squad['DEF'])}</div>
                            <div class="pitch-row">{''.join(parsed_squad['GKP'])}</div>
                        </div>
                        <div class="bench-container"><strong style="color:#00ff87;">الدكة:</strong>{''.join(parsed_squad['Bench'])}</div>
                        """, unsafe_allow_html=True)
                        
                        prompt = f"حلل التشكيلة القادمة وقيمها من 100 واقترح الكابتن والبدلاء وأضف في النهاية قسماً باسم '📲 **ملخص سريع للواتساب (قابل للنسخ):**' بـ 3 أسطر فقط:\n{squad_txt}"
                        st.markdown(run_fpl_ai(gemini_key, prompt))
        else:
            up_file = st.file_uploader("ارفع لقطة الشاشة:", type=["png", "jpg", "jpeg"])
            if up_file and st.button("🚀 بدء التحليل من الصورة"):
                with st.spinner("جاري تحليل الصورة..."):
                    st.markdown(run_fpl_ai(gemini_key, "اقرأ التشكيلة من الصورة وقدم تقريراً شاملاً وملخص للواتساب.", Image.open(up_file)))

    elif page == "🏆 حاسبة الدوري الخاص":
        st.header("🏆 تحليل وتكنيك التفوق في الدوري الخاص")
        l_id = st.text_input("رقم ID الدوري الخاص:")
        if st.button("🔍 تحليل الدوري") and l_id:
            with st.spinner("جاري السحب والتحليل..."):
                l_summary, err = fetch_private_league_data(l_id)
                if err: st.error(err)
                else:
                    st.text_area("📋 ترتيب الدوري:", l_summary, height=150)
                    st.markdown(run_fpl_ai(gemini_key, f"بناءً على الترتيب التالي قدم استراتيجية لتجاوز المنافسين:\n{l_summary}"))

    elif page == "🃏 مخطط الـ Wildcard":
        st.header("🃏 بناء تشكيلة الـ Wildcard")
        c1, c2 = st.columns(2)
        bg = c1.number_input("💰 الميزانية (£M):", value=100.0)
        st_style = c2.selectbox("🎯 الأسلوب:", ["متوازنة", "هجوم ناري", "دفاع صلب", "Differential"])
        if st.button("✨ بناء التشكيلة المثالية"):
            st.markdown(run_fpl_ai(gemini_key, f"ابن تشكيلة Wildcard كاملة بميزانية {bg}M بأسلوب {st_style}."))

    elif page == "💬 المساعد الصوتي والدردشة":
        st.header("🎙️ الدردشة والاستفسارات المباشرة")
        if "msgs" not in st.session_state: st.session_state.msgs = []
        for m in st.session_state.msgs:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if p := st.chat_input("اسأل عن أي لاعب، مؤتمر، أو تبديل..."):
            st.session_state.msgs.append({"role": "user", "content": p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                ans = run_fpl_ai(gemini_key, p)
                st.markdown(ans)
                st.session_state.msgs.append({"role": "assistant", "content": ans})

    elif page == "⚔️ مقارنة التشكيلات (H2H)":
        st.header("⚔️ مقارنة تشكيلة الخصم")
        c1, c2 = st.columns(2)
        f1 = c1.file_uploader("تشكليتك", type=["png", "jpg"], key="1")
        f2 = c2.file_uploader("تشكيلة الخصم", type=["png", "jpg"], key="2")
        if f1 and f2 and st.button("🔍 مقارنة التشكيلتين"):
            st.markdown(run_fpl_ai(gemini_key, "قارن بين التشكيلتين واكشف نقاط التفوق لكل فريق.", [Image.open(f1), Image.open(f2)]))

    # أقسام سريعة منفذة عبر الدالة الموحدة render_ai_section
    elif page == "🎲 رادار المداورة (xMins)":
        render_ai_section("🎲 رادار خطر المداورة", "🔍 فحص المداورة", "قدم تحليلاً في جداول لرادار المداورة (xMins) للاعبي الفرق الكبرى.")
    elif page == "🃏 مخطط الخصائص (Chips)":
        render_ai_section("🃏 حاسبة التوقيت الذهبي للخصائص", "🗓️ حساب الخطة", "قدم خطة لتفعيل الـ Wildcard, Free Hit, Bench Boost, Triple Captain.")
    elif page == "🛡️ مؤشر الملكية المؤثرة (EO)":
        render_ai_section("🛡️ مؤشر الملكية المؤثرة", "📊 تحليل مخاطر EO", "حلل مؤشر الملكية المؤثرة (EO) ومخاطر عدم امتلاك أكثر اللاعبين شعبية.")
    elif page == "📅 مخطط التبديلات الـ 3 القادمة":
        render_ai_section("📅 مخطط التبديلات الـ 3 القادمة", "🗓️ إعداد خطة التبديلات", f"اقترح خطة تبديلات لـ 3 جولات قادمة للفريق ID: {saved_fpl_id}")
    elif page == "🔥 رادار الدرافتات (3 أيام)":
        render_ai_section("🔥 أكثر اللاعبين تكراراً في الدرافتات", "🔍 كشف الأكثر تكراراً", "أبرز اللاعبين المختارين بكثرة في تشكيلات الدرافت خلال الـ 72 ساعة الماضية.")
    elif page == "🎙️ رادار المؤتمرات والإصابات":
        render_ai_section("🎙️ ملخص المؤتمرات الصحفية", "🔄 جلب أحدث التصريحات", "قدم ملخصاً لأهم ما ورد في المؤتمرات الصحفية والإصابات هذا الأسبوع.")
    elif page == "📈 رادار الأسعار":
        render_ai_section("📈 موجز تغيرات الأسعار", "🔄 جلب التغيرات", "قدم تقريراً بجداول عن التغيرات المتوقعة في أسعار اللاعبين (ارتفاع/انخفاض).")
    elif page == "👑 مصفوفة الكابتن":
        render_ai_section("👑 ترشيحات شارة الكابتن", "⚡ ترشيح الكابتن", "قدم أفضل 3 خيارات كابتن للجولة القادمة مع نسبة المخاطرة.")
    elif page == "🎯 استراتيجيات المغامرة":
        render_ai_section("🎯 تقييم المغامرة والريسك", "🤖 تقييم الريسك", "قيم استراتيجية خصم النقاط (-4/-8) والخيارات التفاضلية Differential لهذا الأسبوع.")
    elif page == "📜 سجل وتقييم القرارات":
        u_log = st.text_area("✍️ ادخل قراراتك الأخيرة:")
        if st.button("🧐 تقييم القرارات") and u_log:
            st.markdown(run_fpl_ai(gemini_key, f"قيم القرارات التالية واذكر الإيجابيات والسلبيات: {u_log}"))
else:
    st.info("الرجاء إدخال مفتاح Gemini API للبدء.")
