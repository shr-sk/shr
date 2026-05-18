"""Service Delivery Policy — public page (no auth required).

Razorpay's documentation calls this "Shipping Policy". For a SaaS that
delivers a digital service (no physical goods), this is the equivalent
document — clarifying when and how the service is delivered.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))

import streamlit as st

from styles import hero, inject_css

inject_css()

hero("Service Delivery Policy", kicker="Last updated 17 May 2026")

st.markdown("""
## 1. Nature of the Service

Meta Ads Launcher is a **digital software-as-a-service**. There are no
physical goods to ship. Delivery happens entirely online via the web
application.

## 2. When access is delivered

| Event | Access activated |
|---|---|
| You sign up for a free trial | **Immediately** on email + password submission |
| You complete a subscription payment via Razorpay | **Within 2 minutes** of Razorpay's payment confirmation |
| You upgrade to an Agency tier via WhatsApp invoice | **Within 24 hours** of payment confirmation |

If you do not see your subscription active within 10 minutes of a
successful Razorpay payment, click **Refresh status** on the **Account**
tab. If still not active, contact us — see Section 6.

## 3. What "delivery" includes

A delivered subscription gives you:

- Access to all 5 main tabs: Dashboard, Create, Preview, Manage, Account.
- The ability to add up to 1 client Meta Ad Account (Starter tier; more
  on higher tiers).
- AI-assisted ad copy generation (via Gemini API) and city resolution
  for geo-targeting.
- One-click launching of campaigns to your connected Meta Ad Account.
- Auto-pause / auto-resume of campaigns based on subscription status.

## 4. Service uptime

We host the Service on **Streamlit Cloud** with a database on **Turso**.
Both providers have their own SLAs. We aim for **best-effort 99%+
uptime** but do not provide a formal SLA at this stage. Planned
maintenance is rare and announced in advance via in-app notice or email.

Periods of unavailability that are not our fault — outages of Meta's
API, Razorpay, Streamlit Cloud, Turso, or the Gemini API — do not count
against our uptime commitment.

## 5. No physical shipping

This is a fully digital service. We do not ship any physical product.
No shipping address is collected during signup or checkout. No shipping
or handling fees apply.

## 6. Support and issue reporting

If you experience issues with service delivery — signup not working,
payment confirmed but subscription not active, ads not launching,
dashboard not loading — contact us:

- **Email**: sukumarpoddar90@gmail.com
- **WhatsApp**: +91 9102916841

**Response time**: within 24 hours, Monday–Friday, 10:00–18:00 IST.

For urgent issues during business hours, WhatsApp is faster.

## 7. Service modifications

We may add new features, change limits on tiers, or modify the dashboard
layout from time to time. Material changes that affect what you pay or
how the Service works will be notified at least 7 days in advance.

## 8. Termination of service

Your access ends when:

- You cancel your subscription (next renewal does not occur).
- A renewal payment fails repeatedly and is not resolved.
- We terminate your account for violation of the Terms of Service.

On termination, your campaigns continue to run inside your Meta Ad
Account — we do not delete data on Meta's servers. You retain full
control via Meta Business Manager directly.

## 9. Contact

Sukumar Poddar
Bangalore, Karnataka, India
**sukumarpoddar90@gmail.com**
WhatsApp **+91 9102916841**
""")
