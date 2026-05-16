"""Meta Ads Launcher — entry point.

When not signed in:  only the Sign-in page is in the nav.
When signed in:      Dashboard · Create · Preview · Manage · Account
                     (+ Admin tab if the user is_admin OR ADMIN_PASSWORD is set)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "payload_pipeline"))

import streamlit as st

st.set_page_config(
    page_title="Meta Ads Launcher",
    page_icon="📣",
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

if me is None:
    # Not authed — only show the login page
    pages = [
        st.Page(str(THIS_DIR / "views" / "login.py"), title="Sign in", icon="🔐", default=True),
    ]
else:
    pages = [
        st.Page(str(THIS_DIR / "views" / "dashboard.py"), title="Dashboard", icon="📊", default=True),
        st.Page(str(THIS_DIR / "views" / "create.py"),    title="Create",    icon="🚀"),
        st.Page(str(THIS_DIR / "views" / "preview.py"),   title="Preview",   icon="👁️"),
        st.Page(str(THIS_DIR / "views" / "manage.py"),    title="Manage",    icon="🎛️"),
        st.Page(str(THIS_DIR / "views" / "account.py"),   title="Account",   icon="⚙️"),
    ]
    # Admin tab — visible only to admins, or to anyone if ADMIN_PASSWORD set
    if me.get("is_admin") or os.environ.get("ADMIN_PASSWORD"):
        pages.append(st.Page(str(THIS_DIR / "views" / "admin.py"), title="Admin", icon="🛡️"))

nav = st.navigation(pages, position="top")
nav.run()
