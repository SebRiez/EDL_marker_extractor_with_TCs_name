# Script created by Sebastian Riezler with ChatGpt
# c 2025/06

import streamlit as st
import pandas as pd
import re
import io
import math
from datetime import datetime

# App config
st.set_page_config(page_title="EDL locator extractor", layout="wide")

# 💡 CSS for compact inputs
st.markdown("""
<style>
.small-box .stSelectbox, .small-box .stNumberInput, .small-box .stCheckbox {
    width: fit-content !important;
    min-width: 160px;
}
</style>
""", unsafe_allow_html=True)

# 🎬 Title box
st.markdown("""
<div style="display: flex; justify-content: center;">
  <div style='background-color:#e0f0ff;padding:10px 20px;border-radius:10px;
              border:1px solid #b3d1f0; text-align:center; display:inline-block;'>
    <h2 style='color:#003366; margin: 0;'>🎬 EDL locator extractor 🎬 </h2>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Upload an EDL file (optimized for File32 EDL) to extract all `*LOC` entries along with their timecodes and metadata.  
If your EDL contains `Tapename` and `Clipname`, you can check below whether they should be inserted into the CSV (not active yet)
""")

# 🧮 FPS & preview inputs
fps_options = {
    "23.98 fps": 23.976,
    "24 fps": 24,
    "25 fps": 25,
    "29.97 fps": 29.97,
    "30 fps": 30,
    "59.94 fps": 59.94,
    "60 fps": 60
}

with st.container():
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        with st.container():
            st.markdown('<div class="small-box">', unsafe_allow_html=True)
            selected_fps_label = st.selectbox("🎞️ FPS", list(fps_options.keys()), index=2)
            st.markdown("</div>", unsafe_allow_html=True)
            selected_fps = fps_options[selected_fps_label]

    with col2:
        with st.container():
            st.markdown('<div class="small-box">', unsafe_allow_html=True)
            preview_limit = st.number_input("🔢 Preview lines", min_value=50, value=50, step=10, format="%d")
            st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        if selected_fps in [29.97, 59.94]:
            with st.container():
                st.markdown('<div class="small-box">', unsafe_allow_html=True)
                is_drop_frame = st.checkbox("🧮 Drop-Frame", value=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            is_drop_frame = False

# 🆕 Checkboxen für Anzeigeoptionen (inline)
st.markdown("""
<div style="display: flex; gap: 2em; align-items: center; justify-content: center;">
    <div>
        <label><input type="checkbox" checked disabled style="pointer-events: none; margin-right: 0.5em;">📼 tapename</label>
    </div>
    <div>
        <label><input type="checkbox" checked disabled style="pointer-events: none; margin-right: 0.5em;">🎬 clipname</label>
    </div>
</div>
""", unsafe_allow_html=True)

# ➕ NEW: Export mode
export_only_loc = st.checkbox("Export only *LOC entries", value=True,
                              help="Turn off to export ALL events. Events without *LOC will have empty locator fields; events with multiple LOCs will be duplicated per locator.")

# 🕒 Timecode tools
def timecode_to_frames(tc, fps, drop_frame=False):
    h, m, s, f = map(int, tc.strip().split(":"))
    if drop_frame and fps == 29.97:
        drop_frames = math.floor(fps * 0.066666)
        total_minutes = h * 60 + m
        frames = (
            (fps * 3600 * h) +
            (fps * 60 * m) +
            (fps * s) +
            f -
            (drop_frames * (total_minutes - total_minutes // 10))
        )
        return round(frames)
    else:
        return round(h * 3600 * fps + m * 60 * fps + s * fps + f)

def extract_shot_id(text):
    # keep your patterns; extend as needed
    match = re.search(r"(MUM_\d{3}_\d{4}|CS\d{4})", text)
    return match.group(1) if match else ""

def extract_locator_components(loc_line):
    match = re.match(r"\*\s*LOC:?\s+(\d{2}:\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)", loc_line.strip(), re.IGNORECASE)
    if match:
        return match.group(1), match.group(2), match.group(3).strip()
    else:
        return "", "", ""

# 📤 File upload
uploaded_file = st.file_uploader("📤 Upload your EDL file", type=["edl", "txt"])

if uploaded_file:
    edl_text = uploaded_file.read().decode("utf-8", errors="ignore")
    edl_lines = edl_text.splitlines()
    preview_lines = edl_lines[:int(preview_limit)]

    highlighted_lines = []
    for line in preview_lines:
        if re.search(r"\*\s*LOC", line):
            highlighted_lines.append(f'<div style="background-color:#228B22;color:white;padding:2px;">{line}</div>')
        else:
            highlighted_lines.append(f'<div>{line}</div>')
    st.subheader(f"📝 Preview of EDL (first {int(preview_limit)} lines, *LOC highlighted)")
    st.markdown("<br>".join(highlighted_lines), unsafe_allow_html=True)

    if len(edl_lines) > preview_limit:
        st.info(f"The EDL contains {len(edl_lines)} total lines. Only the first {int(preview_limit)} are shown above.")

    # 🔍 Main parsing
    loc_rows = []                       # rows that correspond to actual *LOC lines
    events_order = []                   # keep appearance order of events
    events_map = {}                     # event_number -> dict of base metadata (no locator)
    current_event_number = None
    current_timecodes = None
    current_clipname = ""
    current_tape_name = ""

    event_pattern = re.compile(r"^\s*(\d{3,6})\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")

    for line in edl_lines:
        event_match = event_pattern.match(line)
        if event_match:
            current_event_number = event_match.group(1)
            current_tape_name = event_match.group(2)
            current_timecodes = {
                "src_in": event_match.group(3),
                "src_out": event_match.group(4),
                "rec_in": event_match.group(5),
                "rec_out": event_match.group(6),
            }
            # register/update event base info
            if current_event_number not in events_map:
                events_order.append(current_event_number)
            events_map[current_event_number] = {
                "tape_name": current_tape_name or "",
                "clip_name": current_clipname or "",  # may be updated later
                "src_in": current_timecodes["src_in"] if current_timecodes else "",
                "src_out": current_timecodes["src_out"] if current_timecodes else "",
                "rec_in": current_timecodes["rec_in"] if current_timecodes else "",
                "rec_out": current_timecodes["rec_out"] if current_timecodes else "",
            }
            continue

        if line.strip().startswith("*FROM CLIP NAME:"):
            clip_name_match = re.match(r"\*FROM CLIP NAME:\s+(.*)", line.strip())
            if clip_name_match:
                current_clipname = clip_name_match.group(1).strip()
                # propagate clip name to last seen event if present
                if current_event_number and current_event_number in events_map:
                    events_map[current_event_number]["clip_name"] = current_clipname

        if re.search(r"\*\s*LOC", line):
            locator_tc, locator_color, loc_description = extract_locator_components(line)
            shot_id = extract_shot_id(loc_description)

            try:
                frames_in = timecode_to_frames(current_timecodes["src_in"], selected_fps, is_drop_frame) if current_timecodes else None
                frames_out = timecode_to_frames(current_timecodes["src_out"], selected_fps, is_drop_frame) if current_timecodes else None
                cut_range = frames_out - frames_in if frames_in is not None and frames_out is not None else None
            except Exception:
                cut_range = None

            loc_rows.append({
                "event_number": current_event_number or "",
                "shot_id": shot_id,
                "tape_name": current_tape_name or "",
                "clip_name": current_clipname or "",
                "src_in": current_timecodes["src_in"] if current_timecodes else "",
                "src_out": current_timecodes["src_out"] if current_timecodes else "",
                "cut_range (frames)": cut_range,
                "rec_in": current_timecodes["rec_in"] if current_timecodes else "",
                "rec_out": current_timecodes["rec_out"] if current_timecodes else "",
                "locator_timecode": locator_tc,
                "locator_color": locator_color,
                "locator_text": loc_description
            })

    # 📦 Build output according to export mode
    column_order = [
        "event_number", "shot_id", "tape_name", "clip_name",
        "src_in", "src_out", "cut_range (frames)",
        "rec_in", "rec_out",
        "locator_timecode", "locator_color", "locator_text"
    ]

    if export_only_loc:
        # Only rows with *LOC
        if loc_rows:
            df_out = pd.DataFrame(loc_rows)[column_order]
        else:
            df_out = pd.DataFrame(columns=column_order)
    else:
        # ALL events: merge base event rows with locators
        merged_rows = []
        # build a quick index of locs by event
        loc_by_event = {}
        for row in loc_rows:
            loc_by_event.setdefault(row["event_number"], []).append(row)

        for ev in events_order:
            base = events_map.get(ev, {})
            # compute cut_range for base row too
            try:
                frames_in = timecode_to_frames(base.get("src_in","00:00:00:00"), selected_fps, is_drop_frame) if base.get("src_in") else None
                frames_out = timecode_to_frames(base.get("src_out","00:00:00:00"), selected_fps, is_drop_frame) if base.get("src_out") else None
                cut_range = frames_out - frames_in if frames_in is not None and frames_out is not None else None
            except Exception:
                cut_range = None

            if ev in loc_by_event:
                # add one row per locator (preserve full locator info)
                merged_rows.extend(loc_by_event[ev])
            else:
                # add a base row with empty locator fields
                merged_rows.append({
                    "event_number": ev,
                    "shot_id": "",
                    "tape_name": base.get("tape_name",""),
                    "clip_name": base.get("clip_name",""),
                    "src_in": base.get("src_in",""),
                    "src_out": base.get("src_out",""),
                    "cut_range (frames)": cut_range,
                    "rec_in": base.get("rec_in",""),
                    "rec_out": base.get("rec_out",""),
                    "locator_timecode": "",
                    "locator_color": "",
                    "locator_text": ""
                })

        df_out = pd.DataFrame(merged_rows)[column_order] if merged_rows else pd.DataFrame(columns=column_order)

    # 📥 Output
    if not df_out.empty:
        view_title = "🔍 Extracted *LOC Entries with Metadata" if export_only_loc else "🧾 All Events (incl. locator rows)"
        st.subheader(view_title)
        st.dataframe(df_out, use_container_width=True)

        original_name = uploaded_file.name.rsplit(".", 1)[0]
        date_suffix = datetime.now().strftime("%y%m%d")
        filename = f"{original_name}_processed_{date_suffix}.csv"

        csv_buffer = io.StringIO()
        df_out.to_csv(csv_buffer, index=False)

        st.download_button(
            label=f"📥 Download CSV: {filename}",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv"
        )
    else:
        if export_only_loc:
            st.warning("No *LOC entries found in the EDL.")
        else:
            st.warning("No events were recognized in the EDL.")
