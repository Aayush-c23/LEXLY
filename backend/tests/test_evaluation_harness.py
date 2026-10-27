"""
Automated Pytest CI Benchmark Gate & Noisy Simulation (QA-401, QA-402).
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.engine import corpus_cache
from backend.app.engine.eval_harness import evaluate_gold_dataset, run_noisy_user_comparison
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """Provides a managed TestClient with loaded corpus cache."""
    corpus_cache.load_corpus_from_seed()
    with TestClient(app) as test_client:
        yield test_client


def test_gold_dataset_benchmark_qa_401(client):
    """
    Ticket QA-401: Gold Dataset Automated Benchmark Gate.
    
    Acceptance Criteria:
    - Retrieval Recall@20: >= 98%
    - Multi-Label Resolution F1: >= 90% (Target: >= 92%)
    - Average Question Count: <= 3.5 (Target: <= 3.2)
    """
    results = evaluate_gold_dataset(client=client, noise_rate=0.0)

    # 1. Assert Retrieval Recall@20
    assert results["recall_at_20"] >= 0.98, (
        f"Recall@20 dropped below gate threshold: {results['recall_at_20'] * 100:.2f}% < 98%"
    )

    # 2. Assert Multi-Label Resolution F1
    assert results["f1_score"] >= 0.90, (
        f"Multi-label F1 score dropped below gate threshold: {results['f1_score'] * 100:.2f}% < 90%"
    )

    # 3. Assert Question Efficiency
    assert results["avg_questions"] <= 3.5, (
        f"Average questions to resolution exceeded target: {results['avg_questions']} > 3.5"
    )


def test_noisy_user_simulation_qa_402(client):
    """
    Ticket QA-402: Noisy User Simulator (epsilon = 0.10).

    Validates that Bayesian soft evidence scoring is fault-tolerant to 10% mistaken user responses.
    Acceptance Criteria:
    - Soft Bayesian F1 recovery: >= 85% under 10% noise.
    - Soft scoring accuracy improvement over hard-elimination: > 30%.
    """
    comparison = run_noisy_user_comparison(client=client, noise_rate=0.10)

    soft_f1 = comparison["soft_bayesian_f1"]
    hard_f1 = comparison["hard_elimination_f1"]
    improvement_pct = comparison["relative_improvement_pct"]

    # 1. Soft Bayesian scoring avoids fatal early pruning and maintains >= 85% F1
    assert soft_f1 >= 0.85, (
        f"Soft Bayesian F1 under 10% noise dropped below 85%: {soft_f1 * 100:.2f}%"
    )

    # 2. Soft Bayesian scoring demonstrates > 30% higher accuracy than hard-elimination filtering
    assert improvement_pct >= 30.0, (
        f"Soft Bayesian scoring failed to demonstrate > 30% improvement over hard elimination: {improvement_pct:.1f}%"
    )

