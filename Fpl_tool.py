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
# 1. جلب التشكيلة المباشرة تلقائياً برقم معرف الفريق (FPL ID)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
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

# ---------------------------------------------------------
# 2. جلب البيانات المباشرة يومياً + اتجاهات الملكية والدرافت
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
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
            
            context_str = "=== أحدث الأخبار والإصابات ===\n" + "\n".join(news_list[:25])
            context_str += "\n\n=== الأكثر تكراراً واختياراً في التشكيلات والدرافتات مؤخراً ===\n" + "\n".join(trending_players)
            return context_str
    except Exception:
        pass
    return "تحديثات المؤتمرات وتوجهات الدرافتات الحية تعتمد على التحليل المباشر للنموذج."

# ---------------------------------------------------------
# 3. توجيهات النظام والذكاء الاصطناعي
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = f"""
أنت خبير ومحلل فانتسي الدوري الإنجليزي الممتاز (FPL) لموسم 2026/2027.
تاريخ اليوم المعتمد للمتابعة: {datetime.date.today().strftime('%Y-%m-%d')} (انطلاق المتابعة اليومية من 20/8/2026 حتى نهاية الموسم).

محاور التركيز الرئيسية للتحليل:
1. تحليلات وتوجهات الدرافتات (Draft Trends) واللاعبين الأكثر تكراراً واختياراً في التشكيلات المُنشأة خلال الـ 3 أيام الماضية (72 ساعة).
2. تحليل المؤتمرات الصحفية المباشرة للمدربين (Manager Press Conferences) وتصريحات اللياقة والمداورة.
3. الالتزام بالقوانين الرسمية: ميزانية الـ 15 لاعباً £100.0M كحد أقصى. الحد الأدنى للحراس والمدافعين £4.0M، وللوسط والمهاجمين £4.5M.
4. تقديم جميع التحليلات في جداول منظمة ونقاط مباشرة ومحددة.
"""

def run_fpl_ai(api_key, prompt, images=None):
    genai.configure(api_key=api_key)
    
    live_context = fetch_live_fpl_data()
    augmented_prompt = f"{SYSTEM_INSTRUCTION}\n\n[البيانات والمستجدات الحية والدرافتات الأخيرة]:\n{live_context}\n\n[طلب المستخدم]:\n{prompt}"
    
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
# 4. الواجهة والشريط الجانبي
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ إعدادات البوت والربط")
    gemini_key = st.text_input("مفتاح Gemini API:", type="password")
    
    st.markdown("---")
    st.header("🔗 ربط حساب الفانتسي")
    saved_fpl_id = st.text_input("رقم معرف فريقك (FPL Team ID):", placeholder="مثال: 123456")
    
    st.markdown("---")
    st.success("🟢 نظام الربط بـ FPL ID + الدرافتات مُفعّل")
    st.caption("تغطية يومية مستمرة لموسم 2026/2027")
    st.markdown("[Google AI Studio](https://aistudio.google.com/app/apikey)")

# إضافة العبارة المطلوبة بخط عريض وكبير ولون أحمر
st.markdown(
    "<h1 style='text-align: center; color: #FF1A1A; font-size: 42px; font-weight: bold; margin-bottom: 10px;'>"
    "( حميدي مطلق ما تفوز علي )"
    "</h1>", 
    unsafe_allow_html=True
)

st.title("⚽ بوت الفانتسي الذكي المباشر - موسم 2026/2027")
st.caption("متابعة يومية برقم ID الفريق، المؤتمرات الصحفية، والدرافتات الحديثة")
st.markdown("---")

# ---------------------------------------------------------
# 5. أقسام البوت المحدثة
# ---------------------------------------------------------
if gemini_key:
    page = st.selectbox(
        "📌 اختر القسم المطلوب للتحليل المباشر:",
        [
            "📊 تحليل التشكيلة والتقرير اليومي", 
            "🔥 رادار الدرافتات واللاعبين الأكثر تكراراً (3 أيام)",
            "🎙️ رادار المؤتمرات الصحفية والإصابات الحية",
            "🃏 مخطط الـ Wildcard والتشكيلة المثالية",
            "📈 رادار الأسعار والتغيرات اليومية",
            "💬 المساعد الصوتي والدردشة المباشرة",
            "⚔️ مقارنة التشكيلات (Head-to-Head)", 
            "👑 مصفوفة الكابتن المحدثة يومياً", 
            "🎯 استراتيجيات المغامرة والريسك",
            "📜 سجل وتقييم القرارات الأسبوعي"
        ]
    )
    st.markdown("---")

    if page == "📊 تحليل التشكيلة والتقرير اليومي":
        st.header("📊 تحليل التشكيلة وتوقع النقاط")
        
        input_method = st.radio("اختر طريقة إدخال التشكيلة:", ["🔗 جلب تلقائي عبر ID الفريق", "📸 رفع لقطة شاشة (صورة)"])
        
        if input_method == "🔗 جلب تلقائي عبر ID الفريق":
            fpl_id_input = st.text_input("ادخل رقم معرف فريقك (FPL Team ID):", value=saved_fpl_id if saved_fpl_id else "")
            
            if st.button("🚀 جلب وتحليل التشكيلة بـ ID"):
                if fpl_id_input:
                    with st.spinner("جاري جلب تشكيلتك المباشرة من سيرفر الفانتسي الرسمية..."):
                        squad_txt, err = fetch_manager_squad(fpl_id_input)
                        if err:
                            st.error(err)
                        else:
                            st.success("تم جلب التشكيلة بنجاح من سيرفر الفانتسي!")
                            st.text_area("📋 التشكيلة المسحوبة:", squad_txt, height=220)
                            
                            prompt = f"""
                            المطلوب تحليل فريق الفانتسي التالي المسحوب مباشرة من الموقع الرسمي:
                            
                            {squad_txt}
                            
                            قدم تقريراً كاملاً يشمل:
                            1. تقييم التشكيلة من 100 بناءً على المؤتمرات والدرافتات في الـ 3 أيام الماضية.
                            2. كشف نقاط الضعف واللاعبين المهددين بالدكة أو الإصابات.
                            3. أفضل تبديلين مقترحين وقرار الكابتن للجولة القادمة.
                            """
                            with st.spinner("جاري تحليل التشكيلة المسحوبة بالذكاء الاصطناعي..."):
                                try:
                                    res_text, used_m = run_fpl_ai(gemini_key, prompt)
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
                    prompt = (
                        "اقرأ اللاعبين في الصورة وقدم تقريراً شاملاً يشمل: "
                        "1. تقييم التشكيلة النهائي من 100 بناءً على أحدث تصريحات المؤتمرات وتوجهات الدرافتات في الـ 3 أيام الماضية. "
                        "2. كشف اللاعبين المصابين أو المهددين بالدكة. "
                        "3. التبديلات المقترحة ومقارنتها باللاعبين الأكثر تكراراً في الدرافتات الأخيرة."
                    )
                    try:
                        with st.spinner("جاري قراءة التشكيلة وتحليلها..."):
                            res_text, used_m = run_fpl_ai(gemini_key, prompt, image)
                            st.session_state['last_analysis'] = res_text
                            st.success(f"تم التحليل عبر: ({used_m})")
                            st.markdown(res_text)
                    except Exception as e:
                        st.error(f"خطأ: {e}")

        if 'last_analysis' in st.session_state:
            st.download_button(
                label="📥 تصدير التقرير التحليلي (TXT)",
                data=st.session_state['last_analysis'].encode('utf-8'),
                file_name=f"FPL_Report_{datetime.date.today()}.txt",
                mime="text/plain; charset=utf-8"
            )

    elif page == "🔥 رادار الدرافتات واللاعبين الأكثر تكراراً (3 أيام)":
        st.header("🔥 تحليلات اللاعبين الأكثر تكراراً في الدرافتات الحديثة")
        pos_filter = st.selectbox("🎯 تصفية حسب المركز:", ["الكل", "حراس المرمى", "المدافعون", "خط الوسط", "المهاجمون"])
        
        if st.button("🔍 كشف أكثر اللاعبين تكراراً في الدرافتات الأخيرة"):
            draft_prompt = f"""
            قدم تحليلاً دقيقاً لأكثر اللاعبين تكراراً واختياراً في الدرافتات والتشكيلات الجديدة خلال الـ 3 أيام الماضية لموسم 2026/2027:
            1. أكثر 5 لاعبين تكراراً واختياراً (النادي، السعر، سبب الإقبال عليهم).
            2. خيارات تفاضلية (Differential Drafts) بدأت تظهر مؤخراً.
            {"3. التركيز على مركز: " + pos_filter if pos_filter != "الكل" else ""}
            نسق النتائج في جداول واضحة.
            """
            try:
                with st.spinner("جاري تجميع بيانات الدرافتات والترندات..."):
                    res_text, _ = run_fpl_ai(gemini_key, draft_prompt)
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    elif page == "🎙️ رادار المؤتمرات الصحفية والإصابات الحية":
        st.header("🎙️ رادار تصريحات المدربين والمؤتمرات الصحفية")
        manager_query = st.text_input("🔍 استعلم عن نادي أو مدرب محدد:")
        
        if st.button("🔄 جلب ملخص المؤتمرات الصحفية للجولة"):
            press_prompt = f"""
            قدم ملخصاً تحليلياً شاملاً لأهم ما ورد في المؤتمرات الصحفية لمدربي البريميرليج هذا الأسبوع لموسم 2026/2027:
            1. تصريحات اللياقة والإصابات المؤكدة والشكوك لكل فريق.
            2. تلميحات المدربين بشأن المداورة وتوزيع الأوراق الهجومية.
            {"3. تركيز خاص على تصريحات ومؤتمر: " + manager_query if manager_query else ""}
            نسق التقرير في جداول واضحة ومبسطة.
            """
            try:
                with st.spinner("جاري تحليل وتلخيص تصريحات المؤتمرات الصحفية..."):
                    res_text, _ = run_fpl_ai(gemini_key, press_prompt)
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    elif page == "🃏 مخطط الـ Wildcard والتشكيلة المثالية":
        st.header("🃏 بناء تشكيلة الـ Wildcard المحدثة")
        wc1, wc2 = st.columns(2)
        with wc1:
            budget = st.number_input("💰 الميزانية المتاحة (£M):", min_value=80.0, max_value=110.0, value=100.0, step=0.5)
            strategy = st.selectbox("🎯 الأسلوب التكتيكي:", ["متوازنة", "هجوم ناري", "دفاع صلب برخص بالوسط", "مغامرة Differential"])
        with wc2:
            target_gws = st.slider("🗓️ التخطيط للجولات القادمة:", min_value=3, max_value=8, value=5)
            
        if st.button("✨ بناء التشكيلة المثالية"):
            wc_prompt = f"قم ببناء تشكيلة Wildcard كاملة (15 لاعباً) بميزانية {budget}M بأسلوب '{strategy}' للجولات الـ {target_gws} القادمة مع مراعاة التشكيلات الأكثر تكراراً في الدرافتات الأخيرة والمؤتمرات الصحفية."
            try:
                with st.spinner("جاري صياغة التشكيلة..."):
                    res_text, used_m = run_fpl_ai(gemini_key, wc_prompt)
                    st.success(f"المحرك: ({used_m})")
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

    elif page == "📈 رادار الأسعار والتغيرات اليومية":
        st.header("📈 موجز تغيرات الأسعار المباشرة")
        if st.button("🔄 جلب أحدث تغيرات الأسعار"):
            radar_prompt = "قدم تقريراً شاملاً بجداول عن أحدث تغيرات الأسعار، واللاعبين المتوقع ارتفاع أو انخفاض أسعارهم هذا الأسبوع بناءً على التحركات وسوق الانتقالات."
            try:
                with st.spinner("جاري قراءة البيانات الحية..."):
                    res_text, _ = run_fpl_ai(gemini_key, radar_prompt)
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

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
                        res_text, _ = run_fpl_ai(gemini_key, "قارن بين التشكيلتين واكشف نقاط التفوق لكل فريق بناءً على جاهزية اللاعبين واتجاهات الدرافت الحديثة.", images=[Image.open(f_m), Image.open(f_r)])
                        st.markdown(res_text)
                except Exception as e:
                    st.error(f"خطأ: {e}")

    elif page == "👑 مصفوفة الكابتن المحدثة يومياً":
        st.header("👑 ترشيحات شارة الكابتن للجولة")
        gw_num = st.number_input("🎯 رقم الجولة:", min_value=1, max_value=38, value=1)
        if st.button("⚡ ترشيح الكابتن"):
            try:
                with st.spinner("جاري تحليل خيارات الكابتن..."):
                    res_text, _ = run_fpl_ai(gemini_key, f"قدم أفضل 3 خيارات كابتن للجولة {gw_num} (خيار أمان، خيار وسط ممتاز، وخيار Differential) بناءً على المواجهات وتوجهات التشكيلات والدرافتات الأخيرة.")
                    st.markdown(res_text)
            except Exception as e:
                st.error(f"خطأ: {e}")

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