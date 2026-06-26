#!/usr/bin/env python3
"""
Entry point je .env file auto-load kore tarpor bot chalay.
Local e cholar jonno: `python run.py`
(Railway/Render e env var dashboard theke dile direct `python bot.py` o cholbe.)
"""
import os

# .env file load kora (python-dotenv optional - na thakle manual parse)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv install na thakle - simple manual loader
    if os.path.exists(".env"):
        with open(".env", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from bot import main  # noqa: E402

if __name__ == "__main__":
    main()
