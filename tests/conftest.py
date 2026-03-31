from dotenv import load_dotenv
import os
import pathlib

# Force-load .env from project root
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Try to load .env, fallback to .env.test for CI/testing
if (ROOT / ".env").exists():
    load_dotenv(ROOT / ".env")
else:
    load_dotenv(ROOT / ".env.test")

# Confirm .env loaded - use dummy value for testing if not found
if os.getenv("MT5_ACTIVE_ACCOUNT") is None:
    os.environ["MT5_ACTIVE_ACCOUNT"] = "12345678"
