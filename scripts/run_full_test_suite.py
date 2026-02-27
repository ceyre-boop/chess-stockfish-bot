import subprocess
import sys

TEST_GROUPS = [
    ("UNIT", "tests/unit"),
    ("INTEGRATION", "tests/integration"),
    ("FUNCTIONAL", "tests/functional"),
]

RESULTS = {}


for group, path in TEST_GROUPS:
    print(f"\n=== Running {group} tests ({path}) ===")
    args = [sys.executable, "-m", "pytest", path]
    if group == "FUNCTIONAL":
        args.append("-q")
    else:
        args.append("-s")
    result = subprocess.run(args, capture_output=True, text=True)
    RESULTS[group] = result.returncode
    # Print provider selection logs and engine metadata keys for FUNCTIONAL
    if group == "FUNCTIONAL":
        for line in result.stdout.splitlines():
            if ("Provider:" in line or "Symbol:" in line or "bars:" in line or "MT5 symbol:" in line or "ACTION:" in line):
                print(line)
            if "regime_cluster" in line or "participant_likelihoods" in line or "ev_features" in line or "search_weights" in line or "risk_envelope" in line:
                print("[ENGINE METADATA KEY]", line.split(":")[0])
        # Print summary
        print("\n--- FUNCTIONAL TEST SUMMARY ---")
        if result.returncode == 0:
            print("FUNCTIONAL: PASS")
        else:
            print("FUNCTIONAL: FAIL")
    else:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

print("\n=== SUMMARY ===")
for group in TEST_GROUPS:
    name = group[0]
    code = RESULTS[name]
    status = "PASS" if code == 0 else "FAIL"
    print(f"{name}: {status}")

if any(code != 0 for code in RESULTS.values()):
    sys.exit(1)
else:
    sys.exit(0)

def main():
    pass  # For script entry wiring
