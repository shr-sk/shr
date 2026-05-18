"""Meta Ads Launcher — entry point.

When not signed in:  only the Sign-in page is in the nav.
When signed in:      Dashboard · Create · Preview · Manage · Account
                     (+ Admin tab ONLY for users flagged is_admin = 1 in DB)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "payload_pipeline"))

import streamlit as st

st.set_page_config(
    page_title="Meta Ads Launcher",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auth helpers
from auth import auth as auth_mod  # noqa: E402

# Cookies populate AFTER the controller component renders, so the very first
# pass returns None even when a valid session cookie exists. Force one rerun
# to let the component send its value back, then the second pass restores.
me = auth_mod.current_user()
if me is None and not st.session_state.get("_cookie_warmup_done"):
    st.session_state["_cookie_warmup_done"] = True
    # Give the cookie component a tick to render + report its value
    me = auth_mod.current_user()

THIS_DIR = Path(__file__).parent

# Public policy pages — visible in nav regardless of auth state so payment
# processors (Razorpay) and other reviewers can navigate to them without
# needing to sign up.
policy_pages = [
    st.Page(str(THIS_DIR / "views" / "terms.py"),   title="Terms"),
    st.Page(str(THIS_DIR / "views" / "privacy.py"), title="Privacy"),
    st.Page(str(THIS_DIR / "views" / "refund.py"),  title="Refund"),
    st.Page(str(THIS_DIR / "views" / "service.py"), title="Service"),
]

if me is None:
    # Not authed — show login + policy pages
    pages = [
        st.Page(str(THIS_DIR / "views" / "login.py"), title="Sign in", default=True),
        *policy_pages,
    ]
else:
    pages = [
        st.Page(str(THIS_DIR / "views" / "dashboard.py"), title="Dashboard", default=True),
        st.Page(str(THIS_DIR / "views" / "create.py"),    title="Create"),
        st.Page(str(THIS_DIR / "views" / "preview.py"),   title="Preview"),
        st.Page(str(THIS_DIR / "views" / "manage.py"),    title="Manage"),
        st.Page(str(THIS_DIR / "views" / "account.py"),   title="Account"),
        *policy_pages,
    ]
    # Admin tab — visible ONLY to users flagged is_admin = 1 in the DB.
    # ADMIN_PASSWORD acts as a backup gate inside admin.py for emergency access
    # via direct URL, but the tab itself never appears in the nav for customers.
    if me.get("is_admin"):
        pages.append(st.Page(str(THIS_DIR / "views" / "admin.py"), title="Admin"))

nav = st.navigation(pages, position="top")
nav.run()
