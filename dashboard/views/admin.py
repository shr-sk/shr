"""Admin panel — agency upgrades, manual subscription overrides.

Two ways to access:
  1. Set ADMIN_PASSWORD in env → enter that password
  2. OR: any user with is_admin=1 in DB (set via SQL once, or via /admin
     "Promote to admin" button only available to existing admins)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from auth import auth as auth_mod
from auth import db
from styles import hero, inject_css, status_pill

inject_css()


# ---------- Gate ----------

ss = st.session_state
ss.setdefault("admin_authed", False)


def _password_gate():
    expected = os.environ.get("ADMIN_PASSWORD")
    if not expected:
        st.error(
            "Admin panel is locked. Set `ADMIN_PASSWORD` in env to enable, "
            "or sign in with an admin-flagged user account."
        )
        st.stop()

    me = auth_mod.current_user()
    if me and me["is_admin"]:
        return  # already authed via user flag

    if ss.admin_authed:
        return

    hero("Admin", kicker="Restricted", subtitle="Enter the admin password to continue.")
    pw = st.text_input("Admin password", type="password")
    if st.button("Enter", type="primary"):
        if pw == expected:
            ss.admin_authed = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()


_password_gate()


# ---------- Panel ----------
hero(
    "Admin",
    kicker="Users & subscriptions",
    subtitle="Apply agency tier upgrades and manual subscription extensions.",
)

users = db.list_users()
if not users:
    st.info("No users yet.")
    st.stop()


# Search
q = st.text_input("Search by email", placeholder="email@example.com")
filtered = [u for u in users if (not q) or q.lower() in u["email"].lower()]

st.caption(f"{len(filtered)} user(s)")

for u in filtered:
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;'>"
                f"<span style='font-weight:600;font-size:15px;'>{u['email']}</span>"
                f"{status_pill(u.get('sub_status') or 'unknown')}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"id={u['id']} · currency={u['currency']} · tier=`{u['tier']}` · "
                f"client_limit={u['client_limit']} · seats={u['team_seats']} · "
                f"admin={'yes' if u['is_admin'] else 'no'}"
            )
            st.caption(
                f"created {u['created_at'][:10]} · trial ends {u['trial_ends_at'][:10]} · "
                f"period end: {(u.get('current_period_end') or '—')[:10]}"
            )
        with c2:
            # Quick actions
            tier = st.selectbox(
                "Tier",
                ["starter", "agency_lite", "agency_standard", "agency_pro"],
                index=["starter", "agency_lite", "agency_standard", "agency_pro"].index(u["tier"]) if u["tier"] in ("starter", "agency_lite", "agency_standard", "agency_pro") else 0,
                key=f"tier-{u['id']}",
            )
            limits = {
                "starter": (1, 1),
                "agency_lite": (5, 1),
                "agency_standard": (10, 2),
                "agency_pro": (25, 5),
            }
            new_limit, new_seats = limits[tier]
            if st.button("Apply tier", key=f"apply-{u['id']}", use_container_width=True):
                db.update_user_tier(u["id"], tier, new_limit, new_seats)
                st.success(f"Updated to {tier} ({new_limit} clients, {new_seats} seats).")
                st.rerun()

            days = st.number_input("Extend (days)", min_value=1, max_value=365, value=30, key=f"days-{u['id']}")
            if st.button("Mark paid · extend", key=f"extend-{u['id']}", type="primary", use_container_width=True):
                db.extend_subscription(u["id"], days=int(days))
                st.success(f"Extended by {days} days.")
                st.rerun()
