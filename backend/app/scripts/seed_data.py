"""
Database Seeding Script for Statutory Corpus (Phase 2).

Reads structured statutory data from corpus_data.py, generates 768-dimensional
dense vector embeddings using Google GenAI SDK (gemini-embedding-001 with output_dimensionality=768),
and seeds Supabase PostgreSQL database tables:
- acts
- fact_questions
- legal_provisions
- provision_facts
- provision_hierarchy
"""

import asyncio
import logging
from typing import List
import asyncpg
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.scripts.corpus_data import (
    ACTS_DATA,
    FACT_QUESTIONS_DATA,
    HIERARCHY_DATA,
    PROVISIONS_DATA,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lexly.seed_data")

# Embedding model configuration
EMBEDDING_MODEL = "gemini-embedding-001"
TARGET_DIMENSIONS = 768


def get_embedding(client: genai.Client, text: str) -> List[float]:
    """
    Generates a 768-dimensional embedding for the provided text
    using Google GenAI gemini-embedding-001 with output_dimensionality=768.
    """
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=TARGET_DIMENSIONS),
    )
    if response.embeddings and len(response.embeddings) > 0:
        return list(response.embeddings[0].values)
    elif hasattr(response, "embedding") and response.embedding:
        return list(response.embedding.values)
    else:
        raise ValueError(f"Could not retrieve embedding values from Gemini response: {response}")


async def seed_database() -> None:
    """
    Asynchronously seeds Acts, Fact Questions, Provisions (with vectors),
    Provision Facts, and Provision Hierarchy into the database.
    """
    logger.info("Initializing Google GenAI client...")
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in settings or environment!")

    genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

    logger.info("Connecting to Supabase PostgreSQL database...")
    conn = await asyncpg.connect(settings.DATABASE_URL, statement_cache_size=0)

    try:
        # -------------------------------------------------------------
        # 0. Ensure schema compatibility (add columns if not present)
        # -------------------------------------------------------------
        logger.info("Checking and adjusting schema migrations if needed...")
        
        # Check if fact_questions has locale
        fq_cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='fact_questions';"
        )
        fq_col_names = [r["column_name"] for r in fq_cols]
        if "locale" not in fq_col_names:
            logger.info("Adding 'locale' and 'observable_proxy_hint' columns to fact_questions...")
            # Drop old single-column primary key to allow composite (fact_key, locale)
            await conn.execute("ALTER TABLE fact_questions DROP CONSTRAINT IF EXISTS fact_questions_pkey CASCADE;")
            await conn.execute("ALTER TABLE fact_questions ADD COLUMN IF NOT EXISTS locale VARCHAR(8) DEFAULT 'en';")
            await conn.execute("ALTER TABLE fact_questions ADD COLUMN IF NOT EXISTS observable_proxy_hint TEXT;")
            await conn.execute("ALTER TABLE fact_questions ADD PRIMARY KEY (fact_key, locale);")

        # Check if legal_provisions has procedural attributes
        lp_cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='legal_provisions';"
        )
        lp_col_names = [r["column_name"] for r in lp_cols]
        if "plain_summary" not in lp_col_names:
            await conn.execute("ALTER TABLE legal_provisions ADD COLUMN IF NOT EXISTS plain_summary TEXT;")
        if "bns_equivalent" not in lp_col_names:
            await conn.execute("ALTER TABLE legal_provisions ADD COLUMN IF NOT EXISTS bns_equivalent VARCHAR(64);")
        if "is_cognizable" not in lp_col_names:
            await conn.execute("ALTER TABLE legal_provisions ADD COLUMN IF NOT EXISTS is_cognizable BOOLEAN DEFAULT TRUE;")
        if "is_bailable" not in lp_col_names:
            await conn.execute("ALTER TABLE legal_provisions ADD COLUMN IF NOT EXISTS is_bailable BOOLEAN DEFAULT FALSE;")
        if "compoundable_type" not in lp_col_names:
            await conn.execute("ALTER TABLE legal_provisions ADD COLUMN IF NOT EXISTS compoundable_type VARCHAR(64) DEFAULT 'NON_COMPOUNDABLE';")
        if "triable_by" not in lp_col_names:
            await conn.execute("ALTER TABLE legal_provisions ADD COLUMN IF NOT EXISTS triable_by VARCHAR(128) DEFAULT 'Any Magistrate';")

        # Create provision_hierarchy table if not exists
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_hierarchy (
                id SERIAL PRIMARY KEY,
                parent_provision_id INT REFERENCES legal_provisions(id) ON DELETE CASCADE,
                child_provision_id INT REFERENCES legal_provisions(id) ON DELETE CASCADE,
                relation_type VARCHAR(32) NOT NULL,
                UNIQUE(parent_provision_id, child_provision_id)
            );
            """
        )

        # -------------------------------------------------------------
        # 1. Seed Acts
        # -------------------------------------------------------------
        logger.info("Seeding statutory Acts...")
        act_id_map = {}
        for act in ACTS_DATA:
            row = await conn.fetchrow(
                """
                INSERT INTO acts (name, short_name, enacted_year, is_active)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (short_name) DO UPDATE 
                SET name = EXCLUDED.name, enacted_year = EXCLUDED.enacted_year, is_active = EXCLUDED.is_active
                RETURNING id, short_name;
                """,
                act["name"],
                act["short_name"],
                act["enacted_year"],
                act["is_active"],
            )
            act_id_map[row["short_name"]] = row["id"]

        logger.info(f"Acts seeded successfully: {act_id_map}")

        # -------------------------------------------------------------
        # 2. Seed Fact Questions (EN & HI)
        # -------------------------------------------------------------
        logger.info(f"Seeding {len(FACT_QUESTIONS_DATA)} multilingual fact question templates...")
        for q in FACT_QUESTIONS_DATA:
            await conn.execute(
                """
                INSERT INTO fact_questions (fact_key, locale, question_text, observable_proxy_hint, category)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (fact_key, locale) DO UPDATE
                SET question_text = EXCLUDED.question_text,
                    observable_proxy_hint = EXCLUDED.observable_proxy_hint,
                    category = EXCLUDED.category;
                """,
                q["fact_key"],
                q["locale"],
                q["question_text"],
                q.get("observable_proxy_hint", ""),
                q["category"],
            )

        logger.info("Fact questions catalog seeded.")

        # -------------------------------------------------------------
        # 3. Seed Legal Provisions & Compute Embeddings
        # -------------------------------------------------------------
        logger.info(f"Computing embeddings and seeding {len(PROVISIONS_DATA)} legal provisions...")
        bns_act_id = act_id_map["BNS"]
        provision_id_map = {}

        for p in PROVISIONS_DATA:
            sec_num = p["section_number"]
            # Embedding content: combination of title, plain summary, and statutory text
            embed_text = f"{p['title']}. {p['plain_summary']} Statutory Definition: {p['statutory_text']}"
            
            logger.info(f"Generating 768-dim embedding for Section {sec_num} ({p['title']})...")
            vector_values = get_embedding(genai_client, embed_text)
            vector_str = f"[{','.join(str(v) for v in vector_values)}]"

            # Check if provision already exists
            existing = await conn.fetchrow(
                "SELECT id FROM legal_provisions WHERE act_id = $1 AND section_number = $2;",
                bns_act_id,
                sec_num,
            )

            if existing:
                pid = existing["id"]
                await conn.execute(
                    """
                    UPDATE legal_provisions
                    SET title = $1, statutory_text = $2, plain_summary = $3, punishment = $4,
                        ipc_equivalent = $5, bns_equivalent = $6, is_cognizable = $7,
                        is_bailable = $8, compoundable_type = $9, triable_by = $10,
                        embedding = $11::vector
                    WHERE id = $12;
                    """,
                    p["title"],
                    p["statutory_text"],
                    p["plain_summary"],
                    p["punishment"],
                    p["ipc_equivalent"],
                    p.get("bns_equivalent", f"Section {sec_num} BNS"),
                    p["is_cognizable"],
                    p["is_bailable"],
                    p["compoundable_type"],
                    p["triable_by"],
                    vector_str,
                    pid,
                )
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO legal_provisions (
                        act_id, section_number, bns_equivalent, ipc_equivalent, title,
                        statutory_text, plain_summary, punishment, is_cognizable, is_bailable,
                        compoundable_type, triable_by, embedding, source_document, source_url
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::vector, $14, $15)
                    RETURNING id;
                    """,
                    bns_act_id,
                    sec_num,
                    p.get("bns_equivalent", f"Section {sec_num} BNS"),
                    p["ipc_equivalent"],
                    p["title"],
                    p["statutory_text"],
                    p["plain_summary"],
                    p["punishment"],
                    p["is_cognizable"],
                    p["is_bailable"],
                    p["compoundable_type"],
                    p["triable_by"],
                    vector_str,
                    "Gazette of India, Extraordinary, Part II, Section 1",
                    "https://www.indiacode.nic.in",
                )
                pid = row["id"]

            provision_id_map[sec_num] = pid

            # ---------------------------------------------------------
            # 4. Seed Provision Facts
            # ---------------------------------------------------------
            for f_key, exp_val in p["facts"].items():
                await conn.execute(
                    """
                    INSERT INTO provision_facts (provision_id, fact_key, expected_value, is_mandatory)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (provision_id, fact_key) DO UPDATE
                    SET expected_value = EXCLUDED.expected_value;
                    """,
                    pid,
                    f_key,
                    exp_val,
                    True,
                )

        logger.info(f"Seeded {len(provision_id_map)} legal provisions and their fact ingredients.")

        # -------------------------------------------------------------
        # 5. Seed Provision Hierarchy
        # -------------------------------------------------------------
        logger.info(f"Seeding {len(HIERARCHY_DATA)} hierarchy relationships...")
        for h in HIERARCHY_DATA:
            p_sec = h["parent_section"]
            c_sec = h["child_section"]
            if p_sec in provision_id_map and c_sec in provision_id_map:
                parent_id = provision_id_map[p_sec]
                child_id = provision_id_map[c_sec]
                await conn.execute(
                    """
                    INSERT INTO provision_hierarchy (parent_provision_id, child_provision_id, relation_type)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (parent_provision_id, child_provision_id) DO UPDATE
                    SET relation_type = EXCLUDED.relation_type;
                    """,
                    parent_id,
                    child_id,
                    h["relation_type"],
                )
            else:
                logger.warning(f"Could not map hierarchy for {p_sec} -> {c_sec}")

        logger.info("Database seeding completed successfully!")

    finally:
        await conn.close()
        logger.info("Database connection closed.")


def main():
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
