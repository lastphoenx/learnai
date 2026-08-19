#!/usr/bin/env python3
"""Schlüssel für .env erzeugen."""

import base64
import secrets


def main() -> None:
    master = base64.b64encode(secrets.token_bytes(32)).decode()
    session = secrets.token_urlsafe(64)
    print("In .env eintragen:\n")
    print(f"ENCRYPTION_MASTER_KEY={master}")
    print(f"SESSION_SECRET={session}")


if __name__ == "__main__":
    main()
