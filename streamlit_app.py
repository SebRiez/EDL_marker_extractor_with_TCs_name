# Script created by Sebastian Riezler with ChatGpt
# c 2025/06

import streamlit as st
import pandas as pd
import re
import io
import math
from datetime import datetime

# ---------------------------------------------------------
# FARBDEFINITIONEN (Unverändert)
# ---------------------------------------------------------
# Mappe von Farbnamen zu CSS-kompatiblen Werten (Hex oder Standardname)
COLOR_HEX_MAP = {
    'Blue': '#0074D9', 'Cyan': '#00B8D4', 'Green': '#2ECC40', 
    'Yellow': '#FFDC00', 'Red': '#FF4136', 'Orange': '#FF851B', 
    'Magenta': '#FF4136', 'Purple': '#B10DC9', 'Fuchsia': '#F012BE', 
    'Rose': '#F5B0C4', 'Sky': '#87CEEB', 'Mint': '#98FB98', 
    'Lemon': '#FFFACD', 'Sand': '#F4A460', 'Cocoa': '#6F4E37', 
    'White': '#FFFFFF', 'Black': '#000000', 
    'Denim': '#1560BD'
}
# Aktualisierte Liste der standardisierten Markerfarben (basiert auf der Map)
COLOR_OPTIONS = list(COLOR_HEX_MAP.keys())
# Farbauswahl für den Filter (Alle Farben + die definierten Optionen)
FILTER_COLOR_OPTIONS = ["All Colors"] + COLOR_OPTIONS


# ---------------------------------------------------------
# Page Configuration (Unverändert)
# ---------------------------------------------------------
st.set_page_config(
    page_title="EDL Locator Extractor",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# CSS – Emerald Green Palette (Unverändert)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* FARBPALETTE (Emerald Green):
     * Deep Dark Grey (Hintergrund): #1E2025 
     * Mid Dark Grey (Container): #2D2F34
     * Emerald Green (Akzent, Interaktion): #42B38F
     * Light Green (Highlight): #80ED99
     * Off-White (Text): #F0F0F0
     */

    /* Main background */
    .stApp { 
        background-color: #1E2025;
        color: #F0F0F0;
    }

    /* Begrenzung der maximalen Breite des Hauptinhalt - 900px */
    .main {
        max-width: 900px; 
        padding: 0 3rem; 
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Header styling (Gradient in Emerald Green) */
    .main-header {
        background: linear-gradient(135deg, #42B38F 0%, #80ED99 100%);
        padding: 2.5rem;
        border-radius: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(66, 179, 143, 0.3);
        text-align: center;
    }
    
    .main-header h1 {
        color: #1E2025; 
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: rgba(30, 32, 37, 0.9);
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 500;
    }
    
    /* Container styling (Mid Dark Grey) */
    .glass-container {
        background: #2D2F34;
        border-radius: 1.5rem;
        border: 1px solid rgba(240, 240, 240, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        padding: 2rem;
        margin-bottom: 1.5rem;
    }
    
    /* Preview cards (nicht direkt verwendet, aber für Konsistenz beibehalten) */
    .preview-card {
        background: #2D2F34;
        border: 1px solid rgba(66, 179, 143, 0.2);
        border-radius: 1rem;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .preview-card:empty {
        display: none !important;
    }

    .preview-card:hover {
        border-color: rgba(66, 179, 143, 0.5);
        box-shadow: 0 8px 24px rgba(66, 179, 143, 0.2);
        transform: translateY(-2px);
    }
    
    /* Section headers */
    h2, h3 {
        color: #80ED99 !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    
    /* Input fields */
    div.stTextInput input, div.stNumberInput input, div[data-baseweb="select"] {
        background: #1E2025 !important; 
        border: 1px solid rgba(128, 237, 153, 0.3) !important; 
        border-radius: 0.5rem !important;
        color: #F0F0F0 !important;
        transition: all 0.3s ease !important;
    }
    
    div.stTextInput input:focus, div.stNumberInput input:focus, div[data-baseweb="select"]:focus-within {
        border-color: #42B38F !important; 
        box-shadow: 0 0 0 3px rgba(66, 179, 143, 0.3) !important;
    }
    
    /* Buttons - Primary (Emerald Green Akzent) */
    .stButton button {
        background: #42B38F !important;
        color: #1E2025 !important;
        border-radius: 0.75rem !important;
        transition: all 0.3s ease !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        box-shadow: 0 4px 12px rgba(66, 179, 143, 0.3) !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        background: #80ED99 !important;
        box-shadow: 0 8px 24px rgba(66, 179, 143, 0.5) !important;
    }
    
    /* Download buttons (Sekundärer Akzent) */
    .stDownloadButton button {
        background: rgba(128, 237, 153, 0.15) !important; 
        color: #80ED99 !important; 
        border: 1px solid rgba(128, 237, 153, 0.3) !important;
        border-radius: 0.75rem !important;
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
    }
    
    .stDownloadButton button:hover {
        background: rgba(128, 237, 153, 0.25) !important;
        border-color: #42B38F !important; 
        transform: translateY(-2px) !important;
    }
    
    /* File uploader (Dunkler Hintergrund mit hellem Rand) */
    div[data-testid="stFileUploader"] {
        background: #2D2F34;
        border: 2px dashed rgba(128, 237, 153, 0.5); 
        border-radius: 1rem;
        padding: 2rem;
        transition: all 0.3s ease;
    }
    
    div[data-testid="stFileUploader"]:hover {
        border-color: #42B38F;
        background: rgba(66, 179, 143, 0.1);
    }
    
    /* Bilder: Skalierung und Zentrierung */
    div[data-testid="stImage"] img {
        border-radius: 1rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(240, 240, 240, 0.1);
        max-width: 50%; 
        height: auto;
        display: block; 
        margin-left: auto; 
        margin-right: auto; 
    }
    
    /* Dataframes */
    .dataframe {
        background: #2D2F34 !important;
        border-radius: 0.75rem !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: #2D2F34;
        padding: 0.5rem;
        border-radius: 0.75rem;
    }
    
    .stTabs [aria-selected="true"] {
        /* Aktiver Tab als heller Akzent */
        background: linear-gradient(135deg, #42B38F 0%, #80ED99 100%);
        color: #1E2025 !important; 
    }
    
    /* Info/Success/Error */
    .stAlert {
        border-left: 4px solid #42B38F;
        color: #80ED99;
    }
    div[data-testid="stSuccess"] {
        border-left: 4px solid #4CAF50 !important;
        color: #4CAF50 !important;
    }
    div[data-testid="stError"] {
        border-left: 4px solid #F44336 !important;
        color: #F44336 !important;
    }
    
    /* Divider */
    hr {
        border-color: rgba(240, 240, 240, 0.1) !important;
        margin: 2rem 0 !important;
    }
    
    /* ZUGEFÜGT FÜR CODE 2: Angepasstes Styling für kleine Boxen/Inputs */
    .small-box .stSelectbox, .small-box .stNumberInput, .small-box .stCheckbox {
        width: fit-content !important;
        min-width: 160px;
    }
    
    /* Hintergrundfarbe für die *LOC Zeilen-Highlights anpassen */
    .loc-highlight {
        background-color: rgba(66, 179, 143, 0.3) !important; /* Emerald Green Akzent */
        color: #F0F0F0 !important;
        padding: 2px;
        border-radius: 0.25rem;
        margin-bottom: 2px;
    }
    .edl-line {
        color: #F0F0F0;
        padding: 2px;
        margin-bottom: 2px;
    }

</style>
""", unsafe_allow_html=True)

# 🎬 Title box 
st.markdown("""
<div class="main-header">
    <h1>🎬 EDL Locator Extractor</h1>
    <p>Extract locator data and timecodes from Edit Decision Lists (EDLs)</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Upload an EDL file (optimized for File32 EDL) to extract all `*LOC` entries along with their timecodes and metadata. 
If your EDL contains `Tapename` and `Clipname`, you can check below whether they should be inserted into the CSV.
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

st.markdown('<div class="glass-container">', unsafe_allow_html=True) # Neuer Container
st.markdown("### ⚙️ Settings")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    with st.container():
        st.markdown('<div class="small-box">', unsafe_allow_html=True)
        selected_fps_label = st.selectbox("🎞️ **FPS**", list(fps_options.keys()), index=2)
        st.markdown("</div>", unsafe_allow_html=True)
        selected_fps = fps_options[selected_fps_label]

with col2:
    with st.container():
        st.markdown('<div class="small-box">', unsafe_allow_html=True)
        preview_limit = st.number_input("🔢 **Preview Lines**", min_value=50, value=50, step=10, format="%d")
        st.markdown("</div>", unsafe_allow_html=True)

with col3:
    with st.container():
        st.markdown('<div class="small-box">', unsafe_allow_html=True)
        selected_color = st.selectbox(
            "🎨 **Filter Locator Color**", 
            FILTER_COLOR_OPTIONS, 
            index=0, 
            help="Select a color to export only locators of that color."
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Drop-Frame Option
    is_drop_frame = False
    if selected_fps in [29.97, 59.94]:
        with st.container():
            st.markdown('<div class="small-box">', unsafe_allow_html=True)
            is_drop_frame = st.checkbox("🧮 **Drop-Frame**", value=True)
            st.markdown("</div>", unsafe_allow_html=True)


# 🆕 Checkboxes for display options (inline)
st.markdown("---")
col_cb1, col_cb2, col_cb3, col_cb4 = st.columns(4)

with col_cb1:
    include_tapename = st.checkbox("📼 **Include Tapename**", value=True, help="Include Tapename column in the exported CSV.")

with col_cb2:
    include_clipname = st.checkbox("🎬 **Include Clipname**", value=True, help="Include Clipname column in the exported CSV.")

with col_cb3:
    export_only_loc = st.checkbox("📝 **Export only *LOC entries**", value=True,
                                  help="Turn off to export ALL events. Events without *LOC will have empty locator fields; events with multiple LOCs will be duplicated per locator.")

with col_cb4:
    # NEUE OPTION FÜR DIE DAUERBERECHNUNG
    exclude_last_frame = st.checkbox(
        "➖ **Dauer: Letztes Frame abziehen**", 
        value=True, 
        help="Aktiviert: Dauer = (SRC OUT - SRC IN) - 1 Frame (z.B. 00:01:00 - 00:00:01 = 24 Frames; mit Abzug: 23 Frames). Deaktiviert: Standard EDL Dauer (Out ist exklusiv)."
    )
    
st.markdown('</div>', unsafe_allow_html=True) # Ende des Settings-Containers

# 🕒 Timecode tools 
def timecode_to_frames(tc, fps, drop_frame=False):
    # Hilfsfunktion, um Timecode in Frames umzuwandeln
    try:
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
    except Exception:
        return 0 

def calculate_duration_frames(tc_in, tc_out, fps, drop_frame=False, exclude_last=False):
    # Berechnet die Dauer in Frames (Out - In)
    frames_out = timecode_to_frames(tc_out, fps, drop_frame)
    frames_in = timecode_to_frames(tc_in, fps, drop_frame)
    
    # Standard-EDL-Dauer (Out ist exklusiv: Frames(OUT) - Frames(IN))
    duration = frames_out - frames_in
    
    # Logik für den optionalen Abzug des letzten Frames
    if exclude_last:
        duration = duration - 1
    
    # Sicherstellen, dass die Dauer nicht negativ ist
    return duration if duration >= 0 else 0

def extract_shot_id(text):
    # Searches for 3 uppercase letters followed by underscore and digits (e.g., ABC_123_4567, XYZ_9999) or CSxxxx
    match = re.search(r"([A-Z]{3}_\d{3}_\d{4}|[A-Z]{3}_\d{4}|CS\d{4})", text)
    return match.group(1) if match else ""

def extract_locator_components(loc_line):
    # Extracts TC, color (color is the second word after *LOC:), and text
    match = re.match(r"\*\s*LOC:?\s+(\d{2}:\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)", loc_line.strip(), re.IGNORECASE)
    if match:
        return match.group(1), match.group(2), match.group(3).strip()
    else:
        return "", "", ""

# 📤 File upload
st.markdown('<div class="glass-container">', unsafe_allow_html=True) # Neuer Container
uploaded_file = st.file_uploader("📤 **Upload your EDL file**", type=["edl", "txt"])
st.markdown('</div>', unsafe_allow_html=True) # Ende des Upload-Containers

if uploaded_file:
    st.markdown('<div class="glass-container">', unsafe_allow_html=True) # Neuer Container für Processing
    edl_text = uploaded_file.read().decode("utf-8", errors="ignore")
    edl_lines = edl_text.splitlines()
    preview_lines = edl_lines[:int(preview_limit)]

    highlighted_lines = []
    for line in preview_lines:
        if re.search(r"\*\s*LOC", line):
            highlighted_lines.append(f'<div class="loc-highlight">{line}</div>')
        else:
            highlighted_lines.append(f'<div class="edl-line">{line}</div>')
    
    st.markdown("### 📝 Preview of EDL")
    st.markdown(f"*(First {int(preview_limit)} lines, **`*LOC`** highlighted)*")
    st.markdown("---")
    
    st.markdown(f'<div style="max-height: 400px; overflow-y: scroll; background-color: #1E2025; padding: 1rem; border-radius: 0.5rem;">{"".join(highlighted_lines)}</div>', unsafe_allow_html=True)


    if len(edl_lines) > preview_limit:
        st.info(f"The EDL contains **{len(edl_lines)}** total lines. Only the first **{int(preview_limit)}** are shown above.")

    # 🔍 Main parsing
    loc_rows = []                       
    events_order = []                   
    events_map = {}                     
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
                if current_event_number and current_event_number in events_map:
                    events_map[current_event_number]["clip_name"] = current_clipname

        if re.search(r"\*\s*LOC", line):
            locator_tc, locator_color, loc_description = extract_locator_components(line)
            shot_id = extract_shot_id(loc_description)

            # Filter Color
            color_filter_active = selected_color != "All Colors"
            if color_filter_active and locator_color.lower() != selected_color.lower():
                 continue 
            
            # Daten für Locator Frames (Rec) erfassen
            base_data = events_map.get(current_event_number, {})
            if current_event_number and base_data.get("rec_in"):
                locator_frames = timecode_to_frames(locator_tc, selected_fps, is_drop_frame)
            else:
                locator_frames = None

            # Dauer in Frames berechnen (unter Berücksichtigung der neuen Option)
            src_in = base_data.get("src_in", "")
            src_out = base_data.get("src_out", "")
            duration_frames = calculate_duration_frames(
                src_in, 
                src_out, 
                selected_fps, 
                is_drop_frame, 
                exclude_last_frame # NEUE VARIABLE
            )
            
            row = {
                "Event": current_event_number or "",
                "Shot ID": shot_id,
                "Src_In": src_in,
                "Src_Out": src_out,
                "Rec_In": base_data.get("rec_in", ""),
                "Rec_Out": base_data.get("rec_out", ""),
                "Frames (Rec)": locator_frames if locator_frames is not None else "", # Daten bleiben intern
                "*LOC TC": locator_tc,
                "*LOC Color": locator_color,
                "*LOC Description": loc_description,
                "Dauer (Frames)": duration_frames,
            }
            
            # Conditional inclusion based on checkboxes
            if include_tapename:
                row["Tapename"] = base_data.get("tape_name", "")
            if include_clipname:
                row["Clipname"] = base_data.get("clip_name", "")

            loc_rows.append(row)
        
        # Logic for export_only_loc = False (Export all events)
        elif not export_only_loc and current_event_number and current_event_number in events_map:
            
            # Prüfen, ob das Event bereits einen LOC-Eintrag hat, um keine Duplikate zu erstellen
            event_already_present = any(row.get("Event") == current_event_number and row.get("*LOC TC") != "" for row in loc_rows)
            
            if not event_already_present:
                base_data = events_map.get(current_event_number, {})
                
                # Dauer in Frames berechnen (unter Berücksichtigung der neuen Option)
                src_in = base_data.get("src_in", "")
                src_out = base_data.get("src_out", "")
                duration_frames = calculate_duration_frames(
                    src_in, 
                    src_out, 
                    selected_fps, 
                    is_drop_frame,
                    exclude_last_frame # NEUE VARIABLE
                )
                
                row = {
                    "Event": current_event_number or "",
                    "Shot ID": extract_shot_id(base_data.get("clip_name", "")),
                    "Src_In": src_in,
                    "Src_Out": src_out,
                    "Rec_In": base_data.get("rec_in", ""),
                    "Rec_Out": base_data.get("rec_out", ""),
                    "Frames (Rec)": "",
                    "*LOC TC": "",
                    "*LOC Color": "",
                    "*LOC Description": "No LOCATOR found",
                    "Dauer (Frames)": duration_frames,
                }
                
                # Conditional inclusion based on checkboxes
                if include_tapename:
                    row["Tapename"] = base_data.get("tape_name", "")
                if include_clipname:
                    row["Clipname"] = base_data.get("clip_name", "")
                        
                loc_rows.append(row)
                
    # 📊 Display Results
    if loc_rows:
        df = pd.DataFrame(loc_rows)
        
        # Final Column Order: Event, Shot ID, Tapenam, Clipname, Src IN, Src OUT, Dauer (Frames), Rec IN, Rec OUT, LOC TC, Loc Color, Loc Text
        desired_columns = ["Event", "Shot ID"]
        
        # Bedingte Spalten einfügen
        if include_tapename:
            desired_columns.append("Tapename")
        if include_clipname:
            desired_columns.append("Clipname")
            
        # Feste Spaltenreihenfolge
        desired_columns.extend([
            "Src_In", 
            "Src_Out", 
            "Dauer (Frames)", 
            "Rec_In", 
            "Rec_Out", 
            "*LOC TC", 
            "*LOC Color", 
            "*LOC Description"
        ])
        
        # Nur die gewünschten Spalten in der richtigen Reihenfolge auswählen
        df = df.reindex(columns=[col for col in desired_columns if col in df.columns])

        st.markdown("### ✨ Processed Locator Data")
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### ⬇️ Download Data")

        # Prepare for download
        csv = df.to_csv(index=False)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"EDL_Locators_{timestamp}.csv"
        
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=file_name,
            mime="text/csv",
            use_container_width=True
        )
        st.success("✅ Processing complete! Download your CSV above.")
    else:
        st.warning("⚠️ No `*LOC` entries found in the EDL or they were filtered out by the color selection.")

    st.markdown('</div>', unsafe_allow_html=True)
