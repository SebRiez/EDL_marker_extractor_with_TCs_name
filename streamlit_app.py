import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="EDL *LOC Extractor", layout="wide")

st.title("🎬 EDL *LOC Extractor with Timecodes")
st.markdown("Lade eine EDL-Datei hoch (Textformat, z. B. `.edl`), um alle `*LOC`-Einträge mit den zugehörigen Timecodes und Clipnamen zu extrahieren.")

# Hilfsfunktion zum Umrechnen von Timecode nach Frames
def timecode_to_frames(tc, fps):
    h, m, s, f = map(int, tc.strip().split(":"))
    return round(h * 3600 * fps + m * 60 * fps + s * fps + f)

# Frame-Rate Auswahl
fps_options = {
    "23.98 fps": 23.98,
    "24 fps": 24,
    "25 fps": 25,
    "30 fps": 30,
    "60 fps": 60
}
selected_fps_label = st.selectbox("🎞️ Frame-Rate für Berechnung der Schnittdauer (cut_range)", list(fps_options.keys()), index=2)
selected_fps = fps_options[selected_fps_label]

# Datei-Upload
uploaded_file = st.file_uploader("📤 EDL-Datei hochladen", type=["edl", "txt"])

if uploaded_file:
    # EDL-Inhalt lesen
    edl_text = uploaded_file.read().decode("utf-8")
    edl_lines = edl_text.splitlines()

    # Nur die ersten 50 Zeilen für Vorschau anzeigen
    preview_lines = edl_lines[:50]

    # Hervorhebung für *LOC-Zeilen mit HTML (grüner Hintergrund, weiße Schrift)
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

    # Parsing
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
                frames_in = timecode_to_frames(current_timecodes["src_in"], selected_fps)
                frames_out = timecode_to_frames(current_timecodes["src_out"], selected_fps)
                cut_range = frames_out - frames_in
            except:
                cut_range = None

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

        # CSV-Download
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
