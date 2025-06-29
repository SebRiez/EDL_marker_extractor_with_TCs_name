import streamlit as st
import pandas as pd
import re
import io
import math

st.set_page_config(page_title="EDL *LOC Extractor", layout="wide")

st.title("🎬 EDL *LOC Extractor with Timecodes")
st.markdown("Lade eine EDL-Datei hoch (Textformat, z. B. `.edl`), um alle `*LOC`-Einträge mit den zugehörigen Timecodes und Clipnamen und Dauer ( in Frames) zu extrahieren.")

# Frame-Rate Auswahl
fps_options = {
    "23.98 fps": 23.976,
    "24 fps": 24,
    "25 fps": 25,
    "29.97 fps": 29.97,
    "30 fps": 30,
    "60 fps": 60
}
selected_fps_label = st.selectbox("🎞️ Frame-Rate für Berechnung der Schnittdauer (cut_range)", list(fps_options.keys()), index=2)
selected_fps = fps_options[selected_fps_label]

# Drop-Frame-Option nur bei NTSC-Raten
is_drop_frame = False
if selected_fps in [29.97, 59.94]:
    is_drop_frame = st.checkbox("🧮 Drop-Frame aktivieren (nur für NTSC 29.97 / 59.94)", value=True)

# Hilfsfunktion zum Umrechnen von Timecode nach Frames
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

# Hilfsfunktion zum Umrechnen von Frames nach Timecode
def frames_to_timecode(frames, fps, drop_frame=False):
    if drop_frame and fps == 29.97:
        drop_frames = math.floor(fps * 0.066666)
        frames_per_hour = round(fps * 60 * 60)
        frames_per_10_minutes = round(fps * 60 * 10)
        frames_per_minute = round(fps * 60)
        d = drop_frames

        frames = int(frames)
        ten_min_chunks = frames // (frames_per_10_minutes - d * 9)
        remaining_frames = frames % (frames_per_10_minutes - d * 9)

        minutes = (ten_min_chunks * 10) + (remaining_frames // (frames_per_minute - d))
        remaining_frames = remaining_frames % (frames_per_minute - d)

        hours = minutes // 60
        minutes = minutes % 60
        seconds = remaining_frames // int(fps)
        frames_left = remaining_frames % int(fps)

        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02};{int(frames_left):02}"
    else:
        total_frames = int(frames)
        hours = total_frames // int(fps * 3600)
        minutes = (total_frames % int(fps * 3600)) // int(fps * 60)
        seconds = (total_frames % int(fps * 60)) // int(fps)
        frames_left = total_frames % int(fps)
        return f"{hours:02}:{minutes:02}:{seconds:02}:{frames_left:02}"

# Datei-Upload
uploaded_file = st.file_uploader("📤 EDL-Datei hochladen", type=["edl", "txt"])

if uploaded_file:
    edl_text = uploaded_file.read().decode("utf-8")
    edl_lines = edl_text.splitlines()

    preview_lines = edl_lines[:50]

    highlighted_lines = []
    for line in preview_lines:
        if "*LOC" in line:
            highlighted_lines.append(f'<div style="background-color:#228B22;color:white;padding:2px;">{line}</div>')
        else:
            highlighted_lines.append(f'<div>{line}</div>')

    highlighted_html = "<br>".join(highlighted_lines)

    st.subheader("📝 Vorschau der Original-EDL (erste 50 Zeilen, *LOC hervorgehoben)")
    st.markdown(highlighted_html, unsafe_allow_html=True)

    if len(edl_lines) > 50:
        st.info(f"Die EDL enthält insgesamt {len(edl_lines)} Zeilen. In der Vorschau werden nur die ersten 50 angezeigt.")

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

            loc_data.append({
                "event_number": current_event_number,
                "clip_name": current_clipname,
                "src_in": current_timecodes["src_in"],
                "src_out": current_timecodes["src_out"],
                "rec_in": current_timecodes["rec_in"],
                "rec_out": current_timecodes["rec_out"],
                "cut_range": cut_range,
                "loc_text": line.strip()
            })

    if loc_data:
        df_loc = pd.DataFrame(loc_data)

        st.subheader("🔍 Extrahierte *LOC-Einträge")
        st.dataframe(df_loc, use_container_width=True)

        csv_buffer = io.StringIO()
        df_loc.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 CSV herunterladen",
            data=csv_buffer.getvalue(),
            file_name="EDL_LOC_entries_with_timecodes.csv",
            mime="text/csv"
        )
    else:
        st.warning("Keine *LOC-Einträge gefunden.")
