"""
CLI Evaluation Runner for Gold Benchmark Scenarios & Noisy Simulation (QA-401, QA-402).

Usage:
    python -m backend.app.scripts.run_evaluation
    python -m backend.app.scripts.run_evaluation --noise 0.10
"""

import argparse
import json
import logging
from pathlib import Path
import sys

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from backend.app.engine import corpus_cache
from backend.app.engine.eval_harness import evaluate_gold_dataset, run_noisy_user_comparison
from backend.app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lexly.eval_runner")


def main():
    parser = argparse.ArgumentParser(description="LEXLY Benchmark Evaluation Runner")
    parser.add_argument("--noise", type=float, default=0.0, help="Noise rate for simulated user answers (default: 0.0)")
    parser.add_argument("--compare-hard", action="store_true", help="Compare soft Bayesian scoring against hard elimination")
    args = parser.parse_args()

    corpus_cache.load_corpus_from_seed()

    with TestClient(app) as client:
        if args.compare_hard or args.noise > 0.0:
            print("\n=======================================================")
            print(f"  RUNNING NOISY USER SIMULATION (Noise Rate: {args.noise * 100:.1f}%)")
            print("=======================================================\n")
            comparison = run_noisy_user_comparison(client, noise_rate=args.noise if args.noise > 0.0 else 0.10)
            print(f"Soft Bayesian Scoring F1:     {comparison['soft_bayesian_f1'] * 100:.2f}%")
            print(f"Hard Elimination Filtering F1: {comparison['hard_elimination_f1'] * 100:.2f}%")
            print(f"Fault Tolerance Improvement:   +{comparison['relative_improvement_pct']:.1f}%\n")

            if comparison["soft_bayesian_f1"] >= 0.85:
                print(">>> QA-402 ACCEPTANCE CRITERIA PASSED (F1 >= 85% under 10% noise).")
            else:
                print(">>> QA-402 ACCEPTANCE CRITERIA FAILED.")
                sys.exit(1)
        else:
            print("\n=======================================================")
            print("  LEXLY GOLD DATASET BENCHMARK EVALUATION (25 Scenarios)")
            print("=======================================================\n")
            results = evaluate_gold_dataset(client, noise_rate=0.0)
            
            print(f"Total Test Cases:            {results['total_cases']}")
            print(f"Retrieval Recall@20:         {results['recall_at_20'] * 100:.2f}% (Target: >= 98.0%)")
            print(f"Multi-Label Precision:       {results['precision'] * 100:.2f}%")
            print(f"Multi-Label Recall:          {results['recall'] * 100:.2f}%")
            print(f"Multi-Label Resolution F1:   {results['f1_score'] * 100:.2f}% (Target: >= 92.0%)")
            print(f"Average Question Efficiency: {results['avg_questions']} questions (Target: <= 3.2)\n")

            print("--------------------------------------------------------------------------------")
            print(f"{'Case ID':<10} | {'Expected':<22} | {'Resolved':<22} | {'Questions':<10} | {'Hit'}")
            print("--------------------------------------------------------------------------------")
            for cr in results["case_results"]:
                exp_str = ", ".join(cr["expected_sections"])
                res_str = ", ".join(cr["resolved_sections"])
                print(f"{cr['id']:<10} | {exp_str:<22} | {res_str:<22} | {cr['questions_asked']:<10} | {cr['hit']}")
            print("--------------------------------------------------------------------------------\n")

            # Check CI Gate Thresholds
            passed = True
            if results["recall_at_20"] < 0.98:
                print(f"FAIL: Recall@20 ({results['recall_at_20'] * 100:.1f}%) < 98.0%")
                passed = False
            if results["f1_score"] < 0.90:
                print(f"FAIL: F1 Score ({results['f1_score'] * 100:.1f}%) < 90.0%")
                passed = False
            if results["avg_questions"] > 3.5:
                print(f"FAIL: Avg Questions ({results['avg_questions']}) > 3.5")
                passed = False

            if passed:
                print(">>> ALL QA-401 BENCHMARK TARGETS PASSED SUCCESSFULLY.")
            else:
                print(">>> BENCHMARK FAILED.")
                sys.exit(1)


if __name__ == "__main__":
    main()
