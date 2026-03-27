import pandas as pd
from fpdf import FPDF

def get_end_time(slots_list, current_index):
    slot = slots_list[current_index]
    if hasattr(slot, 'end_time'):
        return slot.end_time
    if current_index + 1 < len(slots_list):
        return getattr(slots_list[current_index + 1], 'start_time', 'End')
    return "Close"

# --- 1. PURE DATA EXTRACTORS ---
def get_weekly_grid_df(timetable, target_class):
    """Returns pure, unformatted text data so it can be edited by the user."""
    data = []
    days = list(timetable.days.keys())
    daily_slots = timetable.get_day(days[0]).slots
    time_slots = [(getattr(s, 'start_time', '00:00'), get_end_time(daily_slots, i), getattr(s, 'is_break', False)) for i, s in enumerate(daily_slots)]
    
    for start_time, end_time, is_break in time_slots:
        time_str = f"{start_time} - {end_time}" if end_time != "Close" else start_time
        row = {"Time": time_str}
        
        for day in days:
            if is_break:
                row[day] = "BREAK"
                continue
                
            slot = next((s for s in timetable.get_day(day).slots if getattr(s, 'start_time', '') == start_time), None)
            
            cell_text = "" 
            
            if slot and not getattr(slot, 'is_break', False):
                if hasattr(slot, 'assigned_classes'):
                    for assignment in slot.assigned_classes:
                        if assignment['grade'] == target_class:
                            cell_text = f"{assignment['subject']} | {assignment['teacher'].teacher_name} | {assignment['room']}"
                            break
            row[day] = cell_text
        data.append(row)
    return pd.DataFrame(data)

def get_teacher_df(timetable, teacher_name, active_days):
    """Returns pure teacher schedule data for editing."""
    data = []
    for day_name in active_days:
        day = timetable.get_day(day_name)
        if not day: continue
        for i, slot in enumerate(day.slots):
            if getattr(slot, 'is_break', False): continue
            if hasattr(slot, 'assigned_teachers'):
                for assignment in slot.assigned_teachers:
                    if assignment['teacher'].teacher_name == teacher_name:
                        start_t = getattr(slot, 'start_time', '')
                        end_t = get_end_time(day.slots, i)
                        time_str = f"{start_t} - {end_t}" if end_t != "Close" else start_t
                        data.append({
                            "Day": day_name,
                            "Time": time_str,
                            "Subject": assignment['subject'],
                            "Class": assignment['grade'],
                            "Room": assignment['room']
                        })
    return pd.DataFrame(data)

# --- 2. HTML PRESENTATION FORMATTERS ---
def format_html_grid(df):
    """Takes pure data and wraps it in our beautiful HTML UI Cards."""
    html_df = df.copy()
    for col in html_df.columns:
        for i in range(len(html_df)):
            val = str(html_df.iloc[i][col])
            if col == "Time":
                html_df.at[i, col] = f"<div style='color:#2c3e50; font-size:14px; font-weight:bold; text-align:center;'>{val}</div>"
            elif val == "BREAK":
                html_df.at[i, col] = "<div style='text-align:center; background-color:#fcf3cf; color:#d68910; padding:10px; border-radius:5px; border:1px solid #f9e79f;'><b>BREAK</b></div>"
            elif val.strip() == "" or val.lower() in ["nan", "none", "<na>", "free period"]:
                # Draw a clean, blank grey space for empty cells
                html_df.at[i, col] = "<div style='background-color:#f8f9fa; border-radius:6px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);'></div>"
            else:
                parts = val.split(" | ")
                subj = parts[0]
                teacher = parts[1] if len(parts) > 1 else ""
                room = parts[2] if len(parts) > 2 else ""
                html_df.at[i, col] = (
                    f"<div style='background-color:#e8f4f8; padding:8px; border-radius:6px; border-left:5px solid #3498db; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>"
                    f"<b style='color:#2980b9; font-size:14px; margin-bottom:4px; display:block;'>{subj}</b>"
                    f"<span style='color:#34495e; font-size:12px;'>{teacher}</span><br>"
                    f"<span style='color:#e67e22; font-size:12px; font-weight:bold;'> {room}</span>"
                    f"</div>"
                )
    return html_df.to_html(index=False, escape=False)

def format_html_teacher(df):
    """Takes pure teacher data and wraps it in colorful badges."""
    html_df = df.copy()
    for i in range(len(html_df)):
        html_df.at[i, "Time"] = f"<div style='background-color:#eaeded; color:#2c3e50; padding:6px; border-radius:6px; font-weight:bold; text-align:center;'>{html_df.iloc[i]['Time']}</div>"
        
        subj = str(html_df.iloc[i]['Subject'])
        if subj.strip() == "" or subj.lower() in ["nan", "none", "free period"]:
            html_df.at[i, "Subject"] = ""
        else:
            html_df.at[i, "Subject"] = f"<b style='color:#2980b9; font-size:15px;'>{subj}</b>"
            
        cls = str(html_df.iloc[i]['Class'])
        if cls.strip() == "" or cls.lower() in ["nan", "none"]:
            html_df.at[i, "Class"] = ""
        else:
            html_df.at[i, "Class"] = f"<span style='background-color:#ebdef0; color:#8e44ad; padding:6px 12px; border-radius:15px; font-weight:bold; font-size:13px;'>{cls}</span>"
            
        rm = str(html_df.iloc[i]['Room'])
        if rm.strip() == "" or rm.lower() in ["nan", "none"]:
            html_df.at[i, "Room"] = ""
        else:
            html_df.at[i, "Room"] = f"<span style='background-color:#fae5d3; color:#d35400; padding:6px 12px; border-radius:15px; font-weight:bold; font-size:13px;'>{rm}</span>"
            
    return html_df.to_html(index=False, escape=False)

# --- 3. THE PDF GENERATOR ---
def export_to_pdf(df, title, school_name="My School", term="", year=""):
    """Draws a highly colorful, card-based PDF with Official School Headers."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # --- 1. OFFICIAL SCHOOL NAME ---
    pdf.set_font('Arial', 'B', 24) 
    pdf.set_text_color(44, 62, 80) 
    pdf.cell(0, 10, str(school_name).upper(), ln=True, align='C')
    
    # --- 2. SMART TERM & YEAR FORMATTING ---
    pdf.set_font('Arial', 'I', 12)
    pdf.set_text_color(127, 140, 141) 
    
    if term:
        pdf.cell(0, 6, term, ln=True, align='C')
    if year:
        pdf.cell(0, 6, f"Academic Year: {year}", ln=True, align='C')
        
    if term or year:
        pdf.ln(4)
    else:
        pdf.ln(2) 
    
    # --- 3. DOCUMENT TITLE ---
    pdf.set_font('Arial', 'B', 16) 
    pdf.set_text_color(41, 128, 185) 
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(5)
    
    col_width = (pdf.w - 20) / len(df.columns) 
    is_grid = "Monday" in df.columns
    row_height = 24 if is_grid else 14 
    
    pdf.set_font('Arial', 'B', 11) 
    pdf.set_fill_color(44, 62, 80) 
    pdf.set_text_color(255, 255, 255) 
    for col in df.columns:
        pdf.cell(col_width, 12, str(col), border=0, align='C', fill=True)
    pdf.ln(12)
    
    for _, row in df.iterrows():
        x_start = 10 
        y_start = pdf.get_y()
        
        if y_start + row_height > pdf.h - 15:
            pdf.add_page()
            y_start = 10
            pdf.set_font('Arial', 'B', 11)
            pdf.set_fill_color(44, 62, 80) 
            pdf.set_text_color(255, 255, 255) 
            for col in df.columns:
                pdf.cell(col_width, 12, str(col), border=0, align='C', fill=True)
            pdf.ln(12)
            y_start = pdf.get_y()
            
        for col in df.columns:
            val = str(row[col])
            
            if is_grid:
                if col == "Time":
                    pdf.set_fill_color(240, 244, 248) 
                    pdf.rect(x_start, y_start, col_width, row_height, 'DF')
                    pdf.set_font('Arial', 'B', 10) 
                    pdf.set_text_color(44, 62, 80)
                    pdf.set_xy(x_start, y_start + 8)
                    pdf.multi_cell(col_width, 5, val, align='C')
                elif val == "BREAK":
                    pdf.set_fill_color(252, 243, 207) 
                    pdf.rect(x_start + 2, y_start + 2, col_width - 4, row_height - 4, 'F')
                    pdf.set_font('Arial', 'B', 11)
                    pdf.set_text_color(214, 137, 16)
                    pdf.set_xy(x_start, y_start + 10)
                    pdf.cell(col_width, 4, "BREAK", align='C')
                elif val.strip() == "" or val.lower() in ["nan", "none", "<na>", "free period"]:
                    
                    pdf.set_fill_color(248, 249, 250) 
                    pdf.rect(x_start + 2, y_start + 2, col_width - 4, row_height - 4, 'F')
                else:
                    parts = val.split(" | ")
                    subj = parts[0]
                    teacher = parts[1] if len(parts) > 1 else ""
                    room = parts[2] if len(parts) > 2 else ""
                    
                    pdf.set_fill_color(232, 244, 248) 
                    pdf.rect(x_start + 2, y_start + 2, col_width - 4, row_height - 4, 'F')
                    pdf.set_fill_color(52, 152, 219) 
                    pdf.rect(x_start + 2, y_start + 2, 2, row_height - 4, 'F')
                    
                    pdf.set_xy(x_start + 4, y_start + 5)
                    pdf.set_font('Arial', 'B', 11) 
                    pdf.set_text_color(41, 128, 185)
                    pdf.cell(col_width - 8, 4, subj, align='C')
                    
                    pdf.set_xy(x_start + 4, y_start + 11)
                    pdf.set_font('Arial', '', 10) 
                    pdf.set_text_color(52, 73, 94)
                    pdf.cell(col_width - 8, 4, teacher, align='C')
                    
                    pdf.set_xy(x_start + 4, y_start + 17)
                    pdf.set_font('Arial', 'B', 10) 
                    pdf.set_text_color(230, 126, 34)
                    pdf.cell(col_width - 8, 4, room, align='C')
                    
                if col != "Time":
                    pdf.set_draw_color(236, 240, 241)
                    pdf.rect(x_start, y_start, col_width, row_height, 'D')
                
            else:
                pdf.set_draw_color(236, 240, 241)
                if col == "Time":
                    pdf.set_fill_color(240, 244, 248) 
                    pdf.rect(x_start, y_start, col_width, row_height, 'DF')
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_text_color(44, 62, 80)
                elif val.strip() == "" or val.lower() in ["nan", "none", "<na>", "free period"]:
                    pdf.set_fill_color(248, 249, 250) 
                    pdf.rect(x_start, y_start, col_width, row_height, 'DF')
                    pdf.set_xy(x_start, y_start + 5)
                    pdf.cell(col_width, 4, "", align='C') # Empty Text
                elif col == "Subject":
                    pdf.set_fill_color(255, 255, 255)
                    pdf.rect(x_start, y_start, col_width, row_height, 'DF')
                    pdf.set_font('Arial', 'B', 11)
                    pdf.set_text_color(41, 128, 185) 
                elif col == "Class":
                    pdf.set_fill_color(245, 238, 248) 
                    pdf.rect(x_start + 2, y_start + 2, col_width - 4, row_height - 4, 'F') 
                    pdf.rect(x_start, y_start, col_width, row_height, 'D') 
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_text_color(142, 68, 173) 
                elif col == "Room":
                    pdf.set_fill_color(253, 235, 208) 
                    pdf.rect(x_start + 2, y_start + 2, col_width - 4, row_height - 4, 'F') 
                    pdf.rect(x_start, y_start, col_width, row_height, 'D') 
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_text_color(211, 84, 0) 
                else:
                    pdf.set_fill_color(255, 255, 255)
                    pdf.rect(x_start, y_start, col_width, row_height, 'DF')
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_text_color(44, 62, 80)
                
                if val.strip() != "" and val.lower() not in ["nan", "none", "<na>", "free period"]:
                    pdf.set_xy(x_start, y_start + 5)
                    pdf.cell(col_width, 4, val, align='C')
                
            x_start += col_width
            
        pdf.set_y(y_start + row_height)
        
    return pdf.output(dest='S').encode('latin-1')