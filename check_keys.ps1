& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

python - <<EOF
import os
print("POLYGON_KEY:", os.getenv("POLYGON_API_KEY"))
print("ALPACA_KEY:", os.getenv("ALPACA_API_KEY"))
print("ALPACA_SECRET:", os.getenv("ALPACA_SECRET_KEY"))
EOF
