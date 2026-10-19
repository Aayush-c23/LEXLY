# Implementation Plan: LEXLY - Adaptive Indian Legal Analysis Assistant

## 1. Executive Summary & Core Architectural Principles

**LEXLY** is an AI-assisted Indian legal retrieval system engineering a mobile-first experience (Android Jetpack Compose MVI) powered by a high-throughput Python/FastAPI backend and Supabase (`pgvector` + PostgreSQL 16). It maps unstructured, natural language incident descriptions directly to applicable statutory sections of the **Bharatiya Nyaya Sanhita, 2023 (BNS)** with cross-referenced equivalents from the **Indian Penal Code, 1860 (IPC)**.

Unlike conventional generative legal bots that hallucinate statutes or guess omitted facts, LEXLY formalizes legal analysis as a deterministic, uncertainty-reducing constraint satisfaction problem. It uses **Shannon Information Gain (IG)** to pick optimal clarification questions (`YES`, `NO`, `NOT SURE`), pruning the search space until provisions are resolved with strict database grounding and a **Zero-LLM Fast Path** for intermediate answers (<50ms compute overhead).

### Core Architectural Upgrades (Post-Review Improvements)
* **Mathematically Rigorous Information Gain**: Replaces broken 3-way disjoint partitions with overlapping outcomes (`T ∪ I` vs `F ∪ I`), properly accounting for provisions indifferent to a factual ingredient.
* **Bayesian Soft Scoring & Noise Tolerance**: Replaces brittle hard elimination with a soft posterior distribution updated via an error model ($\epsilon \approx 0.05 - 0.10$), initialized from retrieval similarity.
* **Multi-Label & Hierarchical Offence Modeling**: Evaluates complex incidents involving concurrent offences (e.g., house trespass + theft + hurt) and tracks lesser-included offence relationships (theft $\subset$ robbery $\subset$ dacoity) via a `provision_hierarchy` graph.
* **Incident-Date-Aware Statutory Selection**: Automatically bifurcates primary statutory schemes based on the incident date (Offences before **1 July 2024** resolve primary **IPC** with BNS reference; on/after resolve primary **BNS** with IPC reference).
* **Single Engine Architecture**: A pure, framework-free Python engine (`select_question`, `apply_answer`) shared by both `/analyze` and `/session/{id}/answer`—avoiding logic drift.
* **Hybrid Retrieval Safeguard**: Combines dense vector cosine similarity (OpenAI `text-embedding-3-small`, 768-dim) with PostgreSQL full-text search (`tsvector` BM25) and fact-driven candidate seeding ($k \ge 15 - 25$).
* **Evaluation & CI Benchmark Gate**: 150+ realistic gold legal scenarios tested against precision/recall/F1, false-elimination rate, and noisy simulated users ($\epsilon = 10\%$).
* **Compliance & Safety**: Indian DPDP Act 2023 adherence, PII redaction, "informational only" BCI-compliant disclaimers, and emergency crisis routing (112, 181, 1098, 1930).

---

## 2. Mathematical Specification: Corrected Information Gain & Bayesian State

### 2.1 Posterior Distribution Initialization
Instead of a uniform prior $P(P_i) = \frac{1}{|C|}$, candidate provisions $C = \{P_1, \dots, P_m\}$ retrieved from hybrid search are assigned initial probabilities using a temperature-scaled softmax over normalized hybrid retrieval scores $s_i$:

$$p_i^{(0)} = \frac{\exp(s_i / \tau)}{\sum_{j=1}^m \exp(s_j / \tau)}$$

Where $\tau \approx 0.5$ balances confident retrieval against over-concentration. The baseline entropy of the candidate pool is:

$$H(p) = - \sum_{i=1}^m p_i \log_2 p_i$$

### 2.2 Corrected Conditional Entropy Over Overlapping Partitions
A candidate question $Q$ associated with fact ingredient $F$ partitions provisions into:
- $T = \{i \in C \mid \text{provision } i \text{ requires } F = \text{TRUE}\}$
- $F_{req} = \{i \in C \mid \text{provision } i \text{ requires } F = \text{FALSE}\}$
- $I = \{i \in C \mid \text{provision } i \text{ is indifferent to } F\}$

When a user answers:
- **YES**: Provisions in $T \cup I$ remain active/supported.
- **NO**: Provisions in $F_{req} \cup I$ remain active/supported.
- **NOT SURE**: Fact is marked ignored/masked; distribution remains unchanged.

Let $q_f$ be the prior probability of fact $F$ being true (default $0.5$ or estimated from corpus base rates). The marginal probability of a user answering YES or NO is:

$$P(\text{YES}) = \sum_{i \in T} p_i + q_f \sum_{i \in I} p_i$$

$$P(\text{NO}) = 1 - P(\text{YES}) = \sum_{i \in F_{req}} p_i + (1 - q_f) \sum_{i \in I} p_i$$

For each potential answer $a \in \{\text{YES}, \text{NO}\}$, calculate the updated posterior vector $p^{(a)}$ and its entropy $H(p^{(a)})$. The expected conditional entropy is:

$$H(C \mid Q) = P(\text{YES}) H(p^{(\text{YES})}) + P(\text{NO}) H(p^{(\text{NO})})$$

The Information Gain is:

$$IG(Q) = H(p) - H(C \mid Q)$$

The engine deterministically selects:

$$Q^* = \arg\max_{Q \in \text{Unknown Facts}} IG(Q)$$

> **Mathematical Assertion**: If every active candidate provision is indifferent to fact $F$ ($|T| = 0$ and $|F_{req}| = 0$), then $P(\text{YES}) = q_f$, $p^{(\text{YES})} = p$, $p^{(\text{NO})} = p$, and $IG(Q) \equiv 0.000\text{ bits}$. A dedicated unit test asserts this invariant.

### 2.3 Bayesian Soft Evidence Update (Mistake Tolerance)
When the user submits answer $a_t \in \{\text{YES}, \text{NO}\}$ for fact $f$:

For each provision $i \in C$:
- If provision $i$ expects $f$ matching $a_t$: $p_i \leftarrow p_i \cdot (1 - \epsilon)$
- If provision $i$ contradicts $a_t$: $p_i \leftarrow p_i \cdot \epsilon$
- If provision $i$ is indifferent to $f$ or answer is $\text{NOT\_SURE}$: $p_i \leftarrow p_i$ (unchanged)

*(Noise parameter $\epsilon \approx 0.05 - 0.10$.)*

After updating, normalize probabilities: $p_i \leftarrow \frac{p_i}{\sum_j p_j}$.

### 2.4 Multi-Label Termination & Hierarchy Promotion
Instead of forcing a single winner:
1. **Multi-label Resolution**: Return all provisions with posterior probability $p_i \ge 0.15$ where all mandatory ingredients have soft confirmation.
2. **Hierarchy Rule**: Consult `provision_hierarchy` (e.g., Simple Hurt $\subset$ Grievous Hurt $\subset$ Grievous Hurt with Weapon). When multiple nodes in the same branch exceed threshold, report the highest supported level as primary and include lesser-included offences as subsidiary alternatives.
3. **Loop Termination Criteria**:
   - Top candidate probability $p_{\max} \ge 0.85$ AND no conflicting co-offence candidates with $IG > 0.1$.
   - $\max_{Q} IG(Q) < 0.10\text{ bits}$.
   - Clarification question budget reached (5–7 questions max).

---

## 3. System Architecture & End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               Android Client (Kotlin + Jetpack Compose)                         │
│  - MVI Architecture (Unidirectional State Flow)      - Material 3 Design Tokens (48dp targets)  │
│  - Offline & Process-Death Recovery (SavedState)    - Accessible Chips (Icons + High Contrast)  │
│  - Step Optimistic Locking & Idempotency Header      - Hindi & English Locale Switcher          │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                │ HTTPS REST (OpenAPI Contract)
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Gateway Service (Python 3.11+)                           │
│  ┌────────────────────────────────────────┐     ┌─────────────────────────────────────────────┐ │
│  │      POST /api/v1/analyze              │     │      POST /api/v1/session/{id}/answer       │ │
│  │  - Crisis & Emergency Router (112, etc)│     │  - Optimistic Lock Check (step == current)  │ │
│  │  - Incident Date Extraction (IPC v BNS)│     │  - Fast Path (<50ms compute)                │ │
│  │  - PII Redaction / DPDP Guardrails     │     │  - In-Memory Static Matrix (1KB RAM)        │ │
│  │  - Concurrent Embed + LLM Extraction   │     │  - Zero LLM Generative Cost                 │ │
│  │  - Hybrid Search (Vector + Full-Text)  │     │  - Undo / Replay Support                    │ │
│  └───────────────────┬────────────────────┘     └──────────────────────┬──────────────────────┘ │
│                      │                                                 │                        │
│                      └───────────────────────┬─────────────────────────┘                        │
│                                              ▼                                                  │
│                       ┌───────────────────────────────────────────────┐                         │
│                       │    Pure Python Engine (engine/core.py)        │                         │
│                       │    - select_question(state, matrix)           │                         │
│                       │    - apply_answer(state, answer, epsilon)     │                         │
│                       │    - resolve_provisions(state, hierarchy)     │                         │
│                       └──────────────────────┬────────────────────────┘                         │
└──────────────────────────────────────────────┼──────────────────────────────────────────────────┘
                                               │ asyncpg / Supabase Transaction Pooler
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                Supabase PostgreSQL 16 + pgvector                                │
│  - legal_provisions (acts, section, bns/ipc, text, procedural attributes: bailable, cognizable)  │
│  - provision_hierarchy (lesser/greater relations)   - provision_facts (pre-cached matrix)       │
│  - fact_questions (multi-locale: en, hi)            - analysis_sessions (JSONB single-row state)│
│  - session_facts (immutable audit log)              - hybrid_search_provisions() RPC            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Supabase Database Schema & Storage

Execute the following migration in Supabase. It incorporates procedural legal attributes (BNSS First Schedule), multilingual question templates, hierarchy graphs, and single-row JSONB session state.

```sql
-- Enable vector engine
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Statutory Acts
CREATE TABLE acts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(64) NOT NULL UNIQUE,
    enacted_year INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. Legal Provisions under Acts
CREATE TABLE legal_provisions (
    id SERIAL PRIMARY KEY,
    act_id INT REFERENCES acts(id) ON DELETE CASCADE,
    section_number VARCHAR(32) NOT NULL,
    bns_equivalent VARCHAR(64),
    ipc_equivalent VARCHAR(64),
    title VARCHAR(255) NOT NULL,
    statutory_text TEXT NOT NULL,
    plain_summary TEXT NOT NULL,
    punishment TEXT NOT NULL,
    -- Procedural attributes (BNSS 2023 First Schedule)
    is_cognizable BOOLEAN NOT NULL DEFAULT TRUE,
    is_bailable BOOLEAN NOT NULL DEFAULT FALSE,
    compoundable_type VARCHAR(64) NOT NULL DEFAULT 'NON_COMPOUNDABLE', -- 'COMPOUNDABLE', 'WITH_PERMISSION', 'NON_COMPOUNDABLE'
    triable_by VARCHAR(128) NOT NULL DEFAULT 'Court of Session',
    -- Embeddings & Search (OpenAI text-embedding-3-small, 768 dimensions)
    embedding vector(768),
    tsv_content tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(statutory_text, '') || ' ' || coalesce(plain_summary, ''))
    ) STORED,
    source_document VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    corpus_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    effective_from DATE NOT NULL DEFAULT '2024-07-01',
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for hybrid retrieval
CREATE INDEX idx_provisions_embedding ON legal_provisions USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_provisions_tsv ON legal_provisions USING gin (tsv_content);

-- 3. Provision Hierarchy (Lesser-Included & Aggravated Offences)
CREATE TABLE provision_hierarchy (
    id SERIAL PRIMARY KEY,
    parent_provision_id INT REFERENCES legal_provisions(id) ON DELETE CASCADE,
    child_provision_id INT REFERENCES legal_provisions(id) ON DELETE CASCADE,
    relation_type VARCHAR(32) NOT NULL, -- 'LESSER_INCLUDED', 'AGGRAVATED_FORM', 'COMPOUND_OFFENCE'
    UNIQUE(parent_provision_id, child_provision_id)
);

-- 4. Mandatory and Optional Facts per Provision
CREATE TABLE provision_facts (
    id SERIAL PRIMARY KEY,
    provision_id INT REFERENCES legal_provisions(id) ON DELETE CASCADE,
    fact_key VARCHAR(64) NOT NULL,
    expected_value VARCHAR(16) NOT NULL, -- 'TRUE' or 'FALSE'
    is_mandatory BOOLEAN DEFAULT TRUE,
    UNIQUE(provision_id, fact_key)
);
CREATE INDEX idx_provision_facts_key ON provision_facts(fact_key);

-- 5. Multilingual Inquiry Question Templates
CREATE TABLE fact_questions (
    id SERIAL PRIMARY KEY,
    fact_key VARCHAR(64) NOT NULL,
    locale VARCHAR(8) NOT NULL DEFAULT 'en', -- 'en', 'hi'
    question_text TEXT NOT NULL,
    observable_proxy_hint TEXT,
    category VARCHAR(64) NOT NULL,
    UNIQUE(fact_key, locale)
);

-- 6. User Analysis Sessions (Optimistic Locking & Single-Row State)
CREATE TABLE analysis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(128),
    initial_scenario TEXT NOT NULL,
    incident_date DATE,
    primary_legal_regime VARCHAR(16) NOT NULL DEFAULT 'BNS', -- 'BNS' or 'IPC'
    current_step INT NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS', -- 'IN_PROGRESS', 'RESOLVED', 'TERMINATED'
    -- Consolidated JSONB State for <50ms Fast Path
    state_payload JSONB NOT NULL DEFAULT '{
        "known_facts": {},
        "ignored_facts": [],
        "candidate_ids": [],
        "posterior": {},
        "audit_trail": []
    }'::jsonb,
    corpus_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
);
CREATE INDEX idx_sessions_expiry ON analysis_sessions(expires_at);

-- 7. Fact State Log (Audit Trail)
CREATE TABLE session_facts (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    fact_key VARCHAR(64) NOT NULL,
    fact_value VARCHAR(16) NOT NULL, -- 'TRUE', 'FALSE', 'UNKNOWN'
    source VARCHAR(32) NOT NULL,      -- 'INITIAL_EXTRACTION', 'USER_RESPONSE'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Hybrid Search RPC Function (Reciprocal Rank Fusion of Vector + BM25)
CREATE OR REPLACE FUNCTION hybrid_search_provisions(
    query_text text,
    query_embedding vector(768),
    match_count int DEFAULT 20,
    rrf_k int DEFAULT 60
)
RETURNS TABLE (
    id int,
    section_number varchar,
    bns_equivalent varchar,
    ipc_equivalent varchar,
    title varchar,
    statutory_text text,
    plain_summary text,
    punishment text,
    is_cognizable boolean,
    is_bailable boolean,
    compoundable_type varchar,
    triable_by varchar,
    hybrid_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_ranks AS (
        SELECT lp.id, ROW_NUMBER() OVER (ORDER BY lp.embedding <=> query_embedding) as r_rank
        FROM legal_provisions lp
        ORDER BY lp.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    text_ranks AS (
        SELECT lp.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(lp.tsv_content, plainto_tsquery('english', query_text)) DESC) as t_rank
        FROM legal_provisions lp
        WHERE lp.tsv_content @@ plainto_tsquery('english', query_text)
        LIMIT match_count * 2
    )
    SELECT
        lp.id,
        lp.section_number,
        lp.bns_equivalent,
        lp.ipc_equivalent,
        lp.title,
        lp.statutory_text,
        lp.plain_summary,
        lp.punishment,
        lp.is_cognizable,
        lp.is_bailable,
        lp.compoundable_type,
        lp.triable_by,
        COALESCE(1.0 / (rrf_k + vr.r_rank), 0.0) + COALESCE(1.0 / (rrf_k + tr.t_rank), 0.0) AS hybrid_score
    FROM legal_provisions lp
    LEFT JOIN vector_ranks vr ON lp.id = vr.id
    LEFT JOIN text_ranks tr ON lp.id = tr.id
    WHERE vr.id IS NOT NULL OR tr.id IS NOT NULL
    ORDER BY hybrid_score DESC
    LIMIT match_count;
END;
$$;
```

---

## 5. API Specification & Data Contracts

### 5.1 Endpoint 1: Initialize Analysis
* **Route:** `POST /api/v1/analyze`
* **Headers:** `Idempotency-Key: <UUID>`, `X-Device-ID: <UUID>`
* **Request:**
```json
{
  "scenario": "On 15 August 2024, my landlord broke into my apartment while I was at work and took my laptop claiming I owed rent.",
  "incident_date": "2024-08-15",
  "locale": "en"
}
```

* **Crisis Interception Response (HTTP 200 - Immediate Emergency Routing):**
*(If input contains indicators of ongoing violence, sexual offence, or child abuse)*
```json
{
  "status": "EMERGENCY_INTERCEPTION",
  "emergency_contacts": [
    {"name": "National Emergency Number", "number": "112"},
    {"name": "Women Helpline", "number": "181"},
    {"name": "Childline India", "number": "1098"},
    {"name": "Cyber Crime Helpline", "number": "1930"}
  ],
  "message": "If you or someone else is in immediate danger, please contact emergency services immediately."
}
```

* **Standard Response (HTTP 200 - Question Required):**
```json
{
  "session_id": "4a282f93-b673-455b-98b6-963e63968603",
  "step": 1,
  "status": "NEEDS_CLARIFICATION",
  "legal_regime": {
    "primary": "BNS",
    "incident_date": "2024-08-15",
    "rationale": "Offence committed after 1 July 2024 is governed by Bharatiya Nyaya Sanhita, 2023."
  },
  "extracted_facts": {
    "property_taken": "TRUE",
    "without_consent": "TRUE",
    "entry_into_dwelling": "TRUE",
    "force_used_on_person": "UNKNOWN",
    "fear_of_death_or_hurt": "UNKNOWN"
  },
  "question": {
    "question_id": "q_force_used_on_person",
    "fact_key": "force_used_on_person",
    "text": "Was any physical force or threat of immediate harm used directly against you or another person?",
    "hint": "Pushing, grabbing, holding, or brandishing a weapon counts as force.",
    "options": ["YES", "NO", "NOT_SURE"],
    "current_step": 1,
    "max_steps": 5
  },
  "disclaimer": "LEXLY provides automated statutory mapping for educational and legal research purposes only. It does not constitute legal advice."
}
```

### 5.2 Endpoint 2: Submit Clarification (Zero-LLM Fast Route)
* **Route:** `POST /api/v1/session/{session_id}/answer`
* **Request:**
```json
{
  "step": 1,
  "fact_key": "force_used_on_person",
  "answer": "NO"
}
```

* **Response (HTTP 200 - Analysis Complete):**
```json
{
  "session_id": "4a282f93-b673-455b-98b6-963e63968603",
  "step": 2,
  "status": "COMPLETED",
  "legal_regime": {
    "primary": "BNS",
    "incident_date": "2024-08-15"
  },
  "primary_provisions": [
    {
      "act": "Bharatiya Nyaya Sanhita, 2023",
      "section": "305",
      "ipc_equivalent": "Section 380 IPC",
      "title": "Theft in dwelling house, etc.",
      "confidence": 0.88,
      "matched_facts": [
        "Movable property taken dishonestly without consent",
        "Offence committed in a building used as a human dwelling",
        "Absence of physical violence prevents escalation to Robbery"
      ],
      "statutory_text": "Whoever commits theft in any building, tent or vessel, which building, tent or vessel is used as a human dwelling...",
      "punishment": "Imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
      "procedural_attributes": {
        "cognizable": true,
        "bailable": false,
        "compoundable": "NON_COMPOUNDABLE",
        "triable_by": "Judicial Magistrate of the First Class"
      },
      "source_document": "Gazette of India, Extraordinary, Part II, Section 1",
      "source_url": "https://www.indiacode.nic.in"
    }
  ],
  "co_occurring_provisions": [
    {
      "act": "Bharatiya Nyaya Sanhita, 2023",
      "section": "331",
      "ipc_equivalent": "Section 448 IPC",
      "title": "House-trespass",
      "confidence": 0.74,
      "matched_facts": ["Unlawful entry into human dwelling"]
    }
  ],
  "lesser_included_offences": [
    {
      "act": "Bharatiya Nyaya Sanhita, 2023",
      "section": "303(2)",
      "ipc_equivalent": "Section 379 IPC",
      "title": "Theft (Simple)",
      "relation": "LESSER_INCLUDED"
    }
  ],
  "general_exceptions_flag": null,
  "audit_trail": [
    {"step": 1, "action": "INITIAL_PARSE", "facts_found": 3, "entropy": 2.32},
    {"step": 2, "question": "force_used_on_person", "answer": "NO", "entropy_delta": 0.81, "p_max": 0.88}
  ],
  "disclaimer": "LEXLY provides automated statutory mapping for educational and legal research purposes only. It does not constitute legal advice."
}
```

### 5.3 Endpoint 3: Undo / Revert Last Step
* **Route:** `POST /api/v1/session/{session_id}/undo`
* **Request:** `{}`
* **Response (HTTP 200):** Returns previous step state, replaying fact states without last entry.

---

## 6. Backend Implementation Plan

### 6.1 Phase 1: Infrastructure & Static Matrix Pre-Caching
1. **Repository Layout**:
   - Monorepo with `backend/` and `android/`.
   - Setup `.env`, `Dockerfile`, `ruff.toml`, and `mypy.ini`.
2. **Database Initialization**:
   - Execute migration script in Supabase.
   - Configure Supavisor / pgBouncer connection pooling and async engine via `asyncpg`.
3. **Static Provision Matrix (`corpus_cache.py`)**:
   - At FastAPI startup (`@asynccontextmanager`), load all `provision_facts` and `provision_hierarchy` into an immutable in-memory data structure:
     ```python
     # Memory footprint: 30 provisions x 40 facts = ~1.2 KB
     PROVISION_FACTS_MATRIX: Dict[int, Dict[str, str]]
     HIERARCHY_GRAPH: Dict[int, List[Tuple[int, str]]]
     FACT_QUESTION_CATALOG: Dict[str, Dict[str, FactQuestionDTO]]
     ```
   - Zero DB queries needed on `/session/{id}/answer` for matrix lookup.

### 6.2 Phase 2: Core Pure-Python Engine (`engine/core.py`)
Implement the single, framework-free legal constraint engine:

```python
import numpy as np
from typing import Dict, List, Optional, Tuple, Set

def calculate_shannon_entropy(probabilities: np.ndarray) -> float:
    """Computes Shannon entropy H(p) = -sum(p * log2(p))."""
    p_nz = probabilities[probabilities > 1e-9]
    if len(p_nz) <= 1:
        return 0.0
    return float(-np.sum(p_nz * np.log2(p_nz)))

def evaluate_best_question(
    candidate_ids: List[int],
    current_posterior: Dict[int, float],
    known_facts: Dict[str, str],
    ignored_facts: Set[str],
    matrix: Dict[int, Dict[str, str]],
    default_q_f: float = 0.5
) -> Tuple[Optional[str], float]:
    """
    Computes Shannon Information Gain across unknown facts using overlapping
    partitions (T U I vs F U I).
    """
    p_vector = np.array([current_posterior.get(pid, 0.0) for pid in candidate_ids])
    total_p = np.sum(p_vector)
    if total_p < 1e-9:
        return None, 0.0
    p_vector = p_vector / total_p
    current_entropy = calculate_shannon_entropy(p_vector)

    # Collect unknown fact keys present across candidate provisions
    candidate_fact_keys = set()
    for pid in candidate_ids:
        candidate_fact_keys.update(matrix.get(pid, {}).keys())

    unknown_keys = candidate_fact_keys - set(known_facts.keys()) - ignored_facts
    if not unknown_keys:
        return None, 0.0

    best_gain = -1.0
    best_fact_key = None

    for fact_key in unknown_keys:
        # Partition candidate indices
        t_indices = []
        f_indices = []
        i_indices = []

        for idx, pid in enumerate(candidate_ids):
            exp = matrix.get(pid, {}).get(fact_key)
            if exp == "TRUE":
                t_indices.append(idx)
            elif exp == "FALSE":
                f_indices.append(idx)
            else:
                i_indices.append(idx)

        # Invariant: If all candidates are indifferent, IG must be 0
        if len(t_indices) == 0 and len(f_indices) == 0:
            continue

        p_yes_marginal = float(np.sum(p_vector[t_indices]) + default_q_f * np.sum(p_vector[i_indices]))
        p_no_marginal = 1.0 - p_yes_marginal

        # Compute posterior vectors for YES and NO
        p_yes_post = np.copy(p_vector)
        p_yes_post[f_indices] *= 0.05  # epsilon penalty
        p_yes_post[t_indices] *= 0.95
        if np.sum(p_yes_post) > 1e-9:
            p_yes_post /= np.sum(p_yes_post)

        p_no_post = np.copy(p_vector)
        p_no_post[t_indices] *= 0.05  # epsilon penalty
        p_no_post[f_indices] *= 0.95
        if np.sum(p_no_post) > 1e-9:
            p_no_post /= np.sum(p_no_post)

        h_cond = p_yes_marginal * calculate_shannon_entropy(p_yes_post) + \
                 p_no_marginal * calculate_shannon_entropy(p_no_post)
        gain = current_entropy - h_cond

        if gain > best_gain:
            best_gain = gain
            best_fact_key = fact_key

    return best_fact_key, max(0.0, best_gain)

def update_posterior_soft(
    candidate_ids: List[int],
    current_posterior: Dict[int, float],
    fact_key: str,
    answer: str,
    matrix: Dict[int, Dict[str, str]],
    epsilon: float = 0.08
) -> Dict[int, float]:
    """Updates provision probabilities with noise tolerance."""
    if answer == "NOT_SURE":
        return current_posterior

    updated = {}
    for pid in candidate_ids:
        p = current_posterior.get(pid, 1.0 / len(candidate_ids))
        expected = matrix.get(pid, {}).get(fact_key)
        if expected is not None:
            if expected == answer:
                p *= (1.0 - epsilon)
            else:
                p *= epsilon
        updated[pid] = p

    total = sum(updated.values())
    if total > 0:
        return {pid: val / total for pid, val in updated.items()}
    return updated
```

### 6.3 Phase 3: Intake Pipeline & Concurrency (`analyze.py`)
1. **Parallel Execution via `asyncio.gather`**:
   - `task_embed = get_embedding(scenario_text)` (OpenAI `text-embedding-3-small`, 768 dims).
   - `task_extract = extract_facts_and_date(scenario_text)` (Fast LLM structured output).
   - Saves 250–400ms sequential latency overhead.
2. **Crisis & Emergency Guardrail**:
   - RegEx & safety keyword classifier intercepting scenarios of active violence, domestic abuse, sexual harassment, or child endangerment—yielding immediate emergency helplines before legal analysis.
3. **Incident-Date Determination**:
   - Extracted date compared against `2024-07-01`.
   - Date prior to 1 July 2024 assigns `primary_legal_regime = 'IPC'`; otherwise `'BNS'`.
4. **Hybrid Retrieval Invocation**:
   - Calls `hybrid_search_provisions(query_text, query_embedding, match_count=20)`.
   - Applies initial softmax prior over RRF scores.

### 6.4 Phase 4: Zero-LLM Fast Path (`session.py`)
1. **Optimistic Locking**:
   ```sql
   UPDATE analysis_sessions 
   SET current_step = current_step + 1, state_payload = $1, updated_at = CURRENT_TIMESTAMP
   WHERE id = $2 AND current_step = $3
   RETURNING *;
   ```
   If no rows are updated, returns existing step state (idempotency against rapid double taps).
2. **In-Memory Compute**:
   - Calls `update_posterior_soft()` and `evaluate_best_question()`.
   - Execution finishes in $<10\text{ms}$ CPU time.
3. **Asynchronous Audit Log**:
   - Dispatches background write to `session_facts` without blocking the HTTP response.

---

## 7. Android Client Implementation Plan (Jetpack Compose + MVI)

### 7.1 Architecture Layers
```
presentation/
├── AnalysisUiState.kt        # InputState, InquiryState, CompletedState, EmergencyState, ErrorState
├── AnalysisUiIntent.kt       # SubmitScenario, AnswerQuestion, UndoStep, Retry, ChangeLocale
├── AnalysisViewModel.kt      # StateFlow + SavedStateHandle (process-death survival)
├── theme/                    # Material 3 Accessible Tokens (High Contrast, 48dp minimum targets)
└── components/
    ├── ScenarioInputCard.kt  # Auto-expanding field, live char count (20-2000), date picker
    ├── QuestionChipGroup.kt  # YES (Check icon), NO (Cross icon), NOT SURE (Help icon)
    ├── EmergencyBanner.kt    # One-tap dialing for 112, 181, 1098, 1930
    ├── ProvisionCard.kt      # BNS/IPC badge, procedural tags (Bailable/Cognizable), facts audit
    └── StepProgressIndicator.kt # "Question 2 of ≤5" + Undo button
domain/
├── model/                    # Clean Kotlin data classes (Provision, Regime, Audit)
└── repository/               # ILexlyRepository contract
data/
├── remote/                   # Retrofit 2 interface, OkHttp with Idempotency Interceptor
└── repository/               # LexlyRepositoryImpl with DataStore session caching
```

### 7.2 UI State Machine & Process Death Survival
```kotlin
sealed interface AnalysisUiState {
    data class InputState(
        val text: String = "",
        val incidentDate: String = "",
        val isValid: Boolean = false,
        val isLoading: Boolean = false,
        val errorMessage: String? = null
    ) : AnalysisUiState

    data class InquiryState(
        val sessionId: String,
        val currentStep: Int,
        val maxSteps: Int = 5,
        val questionText: String,
        val hintText: String?,
        val factKey: String,
        val remainingCandidates: Int,
        val isSubmitting: Boolean = false
    ) : AnalysisUiState

    data class CompletedState(
        val sessionId: String,
        val primaryRegime: String,
        val primaryProvisions: List<ProvisionMatch>,
        val coOccurringProvisions: List<ProvisionMatch>,
        val lesserOffences: List<LesserOffenceMatch>,
        val auditTrail: List<AuditStep>
    ) : AnalysisUiState

    data class EmergencyState(
        val helplines: List<EmergencyContact>,
        val advisory: String
    ) : AnalysisUiState

    data class ErrorState(val message: String, val canRetry: Boolean = true) : AnalysisUiState
}
```

### 7.3 Accessibility & UX Enhancements
- **Colorblind-Safe Design**: Chips feature explicit vector icons (Checkmark for YES, Cross for NO, Question Mark for NOT SURE) alongside color signals.
- **Touch Target**: All interactive elements maintain a minimum $48 \times 48\text{ dp}$ touch target.
- **Undo Navigation**: Top bar provides an "Undo Last Answer" action that triggers `/undo` and restores previous question state without losing progress.
- **Multilingual Support**: Header toggle between English (`en`) and Hindi (`hi`).

---

## 8. Evaluation, Quality Assurance & Benchmarking Gate (P0)

To guarantee legal accuracy and zero statutory hallucinations:

### 8.1 Gold Legal Dataset (150 Scenarios)
Curate a benchmark suite categorized into:
- 50 Simple Single-Offence Scenarios (Theft, Assault, Defamation).
- 40 Ambiguous / Boundary Scenarios (Theft vs Extortion vs Robbery; Hurt vs Grievous Hurt).
- 30 Multi-Offence Incidents (Trespass + Robbery + Hurt).
- 20 Pre-July 2024 Incidents (Asserting IPC primary mapping).
- 10 Adversarial / Vague / Hinglish Scenarios.

### 8.2 Evaluation Metrics in CI Gate
Run automated test suite on every pull request:
1. **Recall@20 Retrieval**: Target $\ge 98\%$ (correct provision present in candidate set).
2. **Final Multi-Label F1 Score**: Target $\ge 92\%$ against gold annotations.
3. **Noisy User Simulation ($\epsilon = 10\%$)**: Target $\ge 85\%$ F1 retention when 1 in 10 questions is answered incorrectly.
4. **Indifference Invariant Test**: Unit test asserting $IG(Q) \equiv 0.000$ when all candidates are indifferent.
5. **Zero Hallucination Assertion**: Check that 100% of sections, act titles, and punishment strings in responses match database rows.

---

## 9. Security, Compliance & DPDP Act 2023

1. **Client Isolation**: The Android app communicates solely with FastAPI; Supabase Service Role and LLM keys are strictly forbidden on the mobile client.
2. **Indian Digital Personal Data Protection (DPDP) Act 2023**:
   - Explicit consent checkbox on scenario intake explaining data processing for statutory lookup.
   - Client-side regex & LLM pre-prompt redaction of Aadhaar numbers, phone numbers, and full personal names.
   - Strict 24-hour TTL on session data (`expires_at` cleanup cron).
   - "Delete My Analysis History" immediate purge endpoint.
3. **Legal Disclaimer**: Bar Council of India compliant disclaimer prominently rendered on mobile intake and resolution screens stating that LEXLY is an automated research aid, not an advocate or legal advisor.

---

## 10. Revised Phased Implementation Roadmap

| Phase | Milestone | Deliverables |
| :--- | :--- | :--- |
| **Phase 0** | **Algorithm & Mathematical Design** | Pure `engine/core.py` with corrected overlapping IG formula, Bayesian soft scoring, multi-label logic, and invariant unit tests. |
| **Phase 1** | **Infrastructure & Database** | Supabase migrations (HNSW, full-text, `provision_hierarchy`, BNSS procedural columns, multilingual questions). Static matrix caching. |
| **Phase 2** | **Corpus Seeding & Gold Dataset** | Seed 30+ BNS/IPC provisions with 768-dim embeddings. Build 150 gold benchmark scenarios with lawyer/student review. |
| **Phase 3** | **FastAPI Backend Services** | Parallel intake (`asyncio.gather`), incident date router, crisis guardrails, fast-path answer endpoint with optimistic locking. |
| **Phase 4** | **Evaluation & CI Gate** | Automated eval runner, noisy user simulator, strict hallucination audit, and GitHub Actions CI workflow. |
| **Phase 5** | **Android Client (Jetpack Compose)** | Clean Architecture + MVI client, Material 3 accessible chips, process-death recovery, undo support, and bilingual UI (EN/HI). |
| **Phase 6** | **Hardening & Launch Prep** | PII redaction, DPDP Act compliance, OpenTelemetry tracing, and Docker container deployment. |

---

## Next Steps
The implementation plan is now fully upgraded with all mathematical corrections, architectural safeguards, and compliance requirements. Ready to begin execution upon your instruction.
