"""Privacy Policy — public page (no auth required)."""
import streamlit as st

st.title("Privacy Policy")
st.caption("Last updated: 17 May 2026")

st.markdown("""
## 1. Who we are

Meta Ads Launcher is operated by **Sukumar Poddar**, sole proprietor
based in Bangalore, India. This Privacy Policy explains what personal
data we collect, why we collect it, and how we handle it. By using the
Service you agree to the data practices described below.

## 2. What data we collect

We collect only what is necessary to operate the Service:

| Category | Examples | Why |
|---|---|---|
| Account data | Email address, hashed password, currency preference | To create + secure your account |
| Subscription data | Trial start/end date, subscription status, Razorpay subscription ID | To enforce billing |
| Business context | Your business name, website URL, business description | To help you build campaigns |
| Meta credentials | Meta Ad Account ID, Page ID, Instagram Actor ID | To launch ads on your behalf |
| Ad content | Headlines, descriptions, keywords you type; images and videos you upload | To create the ad campaigns you request |
| Session data | A randomly generated session token stored in a browser cookie | To keep you logged in |
| Usage data | Page views, button clicks (basic only) | To diagnose bugs |

We do **not** collect: government ID numbers, financial card numbers
(those go directly to Razorpay), location data beyond cities you enter,
or biometric data.

## 3. Where your data is stored

- **Account + subscription data**: stored in our database (Turso, a
  cloud SQLite service) in the AWS Asia-Pacific (Mumbai) region.
- **Uploaded media files**: stored temporarily on Streamlit Cloud
  (where the app runs). Media is also uploaded to Meta's `/adimages`
  endpoint when you launch a campaign, and from that point lives in
  your Meta Ad Account.
- **Payment data**: handled entirely by Razorpay. We never see or store
  card numbers.

## 4. Third parties we use

| Provider | Purpose | What they receive |
|---|---|---|
| **Meta (Facebook)** | Run your ad campaigns | Ad account ID, Page ID, ad creative |
| **Razorpay** | Process subscription payments | Your email, subscription amount |
| **Google (Gemini API)** | Generate ad copy + resolve city coordinates | Your business description + product description (text only, no media) |
| **Streamlit Cloud** | Host the application | Account session traffic |
| **Turso** | Database hosting | All persisted account + subscription data |

Each provider has its own privacy policy. We choose providers we
believe comply with reasonable data protection standards.

## 5. How we use your data

We use your data only to:

- Operate the Service (signup, login, billing, campaign launching).
- Communicate operationally with you (renewal reminders, billing
  failures, account security).
- Improve the Service (debugging, usability).

We do **not**:

- Sell your data to third parties.
- Share your data for advertising other products.
- Use your ad content, business descriptions, or media to train AI
  models. Gemini API calls are transactional only.

## 6. Cookies

We use a single session cookie (`meta_ads_session`) to keep you signed
in for up to 30 days. Removing this cookie signs you out. We do not use
tracking cookies or third-party advertising cookies.

## 7. Your rights

You have the right to:

- **Access** the data we hold about you.
- **Correct** inaccurate data.
- **Delete** your account and associated data.
- **Export** your data in a machine-readable format.

To exercise any of these, email **sukumarpoddar90@gmail.com**. We will
respond within 30 days.

## 8. Security

- All connections are over HTTPS.
- Passwords are hashed using bcrypt with a per-user salt.
- Database credentials and API keys are stored as environment variables,
  never in code or version control.
- Session tokens are randomly generated UUIDs with a 30-day expiry.

No system is perfect. If we discover a breach affecting your data, we
will notify you within 72 hours.

## 9. Data retention

- Account data is retained while your account is active and for 12
  months after deletion, for accounting purposes.
- Uploaded media files are retained for 90 days after launch then
  purged.
- Session tokens auto-expire after 30 days of inactivity.

## 10. Children

The Service is not intended for users under 18. We do not knowingly
collect data from minors.

## 11. Changes to this Policy

We may update this Policy. The "Last updated" date at the top reflects
the most recent revision. Material changes will be notified via email.

## 12. Contact

Sukumar Poddar
Bangalore, Karnataka, India
**sukumarpoddar90@gmail.com**
WhatsApp **+91 9102916841**
""")
