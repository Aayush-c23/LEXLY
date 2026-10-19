# LEXLY: Adaptive Indian Legal Analysis Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Jetpack Compose](https://img.shields.io/badge/Android-Jetpack%20Compose-3DDC84.svg)](https://developer.android.com/jetpack/compose)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20pgvector-3ECF8E.svg)](https://supabase.com/)

**LEXLY** is an AI-assisted Indian legal retrieval application for Android (Jetpack Compose MVI) powered by a high-throughput Python/FastAPI backend and Supabase (`pgvector` + PostgreSQL 16). It maps unstructured, natural language incident descriptions directly to applicable statutory sections of the **Bharatiya Nyaya Sanhita, 2023 (BNS)** with cross-referenced equivalents from the **Indian Penal Code, 1860 (IPC)**.

Unlike generative legal chatbots that hallucinate provisions or assume unstated facts, LEXLY treats legal scoping as a **deterministic constraint satisfaction problem** guided by **Shannon Information Gain**. It dynamically queries the user with single, high-leverage clarification questions (`YES`, `NO`, `NOT SURE`) to bisect the search space until provisions are resolved with strict database grounding and a **Zero-LLM Fast Path** (<15ms compute overhead).

---

## Key Architectural Principles

1. **Information-Theoretic Questioning**: Shannon entropy minimization across overlapping fact partitions ($T \cup I$ vs $F_{\text{req}} \cup I$) determines the mathematically optimal next clarification question.
2. **Bayesian Soft Scoring & Noise Tolerance**: Soft evidence updates ($\epsilon \approx 0.05 - 0.08$) ensure that confused or mistaken user answers do not irreversibly prune the correct statutory section.
3. **Zero-LLM Fast Path**: Intermediate answers update in-memory state and recompute entropy purely in RAM, bypassing generative LLM costs, rate limits, and latency.
4. **Incident-Date-Aware Statutory Selection**: Offences committed before **1 July 2024** resolve primary **IPC** sections with BNS cross-references; offences on or after resolve primary **BNS** with IPC equivalents.
5. **Strict Source Grounding**: Results cite directly from gazette statutory provisions in Supabase; zero hallucinated sections, nonexistent fines, or invented punishments.
6. **Unidirectional State Flow (MVI)**: Android client strictly isolates state mutations across configuration changes and process death using `SavedStateHandle`.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│               Android Client (Jetpack Compose MVI)             │
│   Material 3 • Accessible Chips • StateFlow • Hilt • Retrofit  │
└───────────────────────────────┬────────────────────────────────┘
                                │ HTTPS REST / JSON
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Gateway                      │
├───────────────────────────────┬────────────────────────────────┤
│       Initial Pipeline        │      Zero-LLM Fast Path        │
│   - Emergency Router (112)    │   - Optimistic state lock      │
│   - Date & Regime Selector    │   - Bayesian soft scoring      │
│   - Parallel Embedding (768d) │   - Shannon Entropy Engine     │
│   - PII Redaction             │   - <15ms in-memory compute    │
└───────────────┬───────────────┴────────────────┬───────────────┘
                │                                │
                ▼                                ▼
┌────────────────────────────────────────────────────────────────┐
│               Supabase PostgreSQL 16 + pgvector               │
│   - legal_provisions (768-dim HNSW index + full-text BM25)     │
│   - acts, provision_facts, provision_hierarchy                 │
│   - fact_questions (Bilingual EN / HI)                         │
│   - analysis_sessions (JSONB single-row state + 24h TTL)       │
└────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
LEXLY/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings & environment validation
│   │   │   └── database.py           # asyncpg connection pool with pgbouncer support
│   │   ├── engine/
│   │   │   └── corpus_cache.py       # Zero-latency in-memory statutory matrix cache
│   │   ├── scripts/
│   │   │   ├── corpus_data.py        # Statutory provisions, acts, bilingual questions
│   │   │   └── seed_data.py          # 768-dim vector ingestion via Google GenAI
│   │   └── main.py                   # FastAPI app, lifespan manager & /health route
│   ├── tests/
│   │   ├── gold_dataset.json         # 25 benchmark gold legal scenarios
│   │   └── test_infra.py             # Infrastructure & cache unit tests
│   ├── .env.example                  # Backend environment template
│   └── requirements.txt              # Production Python dependencies
├── engine/
│   ├── __init__.py
│   └── core.py                       # Pure Python Shannon Entropy & Bayesian engine
├── tests/
│   └── test_core.py                  # Pytest mathematical invariants & entropy tests
├── android/
│   └── local.properties.example      # Android SDK & API base URL template
├── implementation_plan.md            # Complete architecture & mathematical design doc
├── SPRINT_CHECKLIST.md               # Sprint-by-sprint backlog & ticket assignments
├── LICENSE                           # MIT Open Source License
├── .gitignore                        # Universal bulletproof gitignore
└── README.md
```

---

## Getting Started

### Prerequisites
- **Python 3.11+** installed.
- **Supabase Account / PostgreSQL 16** with `pgvector` extension enabled.
- **Google Gemini API Key** (for 768-dim embeddings via `gemini-embedding-001` or `text-embedding-004`).
- **Android Studio Ladybug (2024.2+)** & **JDK 17+** (for Android client).

---

### Backend Setup (FastAPI)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/LEXLY.git
   cd LEXLY
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables**:
   Copy `backend/.env.example` to `backend/.env` (or root `.env`):
   ```bash
   cp backend/.env.example backend/.env
   ```
   Edit `backend/.env` and supply:
   - `DATABASE_URL`: Your Supabase transaction pooler URL (e.g., `postgresql://postgres.[ref]:[PASSWORD]@[host]:6543/postgres`).
   - `GEMINI_API_KEY`: Your Google AI Studio API key.

5. **Seed the Statutory Corpus & Generate 768-dim Embeddings**:
   ```bash
   python -m backend.app.scripts.seed_data
   ```
   *This seeds the Acts, 32 bilingual question templates (EN/HI), 20 high-precision BNS/IPC legal provisions with 768-dim dense vectors, and the provision hierarchy graph.*

6. **Run Unit Tests**:
   ```bash
   python -m pytest tests/test_core.py backend/tests/test_infra.py -v
   ```

7. **Start the FastAPI Server**:
   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Swagger Documentation: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - Health & Cache Status: [http://localhost:8000/health](http://localhost:8000/health)

---

### Android Client Setup (Jetpack Compose)

1. Open the `android/` directory in **Android Studio**.
2. Copy `android/local.properties.example` to `android/local.properties`:
   ```properties
   sdk.dir=C\:\\Users\\<YOUR_USER>\\AppData\\Local\\Android\\Sdk
   LEXLY_API_BASE_URL=http://10.0.2.2:8000/api/v1
   ```
   *(Note: `10.0.2.2` routes from the Android Emulator to localhost on your development machine).*
3. Sync Gradle and run the application on an emulator (API 34+) or physical Android device.

---

## Database Schema & Vector Search Setup

If initializing a fresh Supabase database, execute the following SQL in the **Supabase SQL Editor**:

```sql
-- Enable Vector & Trigram extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Reciprocal Rank Fusion Hybrid Search Function
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

## Evaluation Benchmark & Quality Gate

LEXLY includes a 25-scenario gold test dataset located at [`backend/tests/gold_dataset.json`](backend/tests/gold_dataset.json) covering:
- **Body Offences**: Simple Hurt (115(2)), Grievous Hurt (117(2)), Weapon Hurt (118), Provocation (122), Restraint/Confinement (126/127), Modesty (74).
- **Property Offences**: Theft (303(2)), Dwelling Theft (305), Snatching (304(2)), Extortion (308(2)), Robbery (309), Dacoity (310(2)), House-Trespass (331(1)).
- **Temporal Verification**: Pre-July 2024 incidents asserting primary IPC mapping.
- **Multi-Offence Scenarios**: Concurrent offences (e.g., house-trespass + theft + hurt).

---

## Contributing & Development Workflow

1. Check [`SPRINT_CHECKLIST.md`](SPRINT_CHECKLIST.md) for available tickets across Backend (`BE-xxx`), Android (`AND-xxx`), and QA (`QA-xxx`).
2. Create a feature branch:
   ```bash
   git checkout -b feature/BE-302-parallel-intake
   ```
3. Commit with semantic messages:
   ```bash
   git commit -m "feat(api): implement parallel intake with asyncio.gather"
   ```
4. Verify all tests pass before opening a Pull Request:
   ```bash
   python -m pytest tests/test_core.py backend/tests/test_infra.py -v
   ```

---

## Legal & Compliance Disclaimer

LEXLY provides automated statutory mapping for legal research and educational reference only. Under the Bar Council of India rules, LEXLY does not act as an advocate, solicit clients, or provide formal legal advice. If in immediate danger, please dial **112** (National Emergency Helpline) or **181** (Women Helpline).

---

## License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
