# LEXLY: Engineering Sprint Backlog & Implementation Checklist

> **Target System:** Adaptive Indian Legal Analysis Assistant  
> **Architecture:** Android Client (Jetpack Compose MVI) + Backend Gateway (FastAPI / asyncpg) + Vector Database (Supabase `pgvector` PostgreSQL 16) + Pure Mathematical Constraint Engine (`numpy`)  
> **Status Overview:**
> - [x] **Phase 0:** Mathematical Engine & Information Gain Invariants (`engine/core.py`, `tests/test_core.py`)
> - [x] **Phase 1:** Async Infrastructure, Pooler & In-Memory Corpus Cache (`corpus_cache.py`, `database.py`, `main.py`)
> - [x] **Phase 2:** Corpus Seeding (BNS/IPC, bilingual questions, 768-dim Gemini embeddings, 25 gold benchmark cases)
> - [ ] **Phase 3:** FastAPI REST Service & Engine Pipeline Integration
> - [ ] **Phase 4:** Evaluation Runner, CI Gate & Noisy User Simulation
> - [ ] **Phase 5:** Android Jetpack Compose MVI Client
> - [ ] **Phase 6:** Hardening, Compliance (DPDP Act 2023) & Launch Preparation

---

## Track 1: FastAPI Backend & Engine Integration (Phase 3)

### Ticket BE-301: Crisis & Emergency Interception Middleware
- [ ] **Task**: Implement pre-routing emergency classifier in `backend/app/api/v1/endpoints/analyze.py`.
- **Technical Context**:
  - Scenarios involving immediate threats to life, active domestic violence, sexual assault in progress, or crimes against children must trigger emergency interception before statutory analysis.
- **Implementation Details**:
  - Regex & keyword matchers detecting emergency urgency tokens (e.g., `"kidnapped my child right now"`, `"threatened to kill me in 10 minutes"`, `"domestic violence emergency"`).
  - Fast short-circuit response returning verified Indian statutory emergency helplines:
    - National Emergency: `112`
    - Women Helpline: `181`
    - Childline: `1098`
    - National Cyber Crime Helpline: `1930`
- **Acceptance Criteria**:
  - Given an emergency scenario, response status is `EMERGENCY_INTERCEPTION` with HTTP 200 within $< 15\text{ms}$.
  - Zero DB writes or vector calls executed on intercepted emergencies.

---

### Ticket BE-302: Parallel Intake Pipeline (`POST /api/v1/analyze`)
- [ ] **Task**: Build the scenario ingestion endpoint orchestrating concurrent vector embedding and structured LLM extraction.
- **Contract**:
  - **Route**: `POST /api/v1/analyze`
  - **Headers**: `Idempotency-Key: UUID`, `X-Device-ID: String`
  - **Request Body**:
    ```json
    {
      "scenario": "My landlord broke into my flat yesterday while I was at work and took my laptop claiming I owed rent.",
      "incident_date": "2024-08-15",
      "locale": "en"
    }
    ```
- **Implementation Details**:
  1. **Character Validation**: Enforce $20 \le \text{len(scenario)} \le 2000$.
  2. **PII Masking**: Strip phone numbers, 12-digit Aadhaar sequences, and proper names prior to LLM submission.
  3. **Incident Date & Legal Regime**:
     - Extract or parse `incident_date`.
     - Compare against cutoff `2024-07-01`.
     - If `< 2024-07-01`, set `primary_legal_regime = 'IPC'`; otherwise `'BNS'`.
  4. **Concurrent Execution via `asyncio.gather`**:
     - `task_embed`: Call Gemini embedding model (`gemini-embedding-001`, `output_dimensionality=768`).
     - `task_extract`: Call Gemini structured output generating tri-state fact dictionary (`"TRUE"`, `"FALSE"`, `"UNKNOWN"`).
  5. **Hybrid Candidate Retrieval**:
     - Query Supabase vector similarity (`embedding <=> query_vector`) alongside PostgreSQL full-text search (`ts_rank_cd`), fetching top 15–20 candidate provisions.
  6. **Initial Posterior Initialization**:
     - Apply temperature-scaled softmax ($\tau \approx 0.5$) over candidate cosine similarities to initialize $p^{(0)}$.
     - Apply soft updates for extracted known facts using `update_posterior_soft`.
  7. **Decision Gate**:
     - Call `evaluate_best_question` over candidates using in-memory `PROVISION_FACTS_MATRIX`.
     - Persist new session row in `analysis_sessions` with initial JSONB state.
- **Acceptance Criteria**:
  - P95 response latency $< 2.2\text{s}$.
  - Returns `NEEDS_CLARIFICATION` with first question or `COMPLETED` if candidate pool is resolved ($p_{\max} \ge 0.85$ or $IG < 0.1$).

---

### Ticket BE-303: Zero-LLM Fast-Path Answer Endpoint (`POST /api/v1/session/{id}/answer`)
- [ ] **Task**: Build high-throughput, in-memory clarification question resolution endpoint.
- **Contract**:
  - **Route**: `POST /api/v1/session/{session_id}/answer`
  - **Request Body**:
    ```json
    {
      "step": 1,
      "fact_key": "force_used_on_person",
      "answer": "NO"
    }
    ```
- **Implementation Details**:
  1. **Optimistic Locking**:
     - Execute atomic conditional update:
       ```sql
       UPDATE analysis_sessions 
       SET current_step = current_step + 1, updated_at = CURRENT_TIMESTAMP
       WHERE id = $session_id AND current_step = $step
       RETURNING state_payload;
       ```
     - If no rows affected (client replay or double-tap), return previous step state idempotently.
  2. **In-Memory Bayesian Update**:
     - If `answer == "NOT_SURE"`, add `fact_key` to `ignored_facts` and maintain distribution.
     - Else, call `update_posterior_soft(candidate_ids, posterior, fact_key, answer, PROVISION_FACTS_MATRIX, epsilon=0.08)`.
  3. **Stopping Conditions Check**:
     - Compute maximum candidate posterior $p_{\max} = \max(p_i)$.
     - Check: Is $p_{\max} \ge 0.85$, or current step $\ge 5$, or $\max IG < 0.10\text{ bits}$?
     - **If YES**: Return `status: "COMPLETED"` with primary grounded provisions, procedural tags, and lesser-included offences resolved via in-memory `HIERARCHY_GRAPH`.
     - **If NO**: Call `evaluate_best_question`, fetch bilingual question from in-memory `FACT_QUESTION_CATALOG`, and return `status: "NEEDS_CLARIFICATION"`.
  4. **Asynchronous Audit Logging**:
     - Fire-and-forget background insert to `session_facts` for audit trail persistence.
- **Acceptance Criteria**:
  - Backend compute processing overhead $< 15\text{ms}$ (excluding network transit).
  - P95 endpoint latency $< 80\text{ms}$.
  - Zero calls to generative LLM models.

---

### Ticket BE-304: Session Undo & Revert Endpoint (`POST /api/v1/session/{id}/undo`)
- [ ] **Task**: Implement deterministic state rollback for users who make a mistake or change their mind.
- **Implementation Details**:
  - Read session state history from `state_payload["audit_trail"]`.
  - Revert state to step $N-1$, removing the last answered fact.
  - Re-evaluate candidate distribution and return the previous question.
- **Acceptance Criteria**:
  - Reverts question prompt accurately without corrupting session integrity.

---

### Ticket BE-305: Ephemeral Scrubber / DPDP Session Purge (`DELETE /api/v1/session/{id}`)
- [ ] **Task**: Comply with Indian DPDP Act 2023 right-to-erasure requirements.
- **Implementation Details**:
  - Permanent cascade deletion of `analysis_sessions` and `session_facts` for the specified session ID.
  - Setup background scheduled task to automatically purge sessions where `expires_at < NOW()` (24-hour TTL).
- **Acceptance Criteria**:
  - Query confirms deletion of all associated session records and vectors within $< 50\text{ms}$.

---

## Track 2: Android Jetpack Compose Client (Phase 5)

### Ticket AND-501: Architecture, DI & Network Layer
- [ ] **Task**: Set up Kotlin Clean Architecture + MVI framework with Hilt, Retrofit 2, and OkHttp 3.
- **Technical Stack**:
  - Kotlin 2.0+, Jetpack Compose, Material 3, Hilt, Retrofit 2, Kotlinx Serialization, DataStore.
- **Implementation Details**:
  - Create `LexlyApiService` interface with suspend functions for `/analyze`, `/answer`, `/undo`, `/session/{id}`.
  - Configure `OkHttpClient` with 15s timeouts and automatic `Idempotency-Key` header injection.
  - Define domain models: `ProvisionMatch`, `ProceduralAttributes`, `ClarificationQuestion`, `LegalRegime`, `AuditTrace`.
  - Provide `LexlyRepository` and `LexlyRepositoryImpl`.
- **Acceptance Criteria**:
  - Unit tests verify Retrofit DTO parsing and error handling for 4xx/5xx responses.

---

### Ticket AND-502: MVI ViewModel & Process-Death Survival
- [ ] **Task**: Implement `AnalysisViewModel` with `StateFlow` and `SavedStateHandle`.
- **State Machine Definition**:
  ```kotlin
  sealed interface AnalysisUiState {
      data class InputState(val text: String = "", val incidentDate: String = "", val isValid: Boolean = false, val isLoading: Boolean = false, val errorMessage: String? = null) : AnalysisUiState
      data class InquiryState(val sessionId: String, val currentStep: Int, val maxSteps: Int = 5, val questionText: String, val hintText: String?, val factKey: String, val remainingCandidates: Int, val isSubmitting: Boolean = false) : AnalysisUiState
      data class CompletedState(val sessionId: String, val primaryRegime: String, val primaryProvisions: List<ProvisionMatch>, val coOccurringProvisions: List<ProvisionMatch>, val lesserOffences: List<LesserOffenceMatch>, val auditTrail: List<AuditStep>) : AnalysisUiState
      data class EmergencyState(val helplines: List<EmergencyContact>, val advisory: String) : AnalysisUiState
      data class ErrorState(val message: String, val canRetry: Boolean = true) : AnalysisUiState
  }
  ```
- **Acceptance Criteria**:
  - Survives activity recreation and Android OS process death; restores active inquiry step using saved `sessionId` and step index.

---

### Ticket AND-503: Scenario Input Screen
- [ ] **Task**: Build Material 3 scenario intake interface.
- **UI Components**:
  - `OutlinedTextField` with dynamic auto-expand (min 4 lines, max 10 lines).
  - Real-time character counter indicator ($20 - 2000$ characters) with color validation.
  - Date Picker dialog defaulting to current date with clear indication of IPC vs BNS cutoff.
  - Language toggle chip (`English` / `हिंदी`).
  - Bar Council of India informational disclaimer footer.
  - Pulsing shimmer loading indicator during scenario embedding and LLM fact extraction.
- **Acceptance Criteria**:
  - Submit button disabled until character count $\ge 20$.
  - Smooth animation transition to Inquiry Screen upon successful submission.

---

### Ticket AND-504: Dynamic Inquiry Screen with Accessible Chips
- [ ] **Task**: Build interactive question resolution screen with colorblind-safe chips.
- **UI Components**:
  - Progress tracker: "Question X of $\le$5" with animated linear progress bar.
  - Active candidate count badge: "Filtering across X statutory sections".
  - Question card displaying `questionText` in prominent typography, followed by `observable_proxy_hint` in muted italics.
  - **Tri-State Action Chip Group**:
    - `YES`: Green tint, Checkmark vector icon, minimum $48\text{dp}$ touch target.
    - `NO`: Red tint, Close/Cross vector icon, minimum $48\text{dp}$ touch target.
    - `NOT SURE`: Neutral outline, Question mark vector icon, minimum $48\text{dp}$ touch target.
  - Top app bar "Undo" button enabling immediate rollback of previous answer.
- **Acceptance Criteria**:
  - Visual feedback on tap with debounce preventing multiple simultaneous submissions.
  - Screen reader (TalkBack) announcements configured for question text and chip states.

---

### Ticket AND-505: Legal Resolution & Audit Screen
- [ ] **Task**: Build comprehensive result presentation screen with expandable cards.
- **UI Components**:
  - Legal Regime Banner: Prominent chip indicating whether primary statute is **BNS, 2023** or **IPC, 1860** based on incident date.
  - `ProvisionResultCard`:
    - Section Number, Act Name, and cross-referenced IPC/BNS badge.
    - Procedural Tags: Bailable (Green) / Non-Bailable (Red), Cognizable (Amber) / Non-Cognizable (Blue), Court Triable badge.
    - Punishment breakdown box.
    - Matched facts checklist with green verification bullets.
  - `LesserIncludedSection`: Nested accordion showing subsidiary charges.
  - `AuditTrailCard`: Collapsible view detailing entropy reduction steps ($\Delta IG$, posterior shifts).
  - Share / Export action button (generating clean text summary for legal consultation).
- **Acceptance Criteria**:
  - All statutory citations link directly to verified India Code sources.
  - Cards support smooth expand/collapse animations.

---

## Track 3: Evaluation Gate & Compliance (Phase 4 & 6)

### Ticket QA-401: Gold Dataset Evaluation Harness
- [ ] **Task**: Build automated pytest benchmark runner executing against `backend/tests/gold_dataset.json`.
- **Target Metrics**:
  - **Retrieval Recall@20**: $\ge 98\%$ of target provisions retrieved in initial candidate pool.
  - **Multi-Label Resolution F1**: $\ge 92\%$ accuracy on final provisions across all 25 gold scenarios.
  - **Average Question Efficiency**: Target mean question count $\le 3.2$ questions to resolution.
- **Acceptance Criteria**:
  - Automated test runs in CI; fails build if F1 score drops below $90\%$.

---

### Ticket QA-402: Noisy User Simulator ($\epsilon = 0.10$)
- [ ] **Task**: Validate Bayesian soft scoring fault-tolerance against mistaken user answers.
- **Implementation Details**:
  - Script that simulates user responses to questions.
  - Injects $10\%$ random incorrect answers (`YES` instead of `NO` or vice versa).
  - Asserts that soft posterior scoring avoids fatal early pruning and maintains $\ge 85\%$ F1 recovery.
- **Acceptance Criteria**:
  - Soft Bayesian scoring demonstrates $> 30\%$ higher accuracy than hard-elimination filtering under noise.

---

### Ticket SEC-601: Indian DPDP Act 2023 & Security Audit
- [ ] **Task**: Enforce regulatory compliance, data minimization, and privacy guardrails.
- **Checklist**:
  - [ ] Client-side PII scrubber active for phone numbers, emails, and Aadhaar numbers.
  - [ ] Mandatory explicit user consent dialog shown before first scenario submission.
  - [ ] 24-hour TTL expiration enforced on Supabase `analysis_sessions`.
  - [ ] Zero storage of IP addresses or raw device identifiers in persistent logs.
  - [ ] Zero transmission of Supabase service-role key or Gemini API key to Android APK.
- **Acceptance Criteria**:
  - Security audit passes; static code analysis confirms no secret leakage in client bundle.

---

## Sprint Roadmap & Ticket Assignment Summary

| Sprint | Focus Track | Assigned Tickets | Key Milestone |
| :--- | :--- | :--- | :--- |
| **Sprint 1** | Backend Gateway | `BE-301`, `BE-302`, `BE-303`, `BE-304`, `BE-305` | Full REST API operational with sub-50ms Fast Path answer evaluation |
| **Sprint 2** | Evaluation & QA | `QA-401`, `QA-402` | Automated CI evaluation gate passing $\ge 92\%$ F1 benchmark |
| **Sprint 3** | Android Core UI | `AND-501`, `AND-502`, `AND-503`, `AND-504` | Working mobile input and dynamic question resolution flow |
| **Sprint 4** | Resolution & Polishing | `AND-505`, `SEC-601` | Expandable provision cards, bilingual support, DPDP compliance, APK release |
