#!/usr/bin/env python
"""Create Stripe products and prices for TOOD-OS plans.

Usage: python scripts/setup_stripe.py
Writes STRIPE_PRICE_* lines to .env.
Never prints secret key values.
"""

import pathlib
import re
import sys

import stripe

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Read key from .env without importing settings (avoids loading all settings)
def _read_env(key: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text().splitlines():
        if line.strip().startswith(f"{key}="):
            return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main():
    secret_key = _read_env("STRIPE_SECRET_KEY")
    if not secret_key or secret_key.startswith("sk_test_YOUR") or "placeholder" in secret_key.lower():
        print("ERROR: STRIPE_SECRET_KEY not set or is a placeholder in .env")
        print("Set a real Stripe test key and re-run.")
        sys.exit(1)

    stripe.api_key = secret_key

    plans = [
        {"key": "STRIPE_PRICE_STARTER", "name": "TOOD-OS Starter", "amount": 9900},
        {"key": "STRIPE_PRICE_PROFESSIONAL", "name": "TOOD-OS Professional", "amount": 29900},
        {"key": "STRIPE_PRICE_ENTERPRISE", "name": "TOOD-OS Enterprise", "amount": 79900},
    ]

    results = {}
    for plan in plans:
        print(f"Creating product: {plan['name']} ...")
        product = stripe.Product.create(name=plan["name"])
        price = stripe.Price.create(
            product=product.id,
            unit_amount=plan["amount"],
            currency="gbp",
            recurring={"interval": "month"},
        )
        results[plan["key"]] = price.id
        print(f"  Product: {product.id}  Price: {price.id}  Amount: £{plan['amount']//100}/mo")

    # Update .env with price IDs
    env_path = ROOT / ".env"
    env_text = env_path.read_text() if env_path.exists() else ""
    for key, value in results.items():
        pattern = rf"^{re.escape(key)}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, env_text, re.MULTILINE):
            env_text = re.sub(pattern, replacement, env_text, flags=re.MULTILINE)
        else:
            env_text = env_text.rstrip("\n") + f"\n{replacement}\n"
    env_path.write_text(env_text)
    print("\n.env updated with price IDs:")
    for k, v in results.items():
        print(f"  {k}={v}")
    print("\nDone. Run the API and test a checkout flow.")


if __name__ == "__main__":
    main()
