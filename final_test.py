"""One-time evaluation on the held-out test split. Run once, at the end.

Run: python final_test.py --confirm-final
Writes outputs/test_metrics.json, outputs/test_summary.md and
outputs/TEST_RUN_LOG.json (git commit, time). Refuses to run again once the
log exists, so the test set is used exactly once. Only run it after every
measure, its direction and all settings are frozen on dev.
"""

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import measures
from common import SEED, evaluate_measure, load_split
from run_all import table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-final", action="store_true",
                        help="Required: confirms all measures are frozen.")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    log = args.output / "TEST_RUN_LOG.json"
    if not args.confirm_final:
        parser.error("Pass --confirm-final once every measure is frozen on dev.")
    if log.exists():
        parser.error(f"The test set was already evaluated (see {log}). It is used only once.")

    _, train, dev, test, digest = load_split()
    registry = measures.build(train, dev + test)
    metrics = {
        name: evaluate_measure(train, test, fn, higher_means_easier=easier)
        for name, (_, fn, easier) in registry.items()
    }
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "test_metrics.json").write_text(
        json.dumps({"source_sha256": digest, "seed": SEED, "measures": metrics}, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = (
        "# Test results (generated once by final_test.py)\n\n"
        f"{len(train)} train and {len(test)} test explanations. Cutoffs fit on train only.\n\n"
        "## Human-perceived level (primary)\n\n"
        f"{table(metrics, registry, 'perceived')}\n\n"
        "## Intended level (secondary)\n\n"
        f"{table(metrics, registry, 'intended')}\n"
    )
    (args.output / "test_summary.md").write_text(summary, encoding="utf-8")
    log.write_text(json.dumps({"commit": commit,
                               "time_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n",
                   encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
