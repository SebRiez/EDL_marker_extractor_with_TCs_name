# Script created by Sebastian Riezler, refactored for clarity and maintainability
# Updated with Duration (TC) column
import re
import io
import math
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Pattern

# =============================================
# CONSTANTS & CONFIGURATION
# =============================================
COLOR_HEX_MAP = {
    'Blue': '#0074D9', 'Cyan': '#00B8D4', 'Green': '#2ECC40',
    'Yellow': '#FFDC00', 'Red': '#FF4136', 'Orange': '#FF851B',
    'Magenta': '#FF4136', 'Purple': '#B10DC9', 'Fuchsia': '#F012BE',
    'Rose': '#F5B0C4', 'Sky': '#87CEEB', 'Mint': '#98FB98',
    'Lemon': '#FFFACD', 'Sand': '#F4A460', 'Cocoa': '#6F4E37',
    'White': '#FFFFFF', 'Black': '#000000', 'Denim': '#1560BD'
}
COLOR_OPTIONS = list(COLOR_HEX_MAP.keys())
FILTER_COLOR_OPTIONS = ["All Colors"] + COLOR_OPTIONS

FPS_OPTIONS = {
    "23.98 fps": 23.976,
    "24 fps": 24,
    "25 fps": 25,
    "29.97 fps": 29.97,
    "30 fps": 30,
    "59.94 fps": 59.94,
    "60 fps": 60
}

EVENT_PATTERN: Pattern = re.compile(r"^\s*(\d{3,6})\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")
CLIP_NAME_PATTERN: Pattern = re.compile(r"\*FROM CLIP NAME:\s+(.*)")
LOC_PATTERN: Pattern = re.compile(r"\*\s*LOC:?\s+(\d{2}:\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)", re.IGNORECASE)
SHOT_ID_PATTERN: Pattern = re.compile(r"([A-Z]{3}_\d{3}_\d{4}|[A-Z]{3}_\d{4}|CS\d{4})")

# =============================================
# UTILITY FUNCTIONS
# =============================================
def timecode_to_frames(tc: str, fps: float, drop_frame: bool = False) -> int:
    try:
        h, m, s, f = map(int, tc.strip().split(":"))
        if drop_frame and fps == 29.97:
            drop_frames = math.floor(fps * 0.066666)
            total_minutes = h * 60 + m
            frames = (
                (fps * 3600 * h) + (fps * 60 * m) + (fps * s) + f -
                (drop_frames * (total_minutes - total_minutes // 10))
            )
            return round(frames)
        return round(h * 3600 * fps + m * 60 * fps + s * fps + f)
    except:
        return 0

def frames_to_timecode(frames: int, fps: float) -> str:
    """Konvertiert Frame-Anzahl zurück in HH:MM:SS:FF."""
    if frames < 0: frames = 0
    total_seconds = frames / fps
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    f = int(round((total_seconds - int(total_seconds)) * fps))
    
    if f >= int(round(fps)):
        f = 0
        s += 1
    if s >= 60:
        s = 0
        m += 1
    if m >= 60:
        m = 0
        h += 1
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

def calculate_duration_frames(tc_in: str, tc_out: str, fps: float, drop_frame: bool = False, exclude_last: bool = False) -> int:
    f_out = timecode_to_frames(tc_out, fps, drop_frame)
    f_in = timecode_to_frames(tc_in, fps, drop_frame)
    dur = f_out - f_in
    return max(dur - 1, 0) if exclude_last else dur

def extract_shot_id(text: str) -> str:
    match = SHOT_ID_PATTERN.search(text)
    return match.group(1) if match else ""

def extract_locator_components(loc_line: str) -> Tuple[str, str, str]:
    match = LOC_PATTERN.match(loc_line.strip())
    return (match.group(1), match.group(2), match.group(3).strip()) if match else ("", "", "")

# =============================================
# MAIN PARSING LOGIC
# =============================================
def parse_edl(edl_lines, selected_fps, is_drop_frame, selected_color, inc_tape, inc_clip, only_loc, excl_last):
    loc_rows = []
    events_map = {}
    current_event = None
    current_clipname = ""
    color_filter = selected_color != "All Colors"

    for line in edl_lines:
        ev_match = EVENT_PATTERN.match(line)
        if ev_match:
            current_event = ev_match.group(1)
            events_map[current_event] = {
                "tape": ev_match.group(2), "src_in": ev_match.group(3),
                "src_out": ev_match.group(4), "rec_in": ev_match.group(5),
                "rec_out": ev_match.group(6), "clip": ""
            }
            continue

        if line.strip().startswith("*FROM CLIP NAME:"):
            name_match = CLIP_NAME_PATTERN.match(line.strip())
            if name_match and current_event in events_map:
                events_map[current_event]["clip"] = name_match.group(1).strip()

        if "*LOC" in line:
            l_tc, l_col, l_desc = extract_locator_components(line)
            if color_filter and l_col.lower() != selected_color.lower(): continue
            
            base = events_map.get(current_event, {})
            dur = calculate_duration_frames(base.get("src_in", ""), base.get("src_out", ""), selected_fps, is_drop_frame, excl_last)
            
            row = {
                "Event": current_event, "Shot ID": extract_shot_id(l_desc),
                "Src_In": base.get("src_in", ""), "Src_Out": base.get("src_out", ""),
                "Duration (Frames)": dur, "Duration (TC)": frames_to_timecode(dur, selected_fps),
                "Rec_In": base.get("rec_in", ""), "Rec_Out": base.get("rec_out", ""),
                "*LOC TC": l_tc, "*LOC Color": l_col, "*LOC Description": l_desc
            }
            if inc_tape: row["Tapename"] = base.get("tape", "")
            if inc_clip: row["Clipname"] = base.get("clip", "")
            loc_rows.append(row)

    if not loc_rows: return pd.DataFrame()
    df = pd.DataFrame(loc_rows)
    cols = ["Event", "Shot ID"]
    if inc_tape: cols.append("Tapename")
    if inc_clip: cols.append("Clipname")
    cols.extend(["Src_In", "Src_Out", "Duration (Frames)", "Duration (TC)", "Rec_In", "Rec_Out", "*LOC TC", "*LOC Color", "*LOC Description"])
    return df.reindex(columns=[c for c in cols if c in df.columns])

# =============================================
# STREAMLIT UI
# =============================================
def main():
    st.set_page_config(page_title="EDL Locator Extractor", layout="centered")
    st.markdown("""<style>
        .stApp { background-color: #1E2025; color: #F0F0F0; }
        .main-header { background: linear-gradient(135deg, #42B38F 0%, #80ED99 100%); padding: 2.5rem; border-radius: 1.5rem; text-align: center; color: #1E2025; margin-bottom: 2rem; }
        .glass-container { background: #2D2F34; border-radius: 1.5rem; padding: 2rem; margin-bottom: 1.5rem; border: 1px solid rgba(240,240,240,0.1); }
        .stButton button { background: #42B38F !important; color: #1E2025 !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown('<div class="main-header"><h1>🎬 EDL Locator Extractor</h1><p>Extract locator data and durations</p></div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        fps_label = c1.selectbox("🎞️ FPS", list(FPS_OPTIONS.keys()), index=2)
        fps = FPS_OPTIONS[fps_label]
        preview_limit = c2.number_input("🔢 Preview Lines", min_value=50, value=50)
        sel_color = c3.selectbox("🎨 Filter Color", FILTER_COLOR_OPTIONS)
        
        cc1, cc2, cc3, cc4 = st.columns(4)
        inc_t = cc1.checkbox("📼 Tapename", value=True)
        inc_c = cc2.checkbox("🎬 Clipname", value=True)
        o_loc = cc3.checkbox("📝 Only *LOC", value=True)
        excl = cc4.checkbox("➖ Excl. Last Frame", value=False)
        st.markdown('</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📤 Upload EDL", type=["edl", "txt"])
    if uploaded_file:
        lines = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
        df = parse_edl(lines, fps, (fps in [29.97, 59.94]), sel_color, inc_t, inc_c, o_loc, excl)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False), f"processed_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
