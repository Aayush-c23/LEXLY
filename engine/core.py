"""
Core Mathematical and Bayesian Information-Gain Constraint Engine for LEXLY.

Phase 0: Algorithm & Mathematical Design.
This module is pure, framework-free Python using NumPy for vectorized probability
and information entropy calculations over active legal provisions.
"""

from typing import Dict, List, Optional, Set, Tuple
import numpy as np


def calculate_shannon_entropy(probabilities: np.ndarray) -> float:
    """
    Computes Shannon entropy H(p) = -sum(p_i * log2(p_i)) in bits.

    Parameters
    ----------
    probabilities : np.ndarray
        Array of probabilities representing a discrete probability distribution.

    Returns
    -------
    float
        The Shannon entropy in bits. Returns 0.0 if the array has 1 or fewer
        non-zero elements (or if all probabilities are zero).
    """
    # Filter out near-zero or non-positive probabilities to safely evaluate log2
    p_nz = probabilities[probabilities > 1e-9]

    if len(p_nz) <= 1:
        return 0.0

    return float(-np.sum(p_nz * np.log2(p_nz)))


def update_posterior_soft(
    candidate_ids: List[int],
    current_posterior: Dict[int, float],
    fact_key: str,
    answer: str,
    matrix: Dict[int, Dict[str, str]],
    epsilon: float = 0.05,
) -> Dict[int, float]:
    """
    Updates the posterior probability distribution over legal candidates
    using Bayesian noise tolerance.

    Parameters
    ----------
    candidate_ids : List[int]
        Identifiers of active candidate provisions.
    current_posterior : Dict[int, float]
        Current mapping from provision_id to probability.
    fact_key : str
        The statutory fact key being answered (e.g., 'physical_contact').
    answer : str
        The user's response: 'TRUE', 'FALSE', or 'NOT_SURE'.
        Note: If answered as 'YES' or 'NO', callers can normalize to 'TRUE'/'FALSE'.
    matrix : Dict[int, Dict[str, str]]
        The statutory requirement matrix mapping provision_id to expected fact values:
        e.g., {provision_id: {"physical_contact": "TRUE", "weapon": "FALSE"}}.
    epsilon : float, optional
        Mistake/noise parameter representing probability of contradictory response,
        by default 0.05.

    Returns
    -------
    Dict[int, float]
        Normalized updated posterior distribution summing to 1.0.
    """
    # If the user is unsure, retain the posterior distribution without modification
    if answer == "NOT_SURE":
        return {pid: current_posterior.get(pid, 0.0) for pid in candidate_ids}

    # Normalize incoming answers if user passed YES/NO
    normalized_answer = answer
    if answer == "YES":
        normalized_answer = "TRUE"
    elif answer == "NO":
        normalized_answer = "FALSE"

    updated: Dict[int, float] = {}

    for pid in candidate_ids:
        prior_p = current_posterior.get(pid, 0.0)
        expected_val = matrix.get(pid, {}).get(fact_key)

        if expected_val is not None:
            if expected_val == normalized_answer:
                # Provision expected this answer -> reward
                updated[pid] = prior_p * (1.0 - epsilon)
            else:
                # Provision contradicts this answer -> penalize by epsilon
                updated[pid] = prior_p * epsilon
        else:
            # Provision is indifferent to this fact -> prior unchanged
            updated[pid] = prior_p

    total_weight = sum(updated.values())

    # Normalize so probabilities sum to 1.0
    if total_weight > 1e-12:
        return {pid: weight / total_weight for pid, weight in updated.items()}

    # Fallback to uniform distribution if all weights degenerate
    n = len(candidate_ids)
    if n > 0:
        return {pid: 1.0 / n for pid in candidate_ids}
    return {}


def evaluate_best_question(
    candidate_ids: List[int],
    current_posterior: Dict[int, float],
    known_facts: Dict[str, str],
    ignored_facts: Set[str],
    matrix: Dict[int, Dict[str, str]],
    default_q_f: float = 0.5,
    epsilon: float = 0.05,
) -> Tuple[Optional[str], float]:
    """
    Evaluates Shannon Information Gain across unknown fact ingredients to select
    the optimal clarification question using overlapping outcome partitions.

    Mathematical Formulation:
    -------------------------
    Let candidate provisions be partitioned into:
        T     = {i in C | provision i requires fact == TRUE}
        F_req = {i in C | provision i requires fact == FALSE}
        I     = {i in C | provision i is indifferent to fact}

    Marginal probabilities:
        P(YES) = sum_{i in T} p_i + q_f * sum_{i in I} p_i
        P(NO)  = sum_{i in F_req} p_i + (1 - q_f) * sum_{i in I} p_i

    Simulated posteriors:
        p^(YES) updates T by (1 - eps), F_req by eps, and I unchanged (normalized)
        p^(NO)  updates F_req by (1 - eps), T by eps, and I unchanged (normalized)

    Expected conditional entropy:
        H(C | Q) = P(YES) * H(p^(YES)) + P(NO) * H(p^(NO))
        IG(Q) = H(p) - H(C | Q)

    Parameters
    ----------
    candidate_ids : List[int]
        Identifiers of active candidate provisions.
    current_posterior : Dict[int, float]
        Current probability distribution over candidate provisions.
    known_facts : Dict[str, str]
        Facts already established as 'TRUE' or 'FALSE'.
    ignored_facts : Set[str]
        Facts permanently masked/skipped (e.g., from 'NOT_SURE' responses).
    matrix : Dict[int, Dict[str, str]]
        The statutory requirement matrix mapping provision_id to fact requirements.
    default_q_f : float, optional
        Prior probability of fact F being true among indifferent provisions, by default 0.5.
    epsilon : float, optional
        Noise parameter for simulated updates, by default 0.05.

    Returns
    -------
    Tuple[Optional[str], float]
        A tuple of (best_fact_key, best_information_gain). If no viable question
        or candidates exist, returns (None, 0.0).
    """
    if not candidate_ids:
        return None, 0.0

    # Extract probability vector aligned with candidate_ids
    raw_p = np.array([current_posterior.get(pid, 0.0) for pid in candidate_ids], dtype=np.float64)
    total_p = float(np.sum(raw_p))

    if total_p < 1e-12:
        return None, 0.0

    p_vector = raw_p / total_p
    current_entropy = calculate_shannon_entropy(p_vector)

    # Collect all unknown fact keys present across active candidate provisions
    candidate_fact_keys: Set[str] = set()
    for pid in candidate_ids:
        candidate_fact_keys.update(matrix.get(pid, {}).keys())

    unknown_keys = candidate_fact_keys - set(known_facts.keys()) - ignored_facts
    if not unknown_keys:
        return None, 0.0

    best_gain = -1.0
    best_fact_key: Optional[str] = None

    for fact_key in unknown_keys:
        t_indices: List[int] = []
        f_indices: List[int] = []
        i_indices: List[int] = []

        for idx, pid in enumerate(candidate_ids):
            exp_val = matrix.get(pid, {}).get(fact_key)
            if exp_val == "TRUE":
                t_indices.append(idx)
            elif exp_val == "FALSE":
                f_indices.append(idx)
            else:
                i_indices.append(idx)

        # Invariant Check: If all candidates are indifferent, IG is identically 0.0 bits
        if len(t_indices) == 0 and len(f_indices) == 0:
            if best_gain < 0.0:
                best_gain = 0.0
                best_fact_key = fact_key
            continue

        p_t = float(np.sum(p_vector[t_indices])) if t_indices else 0.0
        p_f = float(np.sum(p_vector[f_indices])) if f_indices else 0.0
        p_i = float(np.sum(p_vector[i_indices])) if i_indices else 0.0

        # Marginal probabilities of user answering YES or NO
        p_yes_marginal = p_t + default_q_f * p_i
        p_no_marginal = p_f + (1.0 - default_q_f) * p_i

        # Clamp marginals for numerical stability
        p_yes_marginal = min(max(p_yes_marginal, 0.0), 1.0)
        p_no_marginal = min(max(p_no_marginal, 0.0), 1.0)

        # 1. Simulate Posterior if user answers YES
        p_yes_post = np.copy(p_vector)
        if t_indices:
            p_yes_post[t_indices] *= (1.0 - epsilon)
        if f_indices:
            p_yes_post[f_indices] *= epsilon
        # indifferent indices remain unchanged

        sum_yes = float(np.sum(p_yes_post))
        if sum_yes > 1e-12:
            p_yes_post /= sum_yes
            h_yes = calculate_shannon_entropy(p_yes_post)
        else:
            h_yes = 0.0

        # 2. Simulate Posterior if user answers NO
        p_no_post = np.copy(p_vector)
        if f_indices:
            p_no_post[f_indices] *= (1.0 - epsilon)
        if t_indices:
            p_no_post[t_indices] *= epsilon
        # indifferent indices remain unchanged

        sum_no = float(np.sum(p_no_post))
        if sum_no > 1e-12:
            p_no_post /= sum_no
            h_no = calculate_shannon_entropy(p_no_post)
        else:
            h_no = 0.0

        # Conditional Entropy H(C | Q)
        h_cond = p_yes_marginal * h_yes + p_no_marginal * h_no
        gain = current_entropy - h_cond

        # Information gain cannot be negative
        gain = max(0.0, float(gain))

        if gain > best_gain:
            best_gain = gain
            best_fact_key = fact_key

    return best_fact_key, max(0.0, best_gain)
