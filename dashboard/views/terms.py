"""Terms of Service — public page (no auth required)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))

import streamlit as st

from styles import hero, inject_css

inject_css()

hero("Terms of Service", kicker="Last updated 17 May 2026")

st.markdown("""
## 1. About this service

Meta Ads Launcher ("the Service") is a software-as-a-service dashboard
operated by **Sukumar Poddar**, sole proprietor based in Bangalore, India
("we", "us"). The Service helps you create, preview, launch, and manage
advertising campaigns on Meta platforms (Facebook and Instagram) using
your own Meta Business Manager account.

You access the Service at the URL where it is hosted, by signing up with
an email address and password.

## 2. Eligibility

To use the Service you must:

- Be at least **18 years old** and legally able to enter into contracts in
  your jurisdiction.
- Have an active Meta Business Manager account with a Facebook Page and
  an Ad Account.
- Comply with Meta's Advertising Policies and Community Standards.

## 3. Account registration

You agree to provide accurate information when registering. You are
responsible for keeping your password secure. We hash passwords using
bcrypt and never store them in plain text. You are responsible for all
activity that happens under your account.

## 4. Subscription and billing

- The Service offers a **2-day free trial** on signup. No payment method
  is required during the trial.
- After the trial, continued access requires a paid subscription. The
  Starter plan is **₹999 per month** for users in India, billed monthly
  via Razorpay. International pricing (where supported) is **$21 per
  month** billed via Razorpay International.
- Subscriptions renew automatically each month unless cancelled. By
  subscribing, you authorise Razorpay to charge your registered payment
  method on the renewal date.
- All payments are processed by Razorpay. We do not see, store, or have
  access to your card details — Razorpay's PCI-DSS compliant systems
  handle all card data.

## 5. Your responsibilities

You agree that:

- You will only run campaigns for ad accounts you own or are explicitly
  authorised to operate (e.g., a client who has granted you access via
  Meta Business Manager Partner Access).
- The advertising content you upload through the Service (images, videos,
  text, landing pages) is yours or properly licensed to you.
- You will not use the Service to run ads that violate Meta's policies,
  Indian advertising regulations, or applicable consumer protection laws.
- You will not attempt to reverse engineer, scrape, or interfere with
  the Service.

## 6. Service availability

We aim to keep the Service available continuously but do not guarantee
uninterrupted access. Scheduled maintenance, third-party outages (Meta
API, Razorpay, Streamlit Cloud, Turso, Gemini API), and force majeure
events may cause interruptions.

## 7. Termination

You may cancel your subscription at any time from the **Account** tab.
We may suspend or terminate your account if you violate these Terms or
applicable law. On termination, your access ends but your live Meta
campaigns remain in your Meta Ad Account (we never delete data on
Meta's servers).

## 8. Limitation of liability

The Service is provided "as is". To the maximum extent permitted by law,
we are not liable for:

- Indirect, incidental, or consequential damages.
- Loss of advertising spend, revenue, or business opportunity arising
  from your use of the Service.
- Outcomes of Meta's ad delivery, auction performance, or policy
  enforcement.

Our aggregate liability for any claim is limited to the amount you paid
us in the **12 months preceding** the claim.

## 9. Changes to these Terms

We may update these Terms from time to time. Material changes will be
notified by email or via an in-app notice at least 7 days before they
take effect.

## 10. Governing law and jurisdiction

These Terms are governed by the laws of **India**. Any disputes shall
be subject to the exclusive jurisdiction of the **courts of Bangalore,
Karnataka, India**.

## 11. Contact

For questions about these Terms, contact us at
**sukumarpoddar90@gmail.com** or WhatsApp **+91 9102916841**.
""")
