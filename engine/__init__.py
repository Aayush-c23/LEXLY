"""
Package initialization for LEXLY core engine.
"""

from engine.core import (
    calculate_shannon_entropy,
    evaluate_best_question,
    update_posterior_soft,
)

__all__ = [
    "calculate_shannon_entropy",
    "evaluate_best_question",
    "update_posterior_soft",
]
