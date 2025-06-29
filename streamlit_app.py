import streamlit as st
import pandas as pd
import re
import io
import math

st.set_page_config(page_title="EDL locator extractor", layout="wide")

st.title("🎬 EDL locator extractor with Timecodes")
st.markdown("Upload an EDL file (text format, e.g., `.edl`) to extract all `*LOC` entries along with their corresponding timecodes and clip names and durations in frames.")

fps_options = {
    "23.98 fps": 23.976,
    "24 fps": 24,
    "25 fps": 25,
    "29.97 fps": 29.97,
    "30 fps": 30,
    "59.94 fps": 59.94,
    "60 fps": 60
}
selected_fps_label = st.selectbox("🎞️ Frame rate for calculating cut range", list(fps_options.keys()), index=2)
selected_fps = fps_options[selected_fps_label]

is_drop_frame = False
if selected_fps in [29.97, 59.94]:
    is_drop_frame = st.checkbox("🧮 Enable Drop-Frame (only for NTSC 29.97 / 59.94)", value=True)

# Preview line limit
preview_limit = st.number_input("🔢 Number of preview lines (minimum 50)", min_value=50, value=50, step=10)

def timecode_to_frames(tc, fps, drop_frame=False):
    h, m, s, f = map(int, tc.strip().split(":"))
    if drop_frame and fps == 29.97:
        drop_frames = math.floor(fps * 0.066666)
        total_minutes = h * 60 + m
        frames = (
            (fps * 60 * 60 * h) +
            (fps * 60 * m) +
            (fps * s) +
            f -
            (drop_frames * (total_minutes - total_minutes // 10))
        )
        return round(frames)
    else:
        return round(h * 3600 * fps + m * 60 * fps + s * fps + f)

def extract_shot_id(loc_line):
    match = re.search(r"(MUM_\d{3}_\d{4})", loc_line)
    return match.group(1) if match else ""

uploaded_file = st.file_uploader("📤 Upload your EDL file", type=["edl", "txt"])

if uploaded_file:
    edl_text = uploaded_file.read().decode("utf-8")
    edl_lines = edl_text.splitlines()
    preview_lines = edl_lines[:int(preview_limit)]

    highlighted_lines = []
    for line in preview_lines:
        if "*LOC" in line:
            highlighted_lines.append(f'<div style="background-color:#228B22;color:white;padding:2px;">{line}</div>')
        else:
            highlighted_lines.append(f'<div>{line}</div>')

    highlighted_html = "<br>".join(highlighted_lines)
    st.subheader(f"📝 Preview of EDL (first {int(preview_limit)} lines, *LOC highlighted)")
    st.markdown(highlighted_html, unsafe_allow_html=True)

    if len(edl_lines) > preview_limit:
        st.info(f"The EDL contains {len(edl_lines)} total lines. Only the first {int(preview_limit)} are shown above.")

    loc_data = []
    current_event_number = None
    current_timecodes = None
    current_clipname = None

    event_pattern = re.compile(r"^\s*(\d{6})\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")

    for line in edl_lines:
        event_match = event_pattern.match(line)
        if event_match:
            current_event_number = event_match.group(1)
            current_clipname = event_match.group(2)
            current_timecodes = {
                "src_in": event_match.group(3),
                "src_out": event_match.group(4),
                "rec_in": event_match.group(5),
                "rec_out": event_match.group(6),
            }
            continue

        if "*LOC" in line and current_event_number:
            try:
                frames_in = timecode_to_frames(current_timecodes["src_in"], selected_fps, is_drop_frame)
                frames_out = timecode_to_frames(current_timecodes["src_out"], selected_fps, is_drop_frame)
                cut_range = frames_out - frames_in
            except:
                frames_in, frames_out, cut_range = None, None, None

            shot_id = extract_shot_id(line)

            loc_data.append({
                "event_number": current_event_number,
                "clip_name": current_clipname,
                "shot_id": shot_id,
                "src_in": current_timecodes["src_in"],
                "src_out": current_timecodes["src_out"],
                "rec_in": current_timecodes["rec_in"],
                "rec_out": current_timecodes["rec_out"],
                "cut_range": cut_range,
                "loc_text": line.strip()
            })

    if loc_data:
        df_loc = pd.DataFrame(loc_data)
        st.subheader("🔍 Extracted *LOC Entries with Shot ID")
        st.dataframe(df_loc, use_container_width=True)

        csv_buffer = io.StringIO()
        df_loc.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_buffer.getvalue(),
            file_name="EDL_LOC_entries_with_timecodes.csv",
            mime="text/csv"
        )
    else:
        st.warning("No *LOC entries found in the EDL.")
