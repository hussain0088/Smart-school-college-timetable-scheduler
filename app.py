import streamlit as st
import pandas as pd
import base64
from model.entities import Teacher, SchoolClass
from model.timetable_logic import WeeklyTimetable
from logic.scheduler import Scheduling 
import dashboard as db

# Page Configuration
st.set_page_config(page_title=" AI Timetable Scheduler", layout="wide")

# --- LOAD EXTERNAL CSS ---
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css("style.css")

# --- BACKGROUND PHOTO INJECTION ---
def add_bg_image(image_file):
    try:
        with open(image_file, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{b64_img}");
            background-size: 100% 100%; 
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """, unsafe_allow_html=True)
    except Exception:
        pass 

add_bg_image("bg1.jpg")

# --- IDM DOWNLOADER ---
def generate_pdf_fast(df, title, school_name, term, year):
    return db.export_to_pdf(df, title, school_name, term, year)

def create_download_link(pdf_bytes, filename, button_text):
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    return f'<a href="data:application/pdf;base64,{b64_pdf}" download="{filename}" class="idm-download-btn">{button_text}</a>'

# --- SESSION STATE ---
if 'timetable' not in st.session_state: st.session_state.timetable = None
if 'active_days' not in st.session_state:
    st.session_state.active_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.header("Configuration")
    st.divider()
    
    with st.expander("Smart Timetable Details", expanded=True):
        st.caption("Type your school details below.")
        
        doc_school_name = st.text_input("School Name", placeholder="", value="")
        doc_term = st.text_input("Timetable Term", placeholder="", value="")
        doc_year = st.text_input("Academic Year", placeholder=" ", value="")
        
        safe_school_name = doc_school_name if doc_school_name.strip() else "OFFICIAL SCHOOL TIMETABLE"
        safe_term = doc_term.strip()
        safe_year = doc_year.strip()

    with st.expander("School Days", expanded=False):
        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday","Sunday"]
        st.session_state.active_days = [d for d in all_days if st.checkbox(d, value=(d in st.session_state.active_days))]

    with st.expander("Time Settings", expanded=False):
        start_time = st.time_input("School Start", value=pd.to_datetime("08:00").time())
        duration = st.number_input("Period", 30, 60, 45)
        
        st.markdown("**Closing Times**")
        col_f, col_r = st.columns(2)
        with col_f:
            fri_limit = st.time_input("Friday", value=pd.to_datetime("12:30").time()).strftime("%H:%M")
        with col_r:
            reg_limit = st.time_input("Regular", value=pd.to_datetime("14:30").time()).strftime("%H:%M")

    with st.expander("Break Settings", expanded=False):
        enable_break = st.toggle("Include Break Time", value=True)
        break_after = st.number_input("After Period", 1, 8, 2, disabled=not enable_break)
        break_dur = st.selectbox("Minutes", [20, 30, 45, 60], index=1, disabled=not enable_break)
        safe_break_after = break_after if enable_break else 99 
        safe_break_dur = break_dur if enable_break else 0

# --- SMART RESOURCE VALIDATOR ---
def validate_resources(df_t, df_c, df_s):
    days_count = len(st.session_state.active_days)
    sub_periods = {str(r['subject_name']).strip().lower(): int(float(r['periods_per_week'])) for _, r in df_s.iterrows()}
    
    teachers = []
    for _, t_row in df_t.iterrows():
        teachers.append({
            'name': str(t_row['name']).strip(),
            'expertise': [e.strip().lower() for e in str(t_row['expertise']).split(',')],
            'classes': [c.strip().lower() for c in str(t_row['assigned_classes']).split(',')],
            'capacity': int(float(t_row['max_load_per_day'])) * days_count,
            'daily_limit': int(float(t_row['max_load_per_day']))
        })

    class_demands = []
    total_demand = 0
    for _, c_row in df_c.iterrows():
        class_name = str(c_row['class_name']).strip().lower()
        c_subs = [s.strip().lower() for s in str(c_row['assigned_subjects']).split(',')]
        for sub in c_subs:
            if sub in sub_periods:
                periods = sub_periods[sub]
                class_demands.append({
                    'class_lower': class_name, 
                    'sub': sub, 
                    'periods': periods, 
                    'original_class': str(c_row['class_name']).strip()
                })
                total_demand += periods

    total_supply = sum(t['capacity'] for t in teachers)
    
    st.markdown("### Resource Audit Report")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"<div class='metric-box'><b>Required Periods</b><br><h2>{total_demand}</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-box'><b>Available Capacity</b><br><h2>{total_supply}</h2></div>", unsafe_allow_html=True)
    with c3:
        diff = total_supply - total_demand
        status = "Overall Surplus" if diff >= 0 else "Overall Shortage"
        # Uses standard HTML logic without hardcoded inline CSS colors where possible
        st.markdown(f"<div class='metric-box'><b>{status}</b><br><h2>{abs(diff)}</h2></div>", unsafe_allow_html=True)

    errors = []

    for demand in class_demands:
        capable_teachers = [t for t in teachers if demand['sub'] in t['expertise'] and demand['class_lower'] in t['classes']]
        if not capable_teachers:
            errors.append(f"**{demand['original_class']}** needs **{demand['sub'].upper()}**, but NO teacher is assigned to teach it to this class!")
        else:
            combined_capacity = sum(t['capacity'] for t in capable_teachers)
            if combined_capacity < demand['periods']:
                errors.append(f"**{demand['original_class']} - {demand['sub'].upper()}**: Needs {demand['periods']} periods/week, but assigned teachers only have {combined_capacity} combined capacity.")

    for t in teachers:
        exclusive_burden = 0
        for demand in class_demands:
            capable_teachers = [ct for ct in teachers if demand['sub'] in ct['expertise'] and demand['class_lower'] in ct['classes']]
            
            if len(capable_teachers) == 1 and capable_teachers[0]['name'] == t['name']:
                exclusive_burden += demand['periods']
                
        if exclusive_burden > t['capacity']:
            errors.append(f"**Teacher Overload - {t['name']}**: They are the *only* teacher assigned to certain subjects/classes needing **{exclusive_burden} periods/week**. Their max load is **{t['capacity']}** (Max {t['daily_limit']}/day). Increase their max_load_per_day or assign a helper teacher.")

    if errors:
        st.error("**Action Required: Resource Limitations Detected!**")
        st.markdown("#### Exact Problems Found:")
        for e in sorted(list(set(errors))):
            st.warning(e)
        return False
        
    elif total_supply < total_demand:
        st.error(f"**Action Required:** Your school needs **{total_demand}** total periods, but teachers can only teach **{total_supply}**.")
        return False
        
    st.success("**Perfect!** Your teachers have enough capacity to handle the workload. The AI is ready to schedule.")
    return True

# --- MAIN UI ---
st.title("Smart Timetable Scheduler")
st.markdown("<div class='hero-subtitle'>Upload your school data and let AI generate timetables.</div>", unsafe_allow_html=True)

if st.session_state.timetable is None:
    
    with st.expander("READ BEFORE UPLOADING: Required CSV Formats & Examples", expanded=False):
        st.markdown("Your CSV or Excel files **must** have these exact column headers for the AI to understand them:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            **1. Teachers List** *(5 Columns)*<br> `id`, `name`, `expertise`, `assigned_classes`, `max_load_per_day`
            <div class="example-box example-blue">
                <b>Example Row in Excel:</b><br><br>
                <code>T01</code> | <code>Mr. Ali</code> | <code>English</code> | <code>9th-A, 10th-B</code> | <code>5</code>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            **2. Class List** *(3 Columns)*<br> `class_name`, `assigned_subjects`, `room_no`
            <div class="example-box example-yellow">
                <b>Example Row in Excel:</b><br><br>
                <code>9th-A</code> | <code>Math, English, Physics</code> | <code>Room-01</code>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            **3. Subject Loads** *(2 Columns)*<br> `subject_name`, `periods_per_week`
            <div class="example-box example-red">
                <b>Example Row in Excel:</b><br><br>
                <code>English</code> | <code>6</code>
            </div>
            """, unsafe_allow_html=True)
            
        st.info(" **Pro Tip:** If a teacher teaches multiple classes (or a class takes multiple subjects), just type them all in the same box and separate them with a comma! Example: `Math, Physics`")
    
    st.write("") 

    with st.container():
        u1, u2, u3 = st.columns(3)
        t_file = u1.file_uploader("1.Upload Teachers File", type="csv")
        c_file = u2.file_uploader("2.Upload Classes File", type="csv")
        s_file = u3.file_uploader("3.Upload Subjects File", type="csv")

    st.write("") 
    
    _, col_btn, _ = st.columns([1, 2, 1]) 
    with col_btn:
        generate_pressed = st.button("Generate AI Timetable", type="primary", use_container_width=True)

    if generate_pressed:
        if t_file and c_file and s_file:
            try:
                df_t = pd.read_csv(t_file).fillna("")
                df_c = pd.read_csv(c_file).fillna("")
                df_s = pd.read_csv(s_file).fillna(0)
                
                if validate_resources(df_t, df_c, df_s):
                    sub_cfg = {str(r['subject_name']).strip().lower(): {"count": int(float(r['periods_per_week']))} for _, r in df_s.iterrows()}
                    t_obj = [Teacher(str(r['id']).strip(), str(r['name']).strip(), str(r['expertise']).strip().lower(), str(r['assigned_classes']).strip(), int(float(r['max_load_per_day']))) for _, r in df_t.iterrows()]
                    c_obj = [SchoolClass(str(r['class_name']).strip(), str(r['assigned_subjects']).strip(), str(r['room_no']).strip()) for _, r in df_c.iterrows()]
                    
                    timetable = WeeklyTimetable(school_name="Pro Scheduler")
                    timetable.create_week(st.session_state.active_days, start_time.strftime("%H:%M"), duration, fri_limit, reg_limit, safe_break_after, safe_break_dur)
                    
                    engine = Scheduling(t_obj, c_obj, sub_cfg, timetable)
                    engine.generate()

                    st.session_state.timetable = timetable
                    st.session_state.teachers_obj = t_obj
                    st.session_state.classes_list = [c.class_name for c in c_obj]
                    st.balloons()
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Logical Error: {e}")
        else:
            st.warning("⚠️ Please upload all three files to proceed.")

else:
    if st.button(" Upload New Data"):
        st.session_state.timetable = None
        st.rerun()

# --- OUTPUT DASHBOARD ---
if st.session_state.timetable:
    st.divider()
    t1, t2 = st.tabs(["Classes Schedules", "Teachers Schedules"])
    
    with t1:
        sel_class = st.selectbox("Select Class:", st.session_state.classes_list)
        raw_grid_df = db.get_weekly_grid_df(st.session_state.timetable, sel_class)
        
        edit_mode = st.toggle("Make Manual Changes", key=f"edit_grid_{sel_class}")
        
        if edit_mode:
            st.info("**Manual Edit Mode:** Double-click any cell to change it. Use the format `SUBJECT | Teacher | Room`.")
            final_grid_df = st.data_editor(raw_grid_df, use_container_width=True, hide_index=True)
        else:
            final_grid_df = raw_grid_df
            st.markdown(db.format_html_grid(final_grid_df), unsafe_allow_html=True)
        
        pdf_bytes = generate_pdf_fast(final_grid_df, f"Class {sel_class} Schedule", safe_school_name, safe_term, safe_year)
        btn_html = create_download_link(pdf_bytes, f"Class_{sel_class}_Timetable.pdf", f"Download {sel_class} Schedule")
        st.markdown(btn_html, unsafe_allow_html=True)

    with t2:
        t_names = [t.teacher_name for t in st.session_state.teachers_obj]
        sel_t = st.selectbox("Select Teacher:", t_names)
        raw_t_sched = db.get_teacher_df(st.session_state.timetable, sel_t, st.session_state.active_days)
        
        if not raw_t_sched.empty:
            day_mapping = {
                "Monday": 1, "Tuesday": 2, "Wednesday": 3, 
                "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7
            }
            raw_t_sched['Day_Order'] = raw_t_sched['Day'].map(day_mapping)
            raw_t_sched = raw_t_sched.sort_values(['Day_Order', 'Time']).drop('Day_Order', axis=1).reset_index(drop=True)
            
            edit_mode_t = st.toggle(" Make Manual Changes", key=f"edit_list_{sel_t}")
            
            if edit_mode_t:
                st.info(" **Manual Edit Mode:** Double-click any cell to type a new Subject, Class, or Room.")
                final_t_sched = st.data_editor(raw_t_sched, use_container_width=True, hide_index=True)
            else:
                final_t_sched = raw_t_sched
                st.markdown(db.format_html_teacher(final_t_sched), unsafe_allow_html=True)
            
            pdf_bytes = generate_pdf_fast(final_t_sched, f"Teacher Schedule - {sel_t}", safe_school_name, safe_term, safe_year)
            btn_html = create_download_link(pdf_bytes, f"Teacher_{sel_t}_Schedule.pdf", f"Download {sel_t}'s Schedule")
            st.markdown(btn_html, unsafe_allow_html=True)