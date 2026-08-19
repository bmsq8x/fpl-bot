import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import datetime

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم البصري الفاخر (Glassmorphism & Neon)
# ---------------------------------------------------------
st.set_page_config(
    page_title="FPL AI Manager 2026/27",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تصميم هويّة الفانتسي الرسمية + تأثيرات الزجاج والنيون
st.markdown("""
<style>
    /* الخلفية العامة والخطوط */
    .stApp {
        background: radial-gradient(circle at top right, #1a002c 0%, #0d0118 60%, #05000a 100%);
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* هيدر الديدلاين المتوهج */
    .deadline-banner {
        background: linear-gradient(90deg, rgba(255,26,26,0.2) 0%, rgba(55,0,60,0.8) 50%, rgba(0,255,135,0.2) 100%);
        border: 1px solid rgba(0, 255, 135, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 12px 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 255, 135, 0.15);
    }
    
    /* الأزرار التفاعلية بنمط النيون */
    div.stButton > button {
        background: linear-gradient(135deg, #00ff87 0%, #02efff 100%) !important;
        color: #37003c !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 28px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(0, 255, 135, 0.3) !important;
        width: 100%;
    }
    div.stButton > button:hover {
        transform: translateY(-3px) scale(1.01);
        box-shadow: 0 8px 25px rgba(0, 255, 135, 0.6) !important;
    }
    
    /* القائمة الجانبية الحداثية */
    section[data-testid="stSidebar"] {
        background-color: rgba(26, 0, 44, 0.85) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(0, 255, 135, 0.2);
    }
    
    /* حقول الإدخال الزجاجية */
    .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
        background-color: rgba(36, 0, 56, 0.7) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0, 255, 135, 0.5) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(5px);
    }
    
    /* تصميم ملعب كرة القدم 3D الزجاجي */
    .pitch-container {
        background: radial-gradient(circle, #1e7145 0%, #0d3820 100%);
        border: 2px solid rgba(255, 255, 255, 0.8);
        border-radius: 20px;
        padding: 25px 15px;
        position: relative;
        margin-bottom: 20px;
        box-shadow: inset 0 0 50px rgba(0,0,0,0.5), 0 10px 30px rgba(0,255,135,0.2);
    }
    .pitch-container::before {
        content: "";
        position: absolute;
        top: 50%; left: 10%; right: 10%;
        height: 2px;
        background: rgba(255, 255, 255, 0.3);
    }
    .pitch-row {
        display: flex;
        justify-content: space-evenly;
        align-items: center;
        margin-bottom: 18px;
        flex-wrap: wrap;
    }
    
    /* بطاقات اللاعبين الاحترافية (UT Cards) */
    .player-card {
        background: linear-gradient(145deg, rgba(55,0,60,0.95) 0%, rgba(20,0,30,0.95) 100%);
        border: 1px solid #00ff87;
        color: #ffffff;
        padding: 8px 12px;
        border-radius: 12px;
        text-align: center;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 6px 15px rgba(0,0,0,0.5);
        min-width: 100px;
        margin: 4px;
        transition: transform 0.2s ease;
    }
    .player-card:hover {
        transform: scale(1.08);
        border-color: #02efff;
    }
    .player-card span {
        display: block;
        font-size: 10px;
        color: #00ff87;
        font-weight: 500;
        margin-top: 2px;
    }
    .player-card .role-badge {
        background: #00ff87;
        color: #37003c;
        border-radius: 50%;
        padding: 2px 6px;
        font-size: 9px;
        margin-left: 3px;
    }
    
    /* دكة البدلاء الزجاجية */
    .bench-container {
        background: rgba(26, 0, 44, 0.6);
        border: 1px solid rgba(0, 255, 135, 0.3);
        backdrop-filter: blur(10px);
        padding: 15px;
        border-radius: 15px;
        display: flex;
        justify-content: space-evenly;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. الحفظ التلقائي عبر Secrets
# ---------------------------------------------------------
secrets_gemini = str(st.secrets.get("GEMINI_API_KEY", st.secrets.get("gemini_key", "")))
secrets_fpl_id = str(st.secrets.get("FPL_ID", st.secrets.get("fpl_id", "")))

# ---------------------------------------------------------
# 3. جلب البيانات المباشرة والرسم التفاعلي
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_manager_squad(manager_id):
    try:
        static_res = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if static_res.status_code != 200:
            return None, None, "تعذر جلب بيانات الفانتسي العامة."
            
        static_data = static_res.json()
        players_dict = {p['id']: p for p in static_data['elements']}
        teams_dict = {t['id']: t['name'] for t in static_data['teams']}
        element_types = {et['id']: et['singular_name_short'] for et in static_data['element_types']}

        events = static_data.get('events', [])
        current_gw = 1
        for ev in events:
            if ev.get('is_current'):
                current_gw = ev['id']
                break
            elif ev.get('is_next'):
                current_gw = max(1, ev['id'] - 1)
                break

        mgr_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/", timeout=10)
        mgr_info = ""
        if mgr_res.status_code == 200:
            mdata = mgr_res.json()
            mgr_info = f"اسم الفريق: {mdata.get('name')} | المدرب: {mdata.get('player_first_name')} {mdata.get('player_last_name')} | النقاط: {mdata.get('summary_overall_points')} | الترتيب: {mdata.get('summary_overall_rank')}"

        picks_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{current_gw}/picks/", timeout=10)
        if picks_res.status_code != 200:
            picks_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/1/picks/", timeout=10)
            if picks_res.status_code != 200:
                return None, None, f"لم يتم العثور على تشكيلة للمعرف {manager_id}."

        picks_data = picks_res.json()
        picks = picks_data.get('picks', [])
        bank = picks_data.get('entry_history', {}).get('bank', 0) / 10.0
        value = picks_data.get('entry_history', {}).get('value', 0) / 10.0

        starting_11, bench = [], []
        parsed_squad = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': [], 'Bench': []}

        for p in picks:
            pid = p['element']
            pinfo = players_dict.get(pid, {})
            pname = pinfo.get('web_name', 'Unknown')
            tname = teams_dict.get(pinfo.get('team'), '')
            ptype = element_types.get(pinfo.get('element_type'), 'MID')
            cost = pinfo.get('now_cost', 0) / 10.0

            badge = ""
            role_str = ""
            if p.get('is_captain'):
                badge = "<span class='role-badge'>C</span>"
                role_str = " 👑 (C)"
            elif p.get('is_vice_captain'):
                badge = "<span class='role-badge'>VC</span>"
                role_str = " 🛡️ (VC)"

            line = f"- {pname} ({tname}) | المركز: {ptype} | السعر: £{cost}M{role_str}"
            card_html = f"<div class='player-card'>{pname}{badge}<span>{tname} (£{cost}M)</span></div>"

            if p['position'] <= 11:
                starting_11.append(line)
                if ptype in parsed_squad:
                    parsed_squad[ptype].append(card_html)
                else:
                    parsed_squad['MID'].append(card_html)
            else:
                bench.append(line)
                parsed_squad['Bench'].append(card_html)

        squad_summary = f"""
=== معلومات الحساب والفريق (FPL ID: {manager_id}) ===
{mgr_info}
الميزانية في البنك: £{bank}M | قيمة التشكيلة: £{value}M

=== التشكيلة الأساسية (11 لاعباً) ===
""" + "\n".join(starting_11) + """

=== دكة البدلاء (4 لاعبين) ===
""" + "\n".join(bench)

        return squad_summary, parsed_squad, None

    except Exception as e:
        return None, None, f"حدث خطأ أثناء الاتصال بسيرفر الفانتسي: {e}"

@st.cache_data(ttl=1800)
def fetch_private_league_data(league_id):
    try:
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            league_name = data.get('league', {}).get('name', 'الدوري الخاص')
            standings = data.get('standings', {}).get('results', [])
            
            top_managers = [
                f"- المرتبة {m.get('rank')}: {m.get('entry_name')} ({m.get('player_name')}) | النقاط: {m.get('total')} | (ID: {m.get('entry')})"
                for m in standings[:10]
            ]
            return f"=== بيانات دوري: {league_name} (League ID: {league_id}) ===\n" + "\n".join(top_managers), None
    except Exception as e:
        return None, f"خطأ: {e}"
    return None, "تعذر الوصول لبيانات الدوري."

@st.cache_data(ttl=3600)
def fetch_fixtures_fdr():
    try:
        res = requests.get("https://fantasy.premierleague.com/api/fixtures/?future=1", timeout=10)
        static_res = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if res.status_code == 200 and static_res.status_code == 200:
            fixtures = res.json()
            teams = {t['id']: t['name'] for t in static_res.json().get('teams', [])}
            
            upcoming_summary = [
                f"الجولة {fix.get('event', '?')}: {teams.get(fix.get('team_h'), 'Unknown')} (صعوبة {fix.get('team_h_difficulty', 3)}) ضد {teams.get(fix.get('team_a'), 'Unknown')} (صعوبة {fix.get('team_a_difficulty', 3)})"
                for fix in fixtures[:30]
            ]
            return "\n".join(upcoming_summary[:25])
    except Exception:
        pass
    return "تعذر جلب الجدول المباشر."

@st.cache_data(ttl=3600)
def fetch_live_fpl_data():
    try:
        res = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if res.status_code == 200:
            data = res.json()
            players = data.get('elements', [])
            teams = {t['id']: t['name'] for t in data.get('teams', [])}
            
            news_list = [
                f"- {p['web_name']} ({teams.get(p['team'], 'Unknown')}): {p['news']} (الجاهزية: {p.get('chance_of_playing_next_round', 100)}%)"
                for p in players if p.get('news')
            ]
            
            sorted_by_transfers = sorted(players, key=lambda x: x.get('transfers_in_event', 0), reverse=True)[:15]
            trending_players = [
                f"- {p['web_name']} ({teams.get(p['team'], '')}): ملكية {p.get('selected_by_percent', '0')}% | الشراء مؤخراً: {p.get('transfers_in_event', 0)}"
                for p in sorted_by_transfers
            ]
            
            return "=== أحدث الأخبار والإصابات (تحديث بالساعة) ===\n" + "\n".join(news_list[:25]) + "\n\n=== الأكثر تكراراً وشراءً ===\n" + "\n".join(trending_players)
    except Exception:
        pass
    return "تحديثات المباشرة تعتمد على التحليل المباشر للنموذج."

# ---------------------------------------------------------
# 4. محرك الذكاء الاصطناعي السريع
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = f"""
أنت خبير ومحلل فانتسي الدوري الإنجليزي الممتاز (FPL) لموسم 2026/2027.
تاريخ اليوم: {datetime.date.today().strftime('%Y-%m-%d')}.
قدم جميع الإجابات بأسلوب احترافي، منظم، في جداول ونقاط مباشرة.
"""

def run_fpl_ai(api_key, prompt, images=None):
    genai.configure(api_key=api_key)
    live_context = fetch_live_fpl_data()
    augmented_prompt = f"{SYSTEM_INSTRUCTION}\n\n[البيانات والمستجدات الحية]:\n{live_context}\n\n[طلب المستخدم]:\n{prompt}"
    
    candidates = ['gemini-1.5-flash', 'gemini-1.5-pro']
    contents = [augmented_prompt]
    if images:
        contents.extend(images if isinstance(images, list) else [images])

    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            return model.generate_content(contents).text, model_name
        except Exception:
            continue

    raise Exception("تعذر الاتصال بمحرك الذكاء الاصطناعي.")

# ---------------------------------------------------------
# 5. الشريط الجانبي والهيدر الرئيسي
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='color: #00ff87;'>⚙️ التحكم والربط</h2>", unsafe_allow_html=True)
    gemini_key = st.text_input("مفتاح Gemini API:", value=secrets_gemini, type="password") or secrets_gemini
    saved_fpl_id = st.text_input("رقم الـ ID الخاص بك:", value=secrets_fpl_id, placeholder="مثال: 123456") or secrets_fpl_id
    
    st.markdown("---")
    st.success("⚡ المظهر المتطور والتحديث الآلي مُفعّل")

# الهيدر والتصميم الرئيسي
st.markdown(
    "<h1 style='text-align: center; color: #FF1A1A; font-size: 44px; font-weight: 900; text-shadow: 0 0 15px rgba(255,26,26,0.5);'>"
    "( حميدي مطلق ما تفوز علي )"
    "</h1>", 
    unsafe_allow_html=True
)

st.markdown("""
<div class="deadline-banner">
    <span style="color: #00ff87; font-weight: bold; font-size: 16px;">⏱️ حالة السيرفر:</span> 
    مُتصل بسيرفرات FPL الرسمية - تحديث تلقائي لموسم 2026/2027
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. الأقسام الرئيسية للواجهة
# ---------------------------------------------------------
if gemini_key:
    page = st.selectbox(
        "📌 اختر القسم للتنافس والتحليل المباشر:",
        [
            "🏟️ التشكيلة على الملعب + ملخص الواتساب", 
            "🎲 رادار المداورة ودقائق اللعب (xMins)",
            "🃏 مخطط الخصائص والجولات المضاعفة (Chips Planner)",
            "🛡️ مؤشر الملكية المؤثرة (EO Risk Index)",
            "🏆 حاسبة الدوري الخاص (Private League Analyzer)",
            "📅 مخطط التبديلات للجولات الـ 3 القادمة",
            "🔥 رادار الدرافتات واللاعبين الأكثر تكراراً",
            "🎙️ رادار المؤتمرات الصحفية والإصابات الحية",
            "🃏 مخطط الـ Wildcard والتشكيلة المثالية",
            "📈 رادار الأسعار والتغيرات المباشرة",
            "💬 المساعد الصوتي والدردشة المباشرة",
            "⚔️ مقارنة التشكيلات (Head-to-Head)", 
            "👑 مصفوفة الكابتن المحدثة", 
            "🎯 استراتيجيات المغامرة والريسك",
            "📜 سجل وتقييم القرارات الأسبوعي"
        ]
    )
    st.markdown("---")

    # 1. التشكيلة والملعب والواتساب
    if page == "🏟️ التشكيلة على الملعب + ملخص الواتساب":
        st.subheader("🏟️ العرض البصري وتحليل التشكيلة")
        input_method = st.radio("طريقة الإدخال:", ["🔗 جلب تلقائي عبر ID الفريق", "📸 رفع لقطة شاشة"])
        
        if input_method == "🔗 جلب تلقائي عبر ID الفريق":
            fpl_id_input = st.text_input("ادخل FPL Team ID:", value=saved_fpl_id)
            if st.button("🚀 جلب ورسم التشكيلة على الملعب") and fpl_id_input:
                with st.spinner("جاري الرسم والتحليل..."):
                    squad_txt, parsed_squad, err = fetch_manager_squad(fpl_id_input)
                    if err:
                        st.error(err)
                    else:
                        st.markdown("#### ⚽ تشكليتك الحالية")
                        pitch_html = f"""
                        <div class="pitch-container">
                            <div class="pitch-row">{''.join(parsed_squad['FWD'])}</div>
                            <div class="pitch-row">{''.join(parsed_squad['MID'])}</div>
                            <div class="pitch-row">{''.join(parsed_squad['DEF'])}</div>
                            <div class="pitch-row">{''.join(parsed_squad['GKP'])}</div>
                        </div>
                        <div class="bench-container">
                            <strong style="color: #00ff87;">دكة البدلاء:</strong>
                            {''.join(parsed_squad['Bench'])}
                        </div>
                        """
                        st.markdown(pitch_html, unsafe_allow_html=True)
                        
                        prompt = f"""
                        حلل التشكيلة التالية بشكل كامل:
                        {squad_txt}
                        1. التقييم والغيابات.
                        2. الكابتن والتبديل الموصى به.
                        3. في النهاية ضِع قسماً باسم '📲 **ملخص للواتساب (جاهز للنسخ)**' يحتوي على 3 أسطر حماسية مع إيموجيات لمشاركتها مع المنافسين.
                        """
                        res_text, _ = run_fpl_ai(gemini_key, prompt)
                        st.markdown(res_text)

        else:
            uploaded_file = st.file_uploader("📸 ارفع صورة التشكيلة", type=["png", "jpg", "jpeg"])
            if uploaded_file and st.button("🚀 بدء التحليل من الصورة"):
                image = Image.open(uploaded_file)
                st.image(image, caption="التشكيلة المرفوعة", use_container_width=True)
                res_text, _ = run_fpl_ai(gemini_key, "حلل التشكيلة المرفوعة وأضف ملخصاً للواتساب في النهاية.", image)
                st.markdown(res_text)

    # 2. رادار xMins
    elif page == "🎲 رادار المداورة ودقائق اللعب (xMins)":
        st.subheader("🎲 رادار المداورة وخطر الدكة (Pep Roulette)")
        if st.button("🔍 فحص دقائق اللعب المضمونة والمخاطر"):
            res_text, _ = run_fpl_ai(gemini_key, "قدم تحليلاً في جداول لرادار المداورة (Pep Roulette) ونسب دقائق اللعب المتوقعة xMins لأبرز لاعبي الفرق الكبرى.")
            st.markdown(res_text)

    # 3. مخطط الخصائص Chips
    elif page == "🃏 مخطط الخصائص والجولات المضاعفة (Chips Planner)":
        st.subheader("🃏 مخطط التوقيت الذهبي للخصائص (Chips Planner)")
        if st.button("🗓️ حساب الخطة الذهبية للجولات المضاعفة"):
            res_text, _ = run_fpl_ai(gemini_key, "حدد مواعيد الجولات المضاعفة (Double GW) والفارغة (Blank GW) وقدم الجدول الزمني الأمثل لاستخدام الخصائص الاربع.")
            st.markdown(res_text)

    # 4. مؤشر الملكية EO
    elif page == "🛡️ مؤشر الملكية المؤثرة (EO Risk Index)":
        st.subheader("🛡️ قياس مخاطر الملكية المؤثرة (EO)")
        if st.button("📊 قياس خطورة عدم امتلاك النجوم"):
            res_text, _ = run_fpl_ai(gemini_key, "حلل مؤشر الملكية المؤثرة EO لأهم اللاعبين حالياً ووضح خطورة عدم امتلاكهم أو عدم كبتنتهم على السهم الأخضر.")
            st.markdown(res_text)

    # 5. الدوري الخاص
    elif page == "🏆 حاسبة الدوري الخاص (Private League Analyzer)":
        st.subheader("🏆 حاسبة التفوق في الدوري الخاص")
        league_id_in = st.text_input("🔢 ادخل League ID الخاص بك:", placeholder="مثال: 123456")
        if st.button("🔍 تحليل الدوري وصدارة القائمة") and league_id_in:
            l_summary, err = fetch_private_league_data(league_id_in)
            if err:
                st.error(err)
            else:
                st.text_area("📋 الترتيب الحالي:", l_summary, height=180)
                res_text, _ = run_fpl_ai(gemini_key, f"بناءً على ترتيب الدوري الخاص التالي:\n{l_summary}\nقدم استراتيجية وخيارات تفاضلية (Differentials) لإطاحة المتصدر وتجاوزه.")
                st.markdown(res_text)

    # باقي الأقسام
    elif page == "📅 مخطط التبديلات للجولات الـ 3 القادمة":
        target_id = st.text_input("ادخل FPL ID لتخطيط التبديلات:", value=saved_fpl_id)
        if st.button("🗓️ إنشاء خطة التبديلات") and target_id:
            squad_txt, _, err1 = fetch_manager_squad(target_id)
            fdr_txt = fetch_fixtures_fdr()
            if not err1:
                res_text, _ = run_fpl_ai(gemini_key, f"اعتماداً على التشكيلة:\n{squad_txt}\nوجدول الصعوبة FDR:\n{fdr_txt}\nضع خطة تبديلات مجانية لـ 3 جولات قادمة.")
                st.markdown(res_text)

    elif page == "🔥 رادار الدرافتات واللاعبين الأكثر تكراراً":
        if st.button("🔍 كشف أكثر اللاعبين اختياراً مؤخراً"):
            res_text, _ = run_fpl_ai(gemini_key, "قدم تحليلاً لأكثر اللاعبين تكراراً واختياراً في التشكيلات والدرافتات خلال الـ 72 ساعة الماضية لموسم 2026/2027.")
            st.markdown(res_text)

    elif page == "🎙️ رادار المؤتمرات الصحفية والإصابات الحية":
        if st.button("🔄 جلب ملخص تصريحات المدربين"):
            res_text, _ = run_fpl_ai(gemini_key, "قدم ملخصاً تحليلياً لأهم تصريحات المدربين والمؤتمرات الصحفية والإصابات المحدثة هذا الأسبوع.")
            st.markdown(res_text)

    elif page == "🃏 مخطط الـ Wildcard والتشكيلة المثالية":
        budget = st.number_input("💰 الميزانية (£M):", min_value=80.0, max_value=110.0, value=100.0)
        if st.button("✨ بناء تشكيلة Wildcard"):
            res_text, _ = run_fpl_ai(gemini_key, f"ابنِ تشكيلة Wildcard كاملة بـ {budget}M لموسم 2026/2027 في جدول منظم.")
            st.markdown(res_text)

    elif page == "📈 رادار الأسعار والتغيرات المباشرة":
        if st.button("🔄 جلب توقعات تغير الأسعار"):
            res_text, _ = run_fpl_ai(gemini_key, "قدم تقريراً بجداول عن أكثر اللاعبين القريبين من الارتفاع والانخفاض في السعر الليلة.")
            st.markdown(res_text)

    elif page == "💬 المساعد الصوتي والدردشة المباشرة":
        st.subheader("💬 الدردشة والمساعد التكتيكي")
        if "msgs" not in st.session_state: st.session_state.msgs = []
        for m in st.session_state.msgs:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if p := st.chat_input("اسأل البوت عن أي لاعب أو خيار..."):
            st.session_state.msgs.append({"role": "user", "content": p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                ans, _ = run_fpl_ai(gemini_key, p)
                st.markdown(ans)
                st.session_state.msgs.append({"role": "assistant", "content": ans})

    elif page == "⚔️ مقارنة التشكيلات (Head-to-Head)":
        c1, c2 = st.columns(2)
        with c1: f_m = st.file_uploader("📸 تشكليتك", type=["png", "jpg"], key="m")
        with c2: f_r = st.file_uploader("📸 تشكيلة المنافس", type=["png", "jpg"], key="r")
        if f_m and f_r and st.button("🔍 بدء المقارنة المباشرة"):
            res_text, _ = run_fpl_ai(gemini_key, "قارن بين التشكيلتين واكشف نقاط التفوق ومصادر النقاط للطرفين.", images=[Image.open(f_m), Image.open(f_r)])
            st.markdown(res_text)

    elif page == "👑 مصفوفة الكابتن المحدثة":
        gw_num = st.number_input("🎯 رقم الجولة:", min_value=1, max_value=38, value=1)
        if st.button("⚡ ترشيح أفضل خيارات الكابتن"):
            res_text, _ = run_fpl_ai(gemini_key, f"قدم أفضل 3 خيارات كابتن للجولة {gw_num} مع شرح المخاطرة والمكافأة لكل خيار.")
            st.markdown(res_text)

    elif page == "🎯 استراتيجيات المغامرة والريسك":
        strat_choice = st.radio("نوع الريسك:", ["خصم نقاط للتبديلات (-4/-8)", "حرق الميزانية هجومياً", "كابتن Differential"])
        if st.button("🤖 تقييم الريسك"):
            res_text, _ = run_fpl_ai(gemini_key, f"قيم نوع الريسك التالي لهذا الأسبوع: {strat_choice}")
            st.markdown(res_text)

    elif page == "📜 سجل وتقييم القرارات الأسبوعي":
        user_log = st.text_area("✍️ سجل قراراتك الأسبوعية:")
        if st.button("🧐 تقييم الأداء") and user_log:
            res_text, _ = run_fpl_ai(gemini_key, f"قيم قرارات المدرب التالية واذكر الإيجابيات والسلبيات: {user_log}")
            st.markdown(res_text)

else:
    st.info("أدخل مفتاح Gemini API في الشريط الجانبي للبدء.")
