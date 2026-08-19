import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import datetime

st.set_page_config(
    page_title="مدير الفانتسي الذكي - موسم 2026/2027",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. إعدادات التصميم وملعب كرة القدم (Custom CSS & Pitch)
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0d0118; color: #ffffff; }
    div.stButton > button {
        background: linear-gradient(135deg, #00ff87 0%, #02efff 100%);
        color: #37003c !important; font-weight: bold !important;
        border-radius: 12px !important; border: none !important;
    }
    .pitch-container {
        background: linear-gradient(180deg, #2e8b57 0%, #236b43 100%);
        border: 3px solid #ffffff; border-radius: 15px; padding: 20px;
        position: relative; margin-bottom: 20px;
    }
    .pitch-row {
        display: flex; justify-content: space-evenly; margin-bottom: 15px;
    }
    .player-card {
        background-color: rgba(255, 255, 255, 0.9);
        color: #37003c; padding: 5px 10px; border-radius: 8px;
        text-align: center; font-size: 12px; font-weight: bold;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3); width: 85px;
    }
    .player-card span { display: block; font-size: 10px; color: #555; }
    .bench-container {
        background-color: #1a002c; padding: 10px; border-radius: 10px;
        display: flex; justify-content: space-evenly; border: 1px solid #00ff87;
    }
</style>
""", unsafe_allow_html=True)

secrets_gemini = st.secrets.get("GEMINI_API_KEY", st.secrets.get("gemini_key", ""))
secrets_fpl_id = str(st.secrets.get("FPL_ID", st.secrets.get("fpl_id", "")))

# ---------------------------------------------------------
# 2. جلب البيانات المباشرة
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_manager_squad(manager_id):
    try:
        static_res = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10).json()
        players_dict = {p['id']: p for p in static_res['elements']}
        teams_dict = {t['id']: t['name'] for t in static_res['teams']}
        element_types = {et['id']: et['singular_name_short'] for et in static_res['element_types']}
        
        current_gw = next((ev['id'] for ev in static_res.get('events', []) if ev.get('is_current')), 1)
        
        mgr_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/", timeout=10)
        mgr_info = ""
        if mgr_res.status_code == 200:
            mdata = mgr_res.json()
            mgr_info = f"المدرب: {mdata.get('player_first_name')} | الترتيب العام: {mdata.get('summary_overall_rank')}"

        picks_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{current_gw}/picks/", timeout=10)
        if picks_res.status_code != 200:
            picks_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/1/picks/", timeout=10)
            
        picks_data = picks_res.json()
        picks = picks_data.get('picks', [])
        
        squad_txt_lines = []
        parsed_squad = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': [], 'Bench': []}
        
        for p in picks:
            pinfo = players_dict.get(p['element'], {})
            pname = pinfo.get('web_name', 'Unknown')
            ptype = element_types.get(pinfo.get('element_type'), '')
            role = " (C)" if p.get('is_captain') else " (VC)" if p.get('is_vice_captain') else ""
            
            card_html = f"<div class='player-card'>{pname}{role}<span>{ptype}</span></div>"
            
            if p['position'] <= 11:
                parsed_squad[ptype].append(card_html)
                squad_txt_lines.append(f"- {pname} | {ptype}{role}")
            else:
                parsed_squad['Bench'].append(card_html)
                squad_txt_lines.append(f"- {pname} | دكة")

        txt_summary = f"{mgr_info}\n" + "\n".join(squad_txt_lines)
        return txt_summary, parsed_squad, None
    except Exception as e:
        return None, None, f"خطأ: {e}"

@st.cache_data(ttl=3600)
def fetch_live_fpl_data():
    try:
        data = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10).json()
        players = data.get('elements', [])
        news_list = [f"- {p['web_name']}: {p['news']}" for p in players if p.get('news')]
        return "أخبار الإصابات:\n" + "\n".join(news_list[:20])
    except:
        return "يعتمد على النموذج المباشر."

SYSTEM_INSTRUCTION = f"أنت خبير فانتسي 2026/2027. التاريخ: {datetime.date.today().strftime('%Y-%m-%d')}. قدم تحليلات في جداول ونقاط مباشرة."

def run_fpl_ai(api_key, prompt, images=None):
    genai.configure(api_key=api_key)
    live_context = fetch_live_fpl_data()
    aug_prompt = f"{SYSTEM_INSTRUCTION}\n\n[البيانات الحية]:\n{live_context}\n\n[الطلب]:\n{prompt}"
    
    candidates = ['gemini-1.5-flash', 'gemini-1.5-pro']
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            contents = [aug_prompt] if not images else [aug_prompt, images]
            return model.generate_content(contents).text
        except Exception:
            continue
    raise Exception("تعذر الاتصال بـ Gemini.")

# ---------------------------------------------------------
# 3. الواجهة
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ إعدادات البوت")
    gemini_key = st.text_input("مفتاح Gemini API:", value=secrets_gemini, type="password")
    saved_fpl_id = st.text_input("رقم الـ ID:", value=secrets_fpl_id)
    st.success("⚡ التحديث التلقائي مُفعّل")

st.markdown("<h1 style='text-align: center; color: #FF1A1A; font-size: 42px; font-weight: bold;'> ( حميدي مطلق ما تفوز علي ) </h1>", unsafe_allow_html=True)
st.markdown("---")

if gemini_key:
    page = st.selectbox("📌 اختر القسم:", [
        "🏟️ تحليل وعرض التشكيلة (مع ملخص الواتساب)", 
        "🎲 رادار المداورة ودقائق اللعب (xMins)",
        "🃏 مخطط الخصائص والجولات المضاعفة (Chips Planner)",
        "🛡️ مؤشر الملكية المؤثرة (EO Risk)",
        "🏆 حاسبة الدوري الخاص",
        "📅 مخطط التبديلات"
    ])
    st.markdown("---")

    if page == "🏟️ تحليل وعرض التشكيلة (مع ملخص الواتساب)":
        fpl_id_input = st.text_input("رقم فريقك:", value=saved_fpl_id)
        if st.button("🚀 جلب وتحليل التشكيلة") and fpl_id_input:
            with st.spinner("جاري الرسم والتحليل..."):
                txt, parsed, err = fetch_manager_squad(fpl_id_input)
                if err:
                    st.error(err)
                else:
                    st.markdown("### 🏟️ تشكيلتك الحالية")
                    pitch_html = f"""
                    <div class="pitch-container">
                        <div class="pitch-row">{''.join(parsed['FWD'])}</div>
                        <div class="pitch-row">{''.join(parsed['MID'])}</div>
                        <div class="pitch-row">{''.join(parsed['DEF'])}</div>
                        <div class="pitch-row">{''.join(parsed['GKP'])}</div>
                    </div>
                    <div class="bench-container">{''.join(parsed['Bench'])}</div>
                    """
                    st.markdown(pitch_html, unsafe_allow_html=True)
                    
                    st.markdown("### 🤖 التحليل المباشر وملخص الواتساب")
                    prompt = f"حلل التشكيلة: {txt}. قدم التقييم والتوصيات. ثم في النهاية اكتب عنوان '📲 ملخص للواتساب' يضم 3 أسطر قصيرة مزودة بإيموجيات تصلح للنسخ واللصق لمشاكسة الأصدقاء في الجروب."
                    st.markdown(run_fpl_ai(gemini_key, prompt))

    elif page == "🎲 رادار المداورة ودقائق اللعب (xMins)":
        st.header("🎲 رادار التدوير وخطر الدكة (Pep Roulette)")
        if st.button("🔍 فحص دقائق اللاعبين الأساسيين"):
            prompt = "حلل تشكيلات الفرق الكبرى (سيتي، أرسنال، ليفربول). حدد اللاعبين المعرضين لخطر المداورة والجلوس على الدكة هذه الجولة، واللاعبين المضمون لعبهم لـ 90 دقيقة (xMins عالي). ضعها في جداول."
            st.markdown(run_fpl_ai(gemini_key, prompt))

    elif page == "🃏 مخطط الخصائص والجولات المضاعفة (Chips Planner)":
        st.header("🃏 التوقيت الذهبي للخصائص (Chips)")
        if st.button("🗓️ تخطيط الجولات المزدوجة والفارغة"):
            prompt = "قم بتحديد الجولات التي يتوقع أن تكون (Double GW) أو (Blank GW) بناءً على جدولة الدوري والكؤوس الإنجليزية. قدم خطة مثالية لتفعيل الـ Wildcard, Free Hit, Bench Boost, و Triple Captain."
            st.markdown(run_fpl_ai(gemini_key, prompt))

    elif page == "🛡️ مؤشر الملكية المؤثرة (EO Risk)":
        st.header("🛡️ تحليل الملكية المؤثرة (Effective Ownership)")
        if st.button("📊 قياس المخاطر في السوق"):
            prompt = "اشرح وضع الملكية المؤثرة (EO) لأهم لاعبي الفانتسي حالياً (مثل هالاند، صلاح، ساكا). وضح بالأرقام خطر عدم الكبتنة أو عدم الامتلاك وكيف سيؤثر على السهم الأخضر/الأحمر."
            st.markdown(run_fpl_ai(gemini_key, prompt))

    elif page == "🏆 حاسبة الدوري الخاص":
        st.info("قم بإدخال League ID لتحليل الترتيب وتقديم نصائح التفاضل.")
        # [نفس الكود السابق للدوري الخاص]
        
    elif page == "📅 مخطط التبديلات":
        st.info("تحليل التبديلات لـ 3 جولات قادمة لتفادي خصم النقاط.")
        # [نفس الكود السابق للتبديلات]
else:
    st.info("أدخل مفتاح Gemini API.")
