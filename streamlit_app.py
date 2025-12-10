# Script created by Sebastian Riezler, refactored for clarity and maintainability
# c 2025/06, updated 2025/12

import re
import io
import math
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Pattern

# =============================================
# CONSTANTS & CONFIGURATION
# =============================================

# Map of color names to CSS-compatible values (Hex or standard name)
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

# FPS options
FPS_OPTIONS = {
    "23.98 fps": 23.976,
    "24 fps": 24,
    "25 fps": 25,
    "29.97 fps": 29.97,
    "30 fps": 30,
    "59.94 fps": 59.94,
    "60 fps": 60
}

# Pre-compiled regex patterns
EVENT_PATTERN: Pattern = re.compile(r"^\s*(\d{3,6})\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")
CLIP_NAME_PATTERN: Pattern = re.compile(r"\*FROM CLIP NAME:\s+(.*)")
LOC_PATTERN: Pattern = re.compile(r"\*\s*LOC:?\s+(\d{2}:\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)", re.IGNORECASE)
SHOT_ID_PATTERN: Pattern = re.compile(r"([A-Z]{3}_\d{3}_\d{4}|[A-Z]{3}_\d{4}|CS\d{4})")

# =============================================
# UTILITY FUNCTIONS
# =============================================

def timecode_to_frames(tc: str, fps: float, drop_frame: bool = False) -> int:
    """
    Convert timecode string to frame count.
    Args:
        tc: Timecode string (HH:MM:SS:FF)
        fps: Frames per second
        drop_frame: Whether to use drop-frame calculation
    Returns:
        Frame count as integer
    """
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
    except Exception as e:
        st.warning(f"Error parsing timecode '{tc}': {e}")
        return 0

def calculate_duration_frames(
    tc_in: str, tc_out: str, fps: float, drop_frame: bool = False, exclude_last: bool = False
) -> int:
    """
    Calculate duration in frames between two timecodes.
    Args:
        tc_in: In timecode
        tc_out: Out timecode
        fps: Frames per second
        drop_frame: Whether to use drop-frame calculation
        exclude_last: Whether to exclude the last frame
    Returns:
        Duration in frames
    """
    frames_out = timecode_to_frames(tc_out, fps, drop_frame)
    frames_in = timecode_to_frames(tc_in, fps, drop_frame)
    duration = frames_out - frames_in
    if exclude_last:
        duration = max(duration - 1, 0)
    return duration

def extract_shot_id(text: str) -> str:
    """Extract shot ID from text using regex."""
    match = SHOT_ID_PATTERN.search(text)
    return match.group(1) if match else ""

def extract_locator_components(loc_line: str) -> Tuple[str, str, str]:
    """Extract timecode, color, and description from a *LOC line."""
    match = LOC_PATTERN.match(loc_line.strip())
    if match:
        return match.group(1), match.group(2), match.group(3).strip()
    return "", "", ""

# =============================================
# MAIN PARSING LOGIC
# =============================================

def parse_edl(
    edl_lines: List[str],
    selected_fps: float,
    is_drop_frame: bool,
    selected_color: str,
    include_tapename: bool,
    include_clipname: bool,
    export_only_loc: bool,
    exclude_last_frame: bool,
) -> pd.DataFrame:
    """
    Parse EDL lines and extract locator data.
    Args:
        edl_lines: List of EDL lines
        selected_fps: Selected FPS
        is_drop_frame: Whether to use drop-frame
        selected_color: Selected color filter
        include_tapename: Whether to include tapename
        include_clipname: Whether to include clipname
        export_only_loc: Whether to export only *LOC entries
        exclude_last_frame: Whether to exclude last frame in duration
    Returns:
        DataFrame with extracted data
    """
    loc_rows = []
    events_order = []
    events_map: Dict[str, Dict] = {}
    current_event_number = None
    current_timecodes = None
    current_clipname = ""
    current_tape_name = ""

    color_filter_active = selected_color != "All Colors"

    for line in edl_lines:
        event_match = EVENT_PATTERN.match(line)
        if event_match:
            current_event_number = event_match.group(1)
            current_tape_name = event_match.group(2)
            current_timecodes = {
                "src_in": event_match.group(3),
                "src_out": event_match.group(4),
                "rec_in": event_match.group(5),
                "rec_out": event_match.group(6),
            }
            if current_event_number not in events_map:
                events_order.append(current_event_number)
            events_map[current_event_number] = {
                "tape_name": current_tape_name or "",
                "clip_name": current_clipname or "",
                "src_in": current_timecodes["src_in"] if current_timecodes else "",
                "src_out": current_timecodes["src_out"] if current_timecodes else "",
                "rec_in": current_timecodes["rec_in"] if current_timecodes else "",
                "rec_out": current_timecodes["rec_out"] if current_timecodes else "",
            }
            continue

        if line.strip().startswith("*FROM CLIP NAME:"):
            clip_name_match = CLIP_NAME_PATTERN.match(line.strip())
            if clip_name_match:
                current_clipname = clip_name_match.group(1).strip()
                if current_event_number and current_event_number in events_map:
                    events_map[current_event_number]["clip_name"] = current_clipname

        if "*LOC" in line:
            locator_tc, locator_color, loc_description = extract_locator_components(line)
            if color_filter_active and locator_color.lower() != selected_color.lower():
                continue

            shot_id = extract_shot_id(loc_description)
            base_data = events_map.get(current_event_number, {})
            locator_frames = (
                timecode_to_frames(locator_tc, selected_fps, is_drop_frame)
                if current_event_number and base_data.get("rec_in")
                else None
            )
            duration_frames = calculate_duration_frames(
                base_data.get("src_in", ""),
                base_data.get("src_out", ""),
                selected_fps,
                is_drop_frame,
                exclude_last_frame,
            )

            row = {
                "Event": current_event_number or "",
                "Shot ID": shot_id,
                "Src_In": base_data.get("src_in", ""),
                "Src_Out": base_data.get("src_out", ""),
                "Rec_In": base_data.get("rec_in", ""),
                "Rec_Out": base_data.get("rec_out", ""),
                "Frames (Rec)": locator_frames if locator_frames is not None else "",
                "*LOC TC": locator_tc,
                "*LOC Color": locator_color,
                "*LOC Description": loc_description,
                "Duration (Frames)": duration_frames,
            }
            if include_tapename:
                row["Tapename"] = base_data.get("tape_name", "")
            if include_clipname:
                row["Clipname"] = base_data.get("clip_name", "")
            loc_rows.append(row)

        elif not export_only_loc and current_event_number and current_event_number in events_map:
            event_already_present = any(
                row.get("Event") == current_event_number and row.get("*LOC TC") != ""
                for row in loc_rows
            )
            if not event_already_present:
                base_data = events_map.get(current_event_number, {})
                duration_frames = calculate_duration_frames(
                    base_data.get("src_in", ""),
                    base_data.get("src_out", ""),
                    selected_fps,
                    is_drop_frame,
                    exclude_last_frame,
                )
                row = {
                    "Event": current_event_number or "",
                    "Shot ID": extract_shot_id(base_data.get("clip_name", "")),
                    "Src_In": base_data.get("src_in", ""),
                    "Src_Out": base_data.get("src_out", ""),
                    "Rec_In": base_data.get("rec_in", ""),
                    "Rec_Out": base_data.get("rec_out", ""),
                    "Frames (Rec)": "",
                    "*LOC TC": "",
                    "*LOC Color": "",
                    "*LOC Description": "No LOCATOR found",
                    "Duration (Frames)": duration_frames,
                }
                if include_tapename:
                    row["Tapename"] = base_data.get("tape_name", "")
                if include_clipname:
                    row["Clipname"] = base_data.get("clip_name", "")
                loc_rows.append(row)

    if not loc_rows:
        st.warning("⚠️ No `*LOC` entries found in the EDL or they were filtered out by the color selection.")
        return pd.DataFrame()

    df = pd.DataFrame(loc_rows)
    desired_columns = ["Event", "Shot ID"]
    if include_tapename:
        desired_columns.append("Tapename")
    if include_clipname:
        desired_columns.append("Clipname")
    desired_columns.extend([
        "Src_In", "Src_Out", "Duration (Frames)",
        "Rec_In", "Rec_Out", "*LOC TC", "*LOC Color", "*LOC Description"
    ])
    return df.reindex(columns=[col for col in desired_columns if col in df.columns])

# =============================================
# STREAMLIT UI
# =============================================

def main():
    st.set_page_config(
        page_title="EDL Locator Extractor",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # CSS – Emerald Green Palette
    st.markdown("""
    <style>
        /* COLOR PALETTE (Emerald Green):
         * Deep Dark Grey (Background): #1E2025
         * Mid Dark Grey (Container): #2D2F34
         * Emerald Green (Accent, Interaction): #42B38F
         * Light Green (Highlight): #80ED99
         * Off-White (Text): #F0F0F0
         */
        /* Main background */
        .stApp {
            background-color: #1E2025;
            color: #F0F0F0;
        }
        /* Limit maximum width of main content - 900px */
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

        /* Preview cards (not directly used, but maintained for consistency) */
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

        /* Buttons - Primary (Emerald Green Accent) */
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

        /* Download buttons (Secondary Accent) */
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

        /* File uploader (Dark background with light border) */
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

        /* Images: Scaling and centering */
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
            /* Active tab as light accent */
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

        /* ADDED FOR CODE 2: Customized styling for small boxes/inputs */
        .small-box .stSelectbox, .small-box .stNumberInput, .small-box .stCheckbox {
            width: fit-content !important;
            min-width: 160px;
        }

        /* Background color for *LOC line highlights adjusted */
        .loc-highlight {
            background-color: rgba(66, 179, 143, 0.3) !important; /* Emerald Green Accent */
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

    # Header
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

    # Settings
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Settings")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        selected_fps_label = st.selectbox("🎞️ **FPS**", list(FPS_OPTIONS.keys()), index=2)
        selected_fps = FPS_OPTIONS[selected_fps_label]
    with col2:
        preview_limit = st.number_input("🔢 **Preview Lines**", min_value=50, value=50, step=10, format="%d")
    with col3:
        selected_color = st.selectbox(
            "🎨 **Filter Locator Color**",
            FILTER_COLOR_OPTIONS,
            index=0,
            help="Select a color to export only locators of that color."
        )

    is_drop_frame = False
    if selected_fps in [29.97, 59.94]:
        is_drop_frame = st.checkbox("🧮 **Drop-Frame**", value=True)

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
        exclude_last_frame = st.checkbox(
            "➖ **Duration: Exclude last frame**",
            value=True,
            help="Depending on the use case, users may define the required duration differently. The feature 'Duration: Exclude last frame' allows you to choose whether the duration should include the End Frame (Out) or not. By default, this option is enabled to subtract the End Frame (Length = Out - In - 1), as this is the most common method for calculating clip length in many systems."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # File upload
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("📤 **Upload your EDL file**", type=["edl", "txt"])
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        edl_text = uploaded_file.read().decode("utf-8", errors="ignore")
        edl_lines = edl_text.splitlines()
        preview_lines = edl_lines[:int(preview_limit)]
        highlighted_lines = []
        for line in preview_lines:
            if re.search(r"\*\s*LOC", line):
                highlighted_lines.append(f'<div class="loc-highlight">{line}</div>')
            else:
                highlighted_lines.append(f'<div class="edl-line">{line}</div>')

        st.markdown("### 📝 EDL Preview")
        st.markdown(f"*(First {int(preview_limit)} lines, **`*LOC`** highlighted)*")
        st.markdown("---")
        st.markdown(f'<div style="max-height: 400px; overflow-y: scroll; background-color: #1E2025; padding: 1rem; border-radius: 0.5rem;">{"".join(highlighted_lines)}</div>', unsafe_allow_html=True)
        if len(edl_lines) > preview_limit:
            st.info(f"The EDL contains **{len(edl_lines)}** total lines. Only the first **{int(preview_limit)}** are shown above.")

        # Process and display
        with st.spinner("Processing EDL..."):
            df = parse_edl(
                edl_lines, selected_fps, is_drop_frame, selected_color,
                include_tapename, include_clipname, export_only_loc, exclude_last_frame
            )

        if not df.empty:
            st.markdown("### ✨ Processed Locator Data")
            st.dataframe(df, use_container_width=True)

            st.markdown("---")
            st.markdown("### ⬇️ Download Data")
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
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
