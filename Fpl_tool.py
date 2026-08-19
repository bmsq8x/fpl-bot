import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import datetime

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم البصري بأسلوب الفانتسي الرسمي (Custom CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="مدير الفانتسي الذكي - موسم 2026/2027",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ثيم وألوان الفانتسي الرسمية (أرجواني داكن، أخضر نيون، بطاقات واضحة للجوال)
st.markdown("""
<style>
    .stApp {
        background-color: #0d0118;
        color: #ffffff;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #00ff87 0%, #02efff 100%);
        color: #37003c !important;
        font-weight: bold !important;
        font-size: 16px !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 255, 135, 0.3);
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 255, 135, 0.5);
    }
    section[data-testid="stSidebar"] {
        background-color: #1a002c !important;
        border-right: 1px solid #37003c;
    }
    .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
        background-color: #240038 !important;
        color: #ffffff !important;
        border: 1px solid #00ff87 !important;
        border-radius: 8px !important;
    }
    .fpl-card {
        background-color: #1f0133;
        border: 1px solid #37003c;
        border-left: 5px solid #00ff87;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. الحفظ التلقائي لمفتاح API و ID الفريق عبر (Secrets)
# ---------------------------------------------------------
secrets_gemini = ""
secrets_fpl_id = ""

if "GEMINI_API_KEY" in st.secrets:
    secrets_gemini = st.secrets["GEMINI_API_KEY"]
elif "gemini_key" in st.secrets:
    secrets_gemini = st.secrets["gemini_key"]

if "FPL_ID" in st.secrets:
    secrets_fpl_id = str(st.secrets["FPL_ID"])
elif "fpl_id" in st.secrets:
    secrets_fpl_id = str(st.secrets["fpl_id"])

# ---------------------------------------------------------
# 3. وظائف جلب البيانات المباشرة مع التحديث التلقائي كل ساعة
# ---------------------------------------------------------
@st.cache_data(ttl=3600)  # تحديث التشكيلة كل ساعة
def fetch_manager_squad(manager_id):
    try:
        static_res = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if static_res.status_code != 200:
            return None, "تعذر جلب بيانات الفانتسي العامة من الموقع الرسمي."
            
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
            mgr_info = f"اسم الفريق: {mdata.get('name')} | المدرب: {mdata.get('player_first_name')} {mdata.get('player_last_name')} | النقاط الكلية: {mdata.get('summary_overall_points')} | الترتيب العام: {mdata.get('summary_overall_rank')}"

        picks_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{current_gw}/picks/", timeout=10)
        if picks_res.status_code != 200:
            picks_res = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/1/picks/", timeout=10)
            if picks_res.status_code != 200:
                return None, f"لم يتم العثور على تشكيلة مجهزة للمعرف {manager_id}."

        picks_data = picks_res.json()
        picks = picks_data.get('picks', [])
        bank = picks_data.get('entry_history', {}).get('bank', 0) / 10.0
        value = picks_data.get('entry_history', {}).get('value', 0) / 10.0

        starting_11 = []
        bench = []

        for p in picks:
            pid = p['element']
            pinfo = players_dict.get(pid, {})
            pname = pinfo.get('web_name', 'Unknown')
            tname = teams_dict.get(pinfo.get('team'), '')
            ptype = element_types.get(pinfo.get('element_type'), '')
            cost = pinfo.get('now_cost', 0) / 10.0

            role_str = ""
            if p.get('is_captain'):
                role_str = " 👑 (C - الكابتن)"
            elif p.get('is_vice_captain'):
                role_str = " 🛡️ (VC - نائب الكابتن)"

            line = f"- {pname} ({tname}) | المركز: {ptype} | السعر: £{cost}M{role_str}"
            if p['position'] <= 11:
                starting_11.append(line)
            else:
                bench.append(line)

        squad_summary = f"""
=== معلومات الحساب والفريق (FPL ID: {manager_id}) ===
{mgr_info}
الميزانية المتبقية في البنك: £{bank}M | قيمة التشكيلة الإجمالية: £{value}M

=== التشكيلة الأساسية (11 لاعباً) ===
""" + "\n".join(starting_11) + """

=== دكة البدلاء (4 لاعبين) ===
""" + "\n".join(bench)

        return squad_summary, None

    except Exception as e:
        return None, f"حدث خطأ أثناء الاتصال بسيرفر الفانتسي: {e}"

# جلب ترتيب الدوري الخاص (تحديث كل نصف ساعة)
@st.cache_data(ttl=1800)
def fetch_private_league_data(league_id):
    try:
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            league_name = data.get('league', {}).get('name', 'الدوري الخاص')
            standings = data.get('standings', {}).get('results', [])
            
            top_managers = []
            for m in standings[:10]:
                top_managers.append(f"- المرتبة {m.get('rank')}: {m.get('entry_name')} ({m.get('player_name')}) | النقاط الكلية: {m.get('total')} | (ID المدرب: {m.get('entry')})")
            
            summary = f"=== بيانات دوري: {league_name} (League ID: {league_id}) ===\n" + "\n".join(top_managers)
            return summary, None
    except Exception as e:
        return None, f"خطأ أثناء جلب بيانات الدوري الخاص: {e}"
    return None, "تعذر الوصول لبيانات الدوري. تأكد من صحة رقم ID الدوري."

# جلب المباريات ونسب الصعوبة FDR (تحديث كل ساعة)
@st.cache_data(ttl=3600)
def fetch_fixtures_fdr():
    try:
        res = requests.get("https://fantasy.premierleague.com/api/fixtures/?future=1", timeout=10)
        static_res = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if res.status_code == 200 and static_res.status_code == 200:
            fixtures = res.json()
            teams = {t['id']: t['name'] for t in static_res.json().get('teams', [])}
            
            upcoming_summary = []
            for fix in fixtures[:30]:
                h_team = teams.get(fix.get('team_h'), 'Unknown')
                a_team = teams.get(fix.get('team_a'), 'Unknown')
                gw = fix.get('event', '?')
                h_diff = fix.get('team_h_difficulty', 3)
                a_diff = fix.get('team_a_difficulty', 3)
                upcoming_summary.append(f"الجولة {gw}: {h_team} (صعوبة {h_diff}) ضد {a_team} (صعوبة {a_diff})")
            
            return "\n".join(upcoming_summary[:25])
    except Exception:
        pass
    return "تعذر جلب الجدول المباشر، سيتم الاعتماد على التحليل المباشر للنموذج."

# جلب أخبار الإصابات والدرافتات والتغيرات المباشرة (تحديث تلقائي كل ساعة)
@st.cache_data(ttl=3600)  # 3600 ثانية = 1 ساعة
def fetch_live_fpl_data():
    try:
        url = "https://fantasy.premierleague.com/api/bootstrap-static/"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            players = data.get('elements', [])
            teams = {t['id']: t['name'] for t in data.get('teams', [])}
            
            news_list = []
            for p in players:
                if p.get('news'):
                    team_name = teams.get(p['team'], 'Unknown')
                    news_list.append(f"- {p['web_name']} ({team_name}): {p['news']} (نسبة الجاهزية: {p.get('chance_of_playing_next_round', 100)}%)")
            
            sorted_by_transfers = sorted(players, key=lambda x: x.get('transfers_in_event', 0), reverse=True)[:15]
            trending_players = [
                f"- {p['web_name']} ({teams.get(p['team'], '')}): ملكية {p.get('selected_by_percent', '0')}% | عمليات الشراء مؤخراً: {p.get('transfers_in_event', 0)}"
                for p in sorted_by_transfers
            ]
            
            context_str = "=== أحدث الأخبار والإصابات (تحديث بالساعة) ===\n" + "\n".join(news_list[:25])
            context_str += "\n\n=== الأكثر تكراراً واختياراً في التشكيلات والدرافتات مؤخراً ===\n" + "\n".join(trending_players)
            return context_str
    except Exception:
        pass
    return "تحديثات المؤتمرات وتوجهات الدرافتات الحية تعتمد على التحليل المباشر للنموذج."

# ---------------------------------------------------------
# 4. توجيهات الذكاء الاصطناعي
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = f"""
أنت خبير ومحلل فانتسي الدوري الإنجليزي الممتاز (FPL) لموسم 2026/2027.
تاريخ اليوم المعتمد للمتابعة: {datetime.date.today().strftime('%Y-%m-%d')} (انطلاق المتابعة المباشرة بتحديثات كل ساعة من 20/8/2026 حتى نهاية الموسم).

محاور التركيز الرئيسية للتحليل:
1. المتابعة المستمرة لآخر الأخبار وتصريحات المؤتمرات الصحفية والإصابات المحدثة كل ساعة.
2. تحليلات وتوجهات الدرافتات (Draft Trends) واللاعبين الأكثر تكراراً واختياراً في التشكيلات المُنشأة خلال الـ 3 أيام الماضية (72 ساعة).
3. التخطيط للتبديلات بناءً على صعوبة المواجهات (FDR) للجولات القادمة.
4. الالتزام بالقوانين الرسمية: ميزانية الـ 15 لاعباً £100.0M كحد أقصى. الحد الأدنى للحراس والمدافعين £4.0M، وللوسط والمهاجمين £4.5M.
5. تقديم جميع التحليلات في جداول منظمة ونقاط مباشرة ومحددة.
"""

def run_fpl_ai(api_key, prompt, images=None):
    genai.configure(api_key=api_key)
    live_context = fetch_live_fpl_data()
    augmented_prompt = f"{SYSTEM_INSTRUCTION}\n\n[البيانات والمستجدات الحية والدرافتات المحدثة خلال هذه الساعة]:\n{live_context}\n\n[طلب المستخدم]:\n{prompt}"
    
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception:
        pass

    candidates = [m for m in available_models if 'flash' in m.lower() or 'pro' in m.lower()]
    if not candidates:
        candidates = ['gemini-1.5-flash', 'gemini-1.5-pro']

    contents = [augmented_prompt]
    if images:
        if isinstance(images, list):
            contents.extend(images)
        else:
            contents.append(images)

    last_error = None
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            clean_name = model_name.replace("models/", "")
            return response.text, clean_name
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"تعذر الاتصال بـ Gemini API: {last_error}")

# ---------------------------------------------------------
# 5. الواجهة والشريط الجانبي
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ إعدادات البوت والربط")
    
    gemini_key_input = st.text_input("مفتاح Gemini API:", value=secrets_gemini, type="password")
    gemini_key = gemini_key_input if gemini_key_input else secrets_gemini
    
    st.markdown("---")
    st.header("🔗 ربط حساب الفانتسي")
    saved_fpl_id_input = st.text_input("رقم معرف فريقك (FPL Team ID):", value=secrets_fpl_id, placeholder="مثال: 123456")
    saved_fpl_id = saved_fpl_id_input if saved_fpl_id_input else secrets_fpl_id
    
    st.markdown("---")
    st.success("⚡ التحديث التلقائي كل ساعة مُفعّل")
    if secrets_gemini or secrets_fpl_id:
        st.info("🟢 الحفظ التلقائي عبر Secrets مفعّل")
    else:
        st.caption("💡 يمكنك حفظ المفتاح والـ ID تلقائياً عبر Secrets")
        
    st.caption("تغطية حية ومستمرة لموسم 2026/2027")
    st.markdown("[Google AI Studio](https://aistudio.google.com/app/apikey)")

# العبارة الرئيسية في أعلى الصفحة
st.markdown(
    "<h1 style='text-align: center; color: #FF1A1A; font-size: 42px; font-weight: bold; margin-bottom: 10px;'>"
    "( حميدي مطلق ما تفوز علي )"
    "</h1>", 
    unsafe_allow_html=True
)

st.title("⚽ بوت الفانتسي الذكي المباشر - موسم 2026/2027")
st.caption("تحديث تلقائي كل ساعة للأخبار، الإصابات، المؤتمرات، والدرافتات الحديثة")
st.markdown("---")

# ---------------------------------------------------------
# 6. أقسام البوت المحدثة
# ---------------------------------------------------------
if gemini_key:
    page = st.selectbox(
        "📌 اختر القسم المطلوب للتحليل المباشر:",
        [
            "📊 تحليل التشكيلة والتقرير اليومي", 
            "🏆 حاسبة الدوري الخاص (Private League Analyzer)",
            "📅 مخطط التبديلات والجولات الـ 3 القادمة (Transfer Planner)",
            "🔥 رادار الدرافتات واللاعبين الأكثر تكراراً (3 أيام)",
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

    # 1. تحليل التشكيلة
    if page == "📊 تحليل التشكيلة والتقرير اليومي":
        st.header("📊 تحليل التشكيلة وتوقع النقاط")
        input_method = st.radio("اختر طريقة إدخال التشكيلة:", ["🔗 جلب تلقائي عبر ID الفريق", "📸 رفع لقطة شاشة (صورة)"])
        
        if input_method == "🔗 جلب تلقائي عبر ID الفريق":
            fpl_id_input = st.text_input("ادخل رقم معرف فريقك (FPL Team ID):", value=saved_fpl_id if saved_fpl_id else "")
            if st.button("🚀 جلب وتحليل التشكيلة بـ ID"):
                if fpl_id_input:
                    with st.spinner("جاري جلب تشكيلتك المباشرة من سيرفر الفانتسي..."):
                        squad_txt, err = fetch_manager_squad(fpl_id_input)
                        if err:
                            st.error(err)
                        else:
                            st.success("تم جلب التشكيلة بنجاح!")
                            st.text_area("📋 التشكيلة المسحوبة:", squad_txt, height=220)
                            
                            prompt = f"المطلوب تحليل فريق الفانتسي التالي المسحوب من الموقع الرسمي:\n\n{squad_txt}\n\nقدم تقريراً كاملاً يشمل التقييم من 100، كشف الغيابات المحدثة، وخيارات التبديل والكابتن."
                            with st.spinner("جاري تحليل التشكيلة..."):
                                try:
                                    res_text, _ = run_fpl_ai(gemini_key, prompt)
                                    st.session_state['last_analysis'] = res_text
                                    st.markdown(res_text)
                                except Exception as e:
                                    st.error(f"خطأ: {e}")
                else:
                    st.warning("يرجى إدخال رقم ID الفريق أولاً.")

        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                uploaded_file = st.file_uploader("📸 ارفع تشكليتك الحالية لموسم 2026/27", type=["png", "jpg", "jpeg"])
            if uploaded_file:
                image = Image.open(uploaded_file)
                with col2:
                    st.image(image, caption="التشكيلة المرفوعة", use_container_width=True)
                if st.button("🚀 بدء التحليل المباشر من الصورة"):
                    prompt = "اقرأ التشكيلة من الصورة وقدم تقريراً شاملاً بالتقييم والغيابات والتبديلات المقترحة."
                    try:
                        with st.spinner("جاري التحليل..."):
                            res_text, used_m = run_fpl_ai(gemini_key, prompt, image)
                            st.session_state['last_analysis'] = res_text
                            st.markdown(res_text)
                    except Exception as e:
                        st.error(f"خطأ: {e}")

    # 2. حاسبة الدوري الخاص
    elif page == "🏆 حاسبة الدوري الخاص (Private League Analyzer)":
        st.header("🏆 تحليل وتكنيك التفوق في الدوري الخاص")
        league_id_in = st.text_input("🔢 ادخل رقم ID دوريك الخاص (Private League ID):", placeholder="مثال: 123456")
        
        if st.button("🔍 تحليل الدوري الخاص وصدارة القائمة"):
            if league_id_in:
                with st.spinner("جاري سحب ترتيب الدوري الخاص وتحليل صدارة المنافسين..."):
                    l_summary, err = fetch_private_league_data(league_id_in)
                    if err:
                        st.error(err)
                    else:
                        st.text_area("📋 ترتيب الدوري الحالي:", l_summary, height=200)
                        
                        prompt = f"""
                        بناءً على جدول ترتيب الدوري الخاص التالي:
                        {l_summary}
                        
                        قدم استراتيجية مفصلة تشمل:
                        1. نصائح تفاضلية (Differentials) للتقليص وتجاوز المتصدرين في هذا الدوري.
                        2. تحليل نوعية المخاطرة المطلوبة للحفاظ على الصدارة أو انتزاعها.
                        3. اللاعبين الواجب تجنبهم إذا كان معظم المنافسين يمتلكونهم.
                        """
                        try:
                            res_text, _ = run_fpl_ai(gemini_key, prompt)
                            st.markdown(res_text)
                        except Exception as e:
                            st.error(f"خطأ: {e}")
            else:
                st.warning("ادخل رقم ID الدوري أولاً.")

    # 3. مخطط التبديلات للجولات القادمة
    elif page == "📅 مخطط التبديلات والجولات الـ 3 القادمة (Transfer Planner)":
        st.header("📅 مخطط التبديلات الذكي للجولات الـ 3 القادمة")
        st.write("يساعدك هذا القسم على توزيع تبديلاتك المجانية لـ 3 جولات قادمة بناءً على صعوبة المباريات (FDR):")
        
        target_id = st.text_input("ادخل FPL ID لتخطيط فريقك:", value=saved_fpl_id if saved_fpl_id else "")
        
        if st.button("🗓️ إنشاء خطة التبديلات الـ 3 القادمة"):
            if target_id:
                with st.spinner("جاري جلب جدول المباريات القادمة وتشكيلتك..."):
                    squad_txt, err1 = fetch_manager_squad(target_id)
                    fdr_txt = fetch_fixtures_fdr()
                    
                    if err1:
                        st.error(err1)
                    else:
                        planner_prompt = f"""
                        [بيانات التشكيلة الحالية]:
                        {squad_txt}
                        
                        [جدول صعوبة المباريات المباشرة FDR]:
                        {fdr_txt}
                        
                        قدم جدولاً ومخططاً للتبديلات المجانية للجولات الـ 3 القادمة:
                        1. التبديل الأول المقترح للجولة القادمة.
                        2. التبديل الثاني المتوقع للجولة التي تليها دون خصم نقاط (-4).
                        3. اللاعبين الواجب بيعهم فوراً بسبب صعوبة جدول مواجهاتهم.
                        4. اللاعبين الواجب شراؤهم مبكراً للاستفادة من جدولهم السهل.
                        """
                        try:
                            res_text, _ = run_fpl_ai(gemini_key, planner_prompt)
                            st.markdown(res_text)
                        except Exception as e:
                            st.error(f"خطأ: {e}")
            else:
                st.warning("ادخل رقم ID فريقك أولاً.")

    # 4. رادار الدرافتات
    elif page == "🔥 رادار الدرافتات واللاعبين الأكثر تكراراً (3 أيام)":
        st.header("🔥 تحليلات اللاعبين الأكثر تكراراً في الدرافتات الحديثة")
        pos_filter = st.selectbox("🎯 تصفية حسب المركز:", ["الكل", "حراس المرمى", "المدافعون", "خط الوسط", "المهاجمون"])
        if st.button("🔍 كشف أكثر اللاعبين تكراراً في الدرافتات الأخيرة"):
            draft_prompt = f"قدم تحليلاً دقيقاً لأكثر اللاعبين تكراراً واختياراً في الدرافتات خلال الـ 3 أيام الماضية لموسم 2026/2027. (التصفية: {pos_filter})"
            try:
                with st.spinner("جاري القراءة..."):
                    res_text, _ = run_fpl_ai(gemini_key, draft_prompt)
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    # 5. رادار المؤتمرات
    elif page == "🎙️ رادار المؤتمرات الصحفية والإصابات الحية":
        st.header("🎙️ رادار تصريحات المدربين والمؤتمرات الصحفية")
        manager_query = st.text_input("🔍 استعلم عن نادي أو مدرب محدد:")
        if st.button("🔄 جلب ملخص المؤتمرات الصحفية للجولة"):
            press_prompt = f"قدم ملخصاً تحليلياً لأهم ما ورد في المؤتمرات الصحفية لمدربي البريميرليج هذا الأسبوع لموسم 2026/2027. {manager_query}"
            try:
                with st.spinner("جاري التحليل..."):
                    res_text, _ = run_fpl_ai(gemini_key, press_prompt)
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    # 6. مخطط Wildcard
    elif page == "🃏 مخطط الـ Wildcard والتشكيلة المثالية":
        st.header("🃏 بناء تشكيلة الـ Wildcard المحدثة")
        wc1, wc2 = st.columns(2)
        with wc1:
            budget = st.number_input("💰 الميزانية المتاحة (£M):", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
            strategy = st.selectbox("🎯 الأسلوب التكتيكي:", ["متوازنة", "هجوم ناري", "دفاع صلب برخص بالوسط", "مغامرة Differential"])
        with wc2:
            target_gws = st.slider("🗓️ التخطيط للجولات القادمة:", min_value=3, max_value=8, value=5)
            
        if st.button("✨ بناء التشكيلة المثالية"):
            wc_prompt = f"قم ببناء تشكيلة Wildcard كاملة (15 لاعباً) بميزانية {budget}M بأسلوب '{strategy}' للجولات الـ {target_gws} القادمة."
            try:
                with st.spinner("جاري صياغة التشكيلة..."):
                    res_text, used_m = run_fpl_ai(gemini_key, wc_prompt)
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    # 7. رادار الأسعار
    elif page == "📈 رادار الأسعار والتغيرات المباشرة":
        st.header("📈 موجز تغيرات الأسعار المباشرة")
        if st.button("🔄 جلب أحدث تغيرات الأسعار"):
            try:
                with st.spinner("جاري قراءة البيانات الحية..."):
                    res_text, _ = run_fpl_ai(gemini_key, "قدم تقريراً شاملاً بجداول عن أحدث تغيرات الأسعار واللاعبين القريبين من الارتفاع والانخفاض.")
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    # 8. المساعد الصوتي والدردشة
    elif page == "💬 المساعد الصوتي والدردشة المباشرة":
        st.header("🎙️ الاستفسارات المباشرة والدردشة")
        audio_val = st.audio_input("🎙️ سجل استفسارك الصوتي:")
        if audio_val and st.button("🔍 تحليل الصوت"):
            st.info("جارٍ معالجة الصوت...")

        st.markdown("---")
        if "msgs" not in st.session_state:
            st.session_state.msgs = []

        for m in st.session_state.msgs:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if p := st.chat_input("اسأل عن أي درافت، مؤتمر صحفي، لاعب، أو تبديل اليوم..."):
            st.session_state.msgs.append({"role": "user", "content": p})
            with st.chat_message("user"):
                st.markdown(p)

            with st.chat_message("assistant"):
                with st.spinner("جاري التحليل..."):
                    try:
                        ans, _ = run_fpl_ai(gemini_key, p)
                    except Exception as e:
                        ans = f"خطأ: {e}"
                    st.markdown(ans)
                    st.session_state.msgs.append({"role": "assistant", "content": ans})

    # 9. مقارنة الخصم
    elif page == "⚔️ مقارنة التشكيلات (Head-to-Head)":
        st.header("⚔️ مقارنة تشكيلة الخصم")
        c1, c2 = st.columns(2)
        with c1:
            f_m = st.file_uploader("📸 تشكليتك", type=["png", "jpg", "jpeg"], key="m")
        with c2:
            f_r = st.file_uploader("📸 تشكيلة الخصم", type=["png", "jpg", "jpeg"], key="r")

        if f_m and f_r:
            if st.button("🔍 تحليل الفروق ومصدر النقاط"):
                try:
                    with st.spinner("جاري مقارنة التشكيلتين..."):
                        res_text, _ = run_fpl_ai(gemini_key, "قارن بين التشكيلتين واكشف نقاط التفوق لكل فريق.", images=[Image.open(f_m), Image.open(f_r)])
                        st.markdown(res_text)
                except Exception as e:
                    st.error(f"خطأ: {e}")

    # 10. مصفوفة الكابتن
    elif page == "👑 مصفوفة الكابتن المحدثة":
        st.header("👑 ترشيحات شارة الكابتن للجولة")
        gw_num = st.number_input("🎯 رقم الجولة:", min_value=1, max_value=38, value=1)
        if st.button("⚡ ترشيح الكابتن"):
            try:
                with st.spinner("جاري تحليل خيارات الكابتن..."):
                    res_text, _ = run_fpl_ai(gemini_key, f"قدم أفضل 3 خيارات كابتن للجولة {gw_num}.")
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    # 11. استراتيجيات المغامرة
    elif page == "🎯 استراتيجيات المغامرة والريسك":
        st.header("🎯 استشارات المغامرة والريسك")
        strat_choice = st.radio("اختر نوع الريسك:", ["خصم نقاط للتبديلات (-4/-8)", "حرق الميزانية هجومياً", "كابتن Differential", "توقيت الخصائص (Chips)"])
        if st.button("🤖 طلب تقييم المغامرة"):
            try:
                with st.spinner("جاري دراسة نسبة المخاطرة..."):
                    res_text, _ = run_fpl_ai(gemini_key, f"قيم استراتيجية الريسك التالية هذا الأسبوع: {strat_choice}")
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    # 12. تقييم سجل القرارات
    elif page == "📜 سجل وتقييم القرارات الأسبوعي":
        st.header("📜 سجل القرارات والأداء")
        user_log = st.text_area("✍️ ادخل قراراتك في الجولات الأخيرة:")
        if st.button("🧐 تقييم القرارات"):
            if user_log:
                try:
                    with st.spinner("جاري مراجعة الأداء..."):
                        res_text, _ = run_fpl_ai(gemini_key, f"قيم قرارات المدرب التالية واذكر الإيجابيات والسلبيات: {user_log}")
                        st.markdown(res_text)
                except Exception as e:
                    st.error(f"خطأ: {e}")
            else:
                st.warning("ادخل القرارات أولاً.")

else:
    st.info("الرجاء إدخال مفتاح Gemini API للبدء.")
