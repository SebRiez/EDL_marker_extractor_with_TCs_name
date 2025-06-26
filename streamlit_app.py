import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="EDL *LOC Extractor", layout="wide")

st.title("🎬 EDL *LOC Extractor with Timecodes")
st.markdown("Lade eine EDL-Datei hoch (Textformat, z. B. `.edl`), um alle `*LOC`-Einträge mit den zugehörigen Timecodes und Clipnamen zu extrahieren.")

# Datei-Upload
uploaded_file = st.file_uploader("📤 EDL-Datei hochladen", type=["edl", "txt"])

if uploaded_file:
    # EDL-Inhalt lesen
    edl_text = uploaded_file.read().decode("utf-8")
    edl_lines = edl_text.splitlines()

    # Hervorhebung für *LOC-Zeilen mit HTML (grüner Hintergrund, weiße Schrift)
    highlighted_lines = []
    for line in edl_lines:
        if "*LOC" in line:
            highlighted_lines.append(f'<div style="background-color:#228B22;color:white;padding:2px;">{line}</div>')
        else:
            highlighted_lines.append(f'<div>{line}</div>')

    highlighted_html = "<br>".join(highlighted_lines)

    st.subheader("📝 Vorschau der Original-EDL (mit *LOC Hervorhebung)")
    st.markdown(highlighted_html, unsafe_allow_html=True)

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
            loc_data.append({
                "event_number": current_event_number,
                "clip_name": current_clipname,
                "src_in": current_timecodes["src_in"],
                "src_out": current_timecodes["src_out"],
                "rec_in": current_timecodes["rec_in"],
                "rec_out": current_timecodes["rec_out"],
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
