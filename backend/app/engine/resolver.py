"""
Resolution of Statutory Provisions, Procedural Attributes, and Lesser-Included Offences (BE-302, BE-303).
"""

from typing import Any, Dict, List, Set, Tuple
from backend.app.schemas.analyze import LesserOffenceResult, ProvisionResult


def resolve_provisions_and_lesser_offences(
    candidate_ids: List[int],
    posterior: Dict[int, float],
    primary_legal_regime: str,
    known_facts: Dict[str, str],
    matrix: Dict[int, Dict[str, str]],
    hierarchy: Dict[int, List[Tuple[int, str]]],
    metadata: Dict[int, Dict[str, Any]],
    prob_threshold: float = 0.08,
) -> Tuple[List[ProvisionResult], List[LesserOffenceResult]]:
    """
    Ranks active candidate provisions and formats statutory results according
    to the active legal regime (BNS or IPC) while resolving hierarchy relations.
    """
    # 1. Filter candidates meeting probability threshold or strong fact alignment
    sorted_candidates = sorted(
        candidate_ids,
        key=lambda pid: posterior.get(pid, 0.0),
        reverse=True,
    )

    resolved_pids: List[int] = []
    for pid in sorted_candidates:
        prob = posterior.get(pid, 0.0)
        prov_reqs = matrix.get(pid, {})
        matches = 0
        contradictions = 0
        for f_key, exp_val in prov_reqs.items():
            if f_key in known_facts:
                if known_facts[f_key] == exp_val:
                    matches += 1
                else:
                    contradictions += 1

        if prob >= prob_threshold:
            resolved_pids.append(pid)
        elif contradictions == 0 and matches >= 2 and len(resolved_pids) < 4:
            resolved_pids.append(pid)
        elif prob >= 0.001 and contradictions == 0 and matches >= 1 and len(resolved_pids) < 4:
            resolved_pids.append(pid)

    # Fallback to the top candidate if none passed the threshold
    if not resolved_pids and sorted_candidates:
        resolved_pids = [sorted_candidates[0]]

    # 2. Build primary provision results
    provisions_result: List[ProvisionResult] = []
    primary_pid_set: Set[int] = set(resolved_pids)

    for pid in resolved_pids:
        meta = metadata.get(pid, {})
        prob = float(posterior.get(pid, 0.0))

        # Determine Act title and primary vs cross-reference citations
        bns_eq = meta.get("bns_equivalent") or f"Section {meta.get('section_number', '')} BNS"
        ipc_eq = meta.get("ipc_equivalent") or ""

        if primary_legal_regime == "IPC" and ipc_eq:
            act_name = "Indian Penal Code, 1860"
            primary_citation = ipc_eq
            cross_citation = bns_eq
            sec_num = ipc_eq.replace("Section ", "").replace(" IPC", "").strip() or str(meta.get("section_number", ""))
        else:
            act_name = "Bharatiya Nyaya Sanhita, 2023"
            primary_citation = bns_eq
            cross_citation = ipc_eq
            sec_num = str(meta.get("section_number", ""))

        # Matched facts: compare known facts with provision requirements
        prov_reqs = matrix.get(pid, {})
        matched_facts: Dict[str, str] = {}
        for f_key, exp_val in prov_reqs.items():
            if f_key in known_facts and known_facts[f_key] == exp_val:
                matched_facts[f_key] = exp_val

        provisions_result.append(
            ProvisionResult(
                provision_id=pid,
                section_number=sec_num,
                act_name=act_name,
                primary_citation=primary_citation,
                cross_reference_citation=cross_citation,
                title=str(meta.get("title", "")),
                plain_summary=str(meta.get("plain_summary", "")),
                punishment=str(meta.get("punishment", "")),
                is_cognizable=bool(meta.get("is_cognizable", True)),
                is_bailable=bool(meta.get("is_bailable", False)),
                compoundable_type=str(meta.get("compoundable_type", "NON_COMPOUNDABLE")),
                triable_by=str(meta.get("triable_by", "Court of Session")),
                posterior_probability=round(prob, 4),
                matched_facts=matched_facts,
            )
        )

    # 3. Resolve lesser-included offences
    lesser_offences: List[LesserOffenceResult] = []
    seen_lesser: Set[int] = set()

    for pid in resolved_pids:
        children = hierarchy.get(pid, [])
        for child_id, rel_type in children:
            if child_id not in primary_pid_set and child_id not in seen_lesser:
                c_meta = metadata.get(child_id, {})
                if c_meta:
                    seen_lesser.add(child_id)
                    lesser_offences.append(
                        LesserOffenceResult(
                            provision_id=child_id,
                            section_number=str(c_meta.get("section_number", "")),
                            title=str(c_meta.get("title", "")),
                            relation_type=rel_type,
                        )
                    )

    return provisions_result, lesser_offences

