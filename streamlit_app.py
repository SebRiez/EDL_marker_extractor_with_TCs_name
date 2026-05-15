# EDL Locator Extractor
# Original by Sebastian Riezler — refactored for correctness and maintainability

import re
import math
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# =============================================
# CONSTANTS & CONFIGURATION
# =============================================

COLOR_HEX_MAP: Dict[str, str] = {
    "Blue":    "#0074D9",
    "Cyan":    "#00B8D4",
    "Green":   "#2ECC40",
    "Yellow":  "#FFDC00",
    "Red":     "#FF4136",
    "Orange":  "#FF851B",
    "Magenta": "#F012BE",   # fixed: was a duplicate of Red (#FF4136)
    "Purple":  "#B10DC9",
    "Fuchsia": "#F012BE",
    "Rose":    "#F5B0C4",
    "Sky":     "#87CEEB",
    "Mint":    "#98FB98",
    "Lemon":   "#FFFACD",
    "Sand":    "#F4A460",
    "Cocoa":   "#6F4E37",
    "White":   "#FFFFFF",
    "Black":   "#000000",
    "Denim":   "#1560BD",
}

COLOR_OPTIONS = list(COLOR_HEX_MAP.keys())
FILTER_COLOR_OPTIONS = ["All Colors"] + COLOR_OPTIONS

FPS_OPTIONS: Dict[str, float] = {
    "23.98 fps": 23.976,
    "24 fps":    24.0,
    "25 fps":    25.0,
    "29.97 fps": 29.97,
    "30 fps":    30.0,
    "59.94 fps": 59.94,
    "60 fps":    60.0,
}
DROP_FRAME_RATES = {29.97, 59.94}

_TC = r"\d{2}:\d{2}:\d{2}:\d{2}"
EVENT_PATTERN: re.Pattern = re.compile(
    # Uses .*? (lazy) to consume track type / cut type between tape name and timecodes.
    # This handles both short tape names ("V") and long Avid-style names
    # ("Drone_-_23334-CONS0") without needing a fixed skip count.
    # Captures: event_num, tape_name, src_in, src_out, rec_in, rec_out
    rf"^\s*(\d{{3,6}})\s+(\S+)\s+.*?({_TC})\s+({_TC})\s+({_TC})\s+({_TC})\s*$"
)
# Handle "* FROM CLIP NAME:" (space after *) as exported by some Avid versions
CLIP_NAME_PATTERN: re.Pattern = re.compile(r"\*\s*FROM CLIP NAME:\s+(.*)")
LOC_PATTERN: re.Pattern = re.compile(
    r"\*\s*LOC:?\s+(\d{2}:\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)", re.IGNORECASE
)
SHOT_ID_PATTERN: re.Pattern = re.compile(
    r"([A-Z]{3}_\d{3}_\d{4}|[A-Z]{3}_\d{4}|CS\d{4})"
)


# =============================================
# TIMECODE UTILITIES
# =============================================

def timecode_to_frames(tc: str, fps: float, drop_frame: bool = False) -> int:
    """Convert a SMPTE timecode string to an absolute frame count."""
    try:
        h, m, s, f = map(int, tc.strip().split(":"))
    except ValueError:
        st.warning(f"Invalid timecode format: '{tc}' — treated as 0.")
        return 0

    if drop_frame and fps in DROP_FRAME_RATES:
        drop_per_min = 2 * round(fps / 30)
        total_minutes = h * 60 + m
        nominal_fps = round(fps)
        frames = (
            nominal_fps * 3600 * h
            + nominal_fps * 60 * m
            + nominal_fps * s
            + f
            - drop_per_min * (total_minutes - total_minutes // 10)
        )
        return int(frames)

    return round(h * 3600 * fps + m * 60 * fps + s * fps + f)


def frames_to_timecode(frames: int, fps: float) -> str:
    """Convert an absolute frame count back to a SMPTE timecode string."""
    frames = max(frames, 0)
    nominal_fps = round(fps)
    total_seconds, f = divmod(frames, nominal_fps)
    total_minutes, s = divmod(total_seconds, 60)
    h, m = divmod(total_minutes, 60)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def calculate_duration_frames(
    tc_in: str, tc_out: str, fps: float,
    drop_frame: bool = False, exclude_last: bool = False
) -> int:
    dur = timecode_to_frames(tc_out, fps, drop_frame) - timecode_to_frames(tc_in, fps, drop_frame)
    return max(dur - 1, 0) if exclude_last else max(dur, 0)


# =============================================
# PARSING HELPERS
# =============================================

def extract_shot_id(text: str) -> str:
    match = SHOT_ID_PATTERN.search(text)
    return match.group(1) if match else ""


def extract_locator_components(loc_line: str) -> Tuple[str, str, str]:
    """Return (timecode, color, description) from a LOC line, or empty strings."""
    match = LOC_PATTERN.match(loc_line.strip())
    if not match:
        return "", "", ""
    return match.group(1), match.group(2), match.group(3).strip()


def _loc_in_line(line: str) -> bool:
    """
    Robust LOC check — handles both '*LOC:' and '* LOC:' (Avid uses a space).
    """
    upper = line.upper()
    return "*LOC:" in upper or "* LOC:" in upper


# =============================================
# MAIN PARSING LOGIC
# =============================================

def parse_edl(
    edl_lines: List[str],
    selected_fps: float,
    is_drop_frame: bool,
    selected_color: str,
    inc_tape: bool,
    inc_clip: bool,
    only_loc: bool,
    excl_last: bool,
) -> pd.DataFrame:

    events_map: Dict[str, Dict] = {}
    current_event: Optional[str] = None
    color_filter = selected_color != "All Colors"

    # ── Pass 1: collect all edit events and their metadata ───────
    for line in edl_lines:
        ev_match = EVENT_PATTERN.match(line)
        if ev_match:
            current_event = ev_match.group(1)
            events_map[current_event] = {
                "tape":    ev_match.group(2),
                "src_in":  ev_match.group(3),
                "src_out": ev_match.group(4),
                "rec_in":  ev_match.group(5),
                "rec_out": ev_match.group(6),
                "clip":    "",
                "loc":     [],   # list of (tc, color, desc) tuples
            }
            continue

        stripped = line.strip()

        if stripped.upper().startswith("*") and "FROM CLIP NAME:" in stripped.upper():
            name_match = CLIP_NAME_PATTERN.match(stripped)
            if name_match and current_event in events_map:
                events_map[current_event]["clip"] = name_match.group(1).strip()
            continue

        if _loc_in_line(line) and current_event in events_map:
            l_tc, l_col, l_desc = extract_locator_components(line)
            if l_tc:
                events_map[current_event]["loc"].append((l_tc, l_col, l_desc))

    if not events_map:
        return pd.DataFrame()

    # ── Pass 2: build rows ───────────────────────────────────────
    rows: List[Dict] = []

    for ev_num, ev in events_map.items():
        dur_frames = calculate_duration_frames(
            ev["src_in"], ev["src_out"], selected_fps, is_drop_frame, excl_last
        )
        base_row: Dict = {
            "Event":             ev_num,
            "Src_In":            ev["src_in"],
            "Src_Out":           ev["src_out"],
            "Duration (Frames)": dur_frames,
            "Duration (TC)":     frames_to_timecode(dur_frames, selected_fps),
            "Rec_In":            ev["rec_in"],
            "Rec_Out":           ev["rec_out"],
        }
        if inc_tape: base_row["Tapename"] = ev["tape"]
        if inc_clip: base_row["Clipname"] = ev["clip"]

        loc_entries = ev["loc"]

        if only_loc:
            # Emit one row per matching LOC marker; skip events without any
            for l_tc, l_col, l_desc in loc_entries:
                if color_filter and l_col.lower() != selected_color.lower():
                    continue
                rows.append({**base_row,
                              "Shot ID":          extract_shot_id(l_desc),
                              "*LOC TC":          l_tc,
                              "*LOC Color":       l_col,
                              "*LOC Description": l_desc})
        else:
            # Emit every event; fill LOC columns from first matching marker if present
            loc_tc = loc_col = loc_desc = ""
            for l_tc, l_col, l_desc in loc_entries:
                if color_filter and l_col.lower() != selected_color.lower():
                    continue
                loc_tc, loc_col, loc_desc = l_tc, l_col, l_desc
                break
            rows.append({**base_row,
                          "Shot ID":          extract_shot_id(loc_desc),
                          "*LOC TC":          loc_tc,
                          "*LOC Color":       loc_col,
                          "*LOC Description": loc_desc})

    if not rows:
        return pd.DataFrame()

    # ── Column ordering ──────────────────────────────────────────
    df = pd.DataFrame(rows)
    ordered_cols = ["Event", "Shot ID"]
    if inc_tape: ordered_cols.append("Tapename")
    if inc_clip: ordered_cols.append("Clipname")
    ordered_cols += [
        "Src_In", "Src_Out", "Duration (Frames)", "Duration (TC)",
        "Rec_In", "Rec_Out", "*LOC TC", "*LOC Color", "*LOC Description",
    ]
    return df.reindex(columns=[c for c in ordered_cols if c in df.columns])


# =============================================
# STREAMLIT UI
# =============================================

def main() -> None:
    st.set_page_config(page_title="EDL Locator Extractor", layout="centered")

    st.markdown("""
    <style>
        .stApp { background-color: #1E2025; color: #F0F0F0; }
        .main-header {
            background: linear-gradient(135deg, #42B38F 0%, #80ED99 100%);
            padding: 2.5rem; border-radius: 1.5rem;
            text-align: center; color: #1E2025; margin-bottom: 2rem;
        }
        .glass-container {
            background: #2D2F34; border-radius: 1.5rem;
            padding: 2rem; margin-bottom: 1.5rem;
            border: 1px solid rgba(240,240,240,0.1);
        }
        .stButton button { background: #42B38F; color: #1E2025; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="main-header"><h1>EDL Locator Extractor</h1>'
        '<p>Extract locator data and durations</p></div>',
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        fps_label     = c1.selectbox("FPS", list(FPS_OPTIONS.keys()), index=2)
        preview_limit = c2.number_input("Preview Rows", min_value=10, value=50)
        sel_color     = c3.selectbox("Filter Color", FILTER_COLOR_OPTIONS)

        cc1, cc2, cc3, cc4 = st.columns(4)
        inc_t = cc1.checkbox("Tapename",        value=True)
        inc_c = cc2.checkbox("Clipname",         value=True)
        o_loc = cc3.checkbox("Only *LOC",        value=True,
                             help="Show only events that contain a LOC marker. "
                                  "Uncheck to show all edit events.")
        excl  = cc4.checkbox("Excl. Last Frame", value=False)

        st.markdown("</div>", unsafe_allow_html=True)

    fps     = FPS_OPTIONS[fps_label]
    is_drop = fps in DROP_FRAME_RATES

    uploaded_file = st.file_uploader("Upload EDL", type=["edl", "txt"])
    if not uploaded_file:
        return

    try:
        lines = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    df = parse_edl(lines, fps, is_drop, sel_color, inc_t, inc_c, o_loc, excl)

    if df.empty:
        if o_loc:
            st.warning("No LOC markers found in the uploaded EDL. "
                       "Try unchecking 'Only *LOC' to see all edit events.")
        else:
            st.warning("No edit events found in the uploaded EDL.")
        return

    st.dataframe(df.head(preview_limit), use_container_width=True)
    st.caption(f"Showing {min(preview_limit, len(df))} of {len(df)} rows.")

    csv_name = f"edl_locators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button(
        "Download CSV", df.to_csv(index=False),
        csv_name, "text/csv", use_container_width=True,
    )


if __name__ == "__main__":
    main()
