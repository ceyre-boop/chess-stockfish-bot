from dotenv import load_dotenv
import os
import pathlib

# Force-load .env from project root
ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Confirm .env loaded
assert os.getenv("MT5_ACTIVE_ACCOUNT") is not None, "Failed to load .env"
