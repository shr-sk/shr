"""Refund & Cancellation Policy — public page (no auth required)."""
import streamlit as st

st.title("Refund & Cancellation Policy")
st.caption("Last updated: 17 May 2026")

st.markdown("""
## 1. Free trial

Every new account starts with a **2-day free trial** of the Starter plan.
No payment method is required to start the trial. The trial expires
automatically after 2 days — there is **nothing to refund** because
nothing was charged.

If you do not subscribe before the trial ends, your access is paused and
any active Meta campaigns are automatically paused on Meta's side
(see Service Delivery Policy).

## 2. Pro-rated refund within 7 days of first payment

If you subscribe (pay your first month's ₹999 or applicable amount) and
decide it's not for you, you may request a **pro-rated refund** within
**7 calendar days** of your first payment.

How the pro-rating works:

| Days used since first payment | Refund |
|---|---|
| 0–2 days | Full refund (₹999) |
| 3 days | ₹999 × (4/7) ≈ ₹571 refund |
| 4 days | ₹999 × (3/7) ≈ ₹428 refund |
| 5 days | ₹999 × (2/7) ≈ ₹286 refund |
| 6 days | ₹999 × (1/7) ≈ ₹143 refund |
| 7 days | Last day of eligibility (1/7 ≈ ₹143) |
| 8+ days | No refund — see Section 3 |

Refunds are issued back to the original payment method via Razorpay
within **5–7 business days** of approval.

## 3. After the 7-day window

Once 7 days have passed from your first payment, **no refund** is issued
for the current month. You may still cancel — see Section 4 — and your
subscription will not renew the following month.

## 4. Cancellation

You can cancel your subscription at any time. Two ways:

1. **In-app**: Go to the **Account** tab → in the future, a "Cancel
   subscription" button will be available there. Until then, use option 2.
2. **WhatsApp or email**: message us on **+91 9102916841** or email
   **sukumarpoddar90@gmail.com** with the subject line *"Cancel
   subscription"* and your registered email.

After cancellation:

- Your current paid period continues until the renewal date — you keep
  full access.
- No further charges are made.
- Your Meta campaigns continue to run on Meta's servers (we do not
  delete data on Meta's side). You retain full control via Meta Business
  Manager.

## 5. Subsequent monthly payments

For months **after the first**, the same pro-rating rule applies if you
request a refund within 7 days of that month's charge. After 7 days
into any month, no refund is issued for that month.

## 6. Failed renewals

If your monthly payment fails (e.g., card expired, insufficient funds),
Razorpay will retry per their standard schedule. After repeated failures,
your account is moved to `past_due` status and your active Meta
campaigns are paused automatically. Updating your payment method on the
Account tab restores access and resumes paused campaigns.

## 7. Exceptional refunds

We will consider a full refund outside the 7-day window if:

- The Service was unavailable for **more than 48 consecutive hours**
  during your billing month due to an issue on our side (not a
  third-party outage like Meta, Razorpay, or Streamlit Cloud).
- A billing error occurred (double charge, incorrect amount).

Email **sukumarpoddar90@gmail.com** with details and we'll review
within 5 business days.

## 8. Chargebacks

If you dispute a charge directly with your bank or card network instead
of contacting us, your account will be suspended pending dispute
resolution. We strongly prefer to handle refund requests directly —
it's faster and avoids dispute fees.

## 9. Contact

Sukumar Poddar
Bangalore, Karnataka, India
**sukumarpoddar90@gmail.com**
WhatsApp **+91 9102916841**

Refund requests are processed Monday–Friday, 10:00–18:00 IST. Response
time: within 24 hours of receipt.
""")
