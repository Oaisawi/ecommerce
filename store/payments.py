"""
Mock payment processor. Never touches the network or any real PSP.
All decisions are made locally based on test card numbers (Stripe-style).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


# Luhn algorithm for card number validation
def _luhn_valid(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if not digits:
        return False
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _detect_brand(number: str) -> str:
    n = number.replace(" ", "")
    if re.match(r"^4", n):
        return "VISA"
    if re.match(r"^5[1-5]|^2[2-7]", n):
        return "MASTERCARD"
    if re.match(r"^3[47]", n):
        return "AMEX"
    if re.match(r"^6(?:011|5)", n):
        return "DISCOVER"
    return "UNKNOWN"


# Stripe-style test card table: number (no spaces) → (status, failure_reason)
_TEST_CARDS: dict[str, tuple[str, str]] = {
    "4242424242424242": ("paid", ""),
    "4000000000000002": ("failed", "Your card was declined."),
    "4000000000009995": ("failed", "Your card has insufficient funds."),
    "4000000000000069": ("failed", "Your card has expired."),
    "4000000000000127": ("failed", "Your card's security code is incorrect."),
    "5555555555554444": ("paid", ""),   # Mastercard
    "378282246310005":  ("paid", ""),   # Amex
    "6011111111111117": ("paid", ""),   # Discover
}


@dataclass
class PaymentResult:
    status: str          # "paid" | "failed"
    method: str
    card_brand: str = ""
    card_last4: str = ""
    wallet_email: str = ""
    failure_reason: str = ""
    txn_id: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "paid"


def process_payment(
    *,
    method: str,
    amount: Decimal,
    card: dict | None = None,
    wallet_email: str = "",
) -> PaymentResult:
    """
    Pure-Python mock. No network calls, no real charges.

    Args:
        method:       One of Payment.Method values.
        amount:       Decimal amount (informational only — not actually charged).
        card:         Dict with keys: number, exp, cvc, name  (only for method="card").
        wallet_email: Email for PayPal / Google Pay mocks.

    Returns:
        PaymentResult with status, card_brand, card_last4, failure_reason.
    """
    from .models import Payment

    if method == Payment.Method.COD:
        return PaymentResult(status="paid", method=method)

    if method in (Payment.Method.APPLE_PAY, Payment.Method.GOOGLE_PAY, Payment.Method.PAYPAL):
        return PaymentResult(
            status="paid",
            method=method,
            wallet_email=wallet_email or f"sandbox@{method.replace('_', '')}.mock",
        )

    # Credit / Debit card
    if method == Payment.Method.CARD:
        raw_number = (card or {}).get("number", "").replace(" ", "").replace("-", "")
        if not raw_number.isdigit():
            return PaymentResult(
                status="failed",
                method=method,
                failure_reason="Please enter a valid card number.",
            )
        if not _luhn_valid(raw_number):
            return PaymentResult(
                status="failed",
                method=method,
                failure_reason="Your card number is invalid.",
            )
        brand = _detect_brand(raw_number)
        last4 = raw_number[-4:]

        # Check known test cards first
        if raw_number in _TEST_CARDS:
            status, reason = _TEST_CARDS[raw_number]
        else:
            # Any other Luhn-valid card succeeds
            status, reason = "paid", ""

        return PaymentResult(
            status=status,
            method=method,
            card_brand=brand,
            card_last4=last4,
            failure_reason=reason,
        )

    return PaymentResult(status="failed", method=method, failure_reason="Unknown payment method.")
