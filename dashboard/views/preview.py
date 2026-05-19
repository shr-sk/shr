"""Preview view — FB / IG mockups + Instant Form preview."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import streamlit.components.v1 as components

from auth.gate import gate

me = gate()

from preview_mockups import surfaces_for
from styles import hero, inject_css

inject_css()

ss = st.session_state


hero(
    "Preview",
    kicker="Step 2 of 3",
    subtitle="See how your ad will look across Facebook, Instagram, Stories, Reels, and the Instant Form.",
)

data = ss.get("preview_data")
if not data:
    st.info(
        "Build a campaign on the **Create** tab first. After you click "
        "*View report*, the preview populates here."
    )
    st.stop()

destination = data.get("destination", "Website")

# Inline meta-line under the hero — destination · business · currency
st.markdown(
    f"<div style='display:flex;gap:18px;color:#54595F;font-size:13px;margin-bottom:6px;'>"
    f"<span><strong style='color:#1C1E21;'>Destination</strong> · {destination}</span>"
    f"<span><strong style='color:#1C1E21;'>Business</strong> · {data.get('business_name', '—')}</span>"
    f"<span><strong style='color:#1C1E21;'>Currency</strong> · {data.get('currency', 'USD')}</span>"
    f"</div>",
    unsafe_allow_html=True,
)
st.divider()

surfaces = surfaces_for(destination)
labels = [label for label, _ in surfaces]

if len(surfaces) > 1:
    chosen = st.radio("Surface", labels, horizontal=True, label_visibility="collapsed")
    pairs = [(label, fn) for label, fn in surfaces if label == chosen]
else:
    pairs = surfaces

for label, fn in pairs:
    st.subheader(label)
    html = fn(data)
    height = (
        680 if "instant form" in label.lower() else
        560 if "stories" in label.lower() or "reels" in label.lower() else
        540 if "facebook feed" in label.lower() else
        520 if "instagram feed" in label.lower() else
        320
    )
    components.html(html, height=height, scrolling=True)
    st.divider()
