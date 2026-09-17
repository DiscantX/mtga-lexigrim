# Developer & AI Agent Guidelines (`AGENTS.md`)

Welcome to the **MTG Expert** codebase. This document provides core guidelines, environment instructions, and architectural constraints for AI agents and human developers working on this project.

---

## 1. Project Context & Current Phase

- **Long-Term Goal**: Create an AI expert on Magic: The Gathering capable of deckbuilding, synergy analysis, rules interrogation, and meta-game understanding.
- **Current Phase**: **Phase 1 (Data Ingestion & Vector Search)** is complete and stable. **Phase 2 (AI Integration / Chatbot / Agnostic LLM Provider Middleware)** is planned next. Do not start Phase 2 until Phase 1 is verified stable.

---

## 2. Environment & Execution Standards

- **Virtual Environment**: All Python commands and script executions must use the virtual environment located at `.venv` (e.g., `.venv\Scripts\python` on Windows or `.venv/bin/python` on Unix).
- **No Global Installations**: Dependencies must be managed within `.venv`.

---

## 3. Code Quality & Architectural Rules

1. **Object-Oriented, Agnostic, & Modular**: Maintain clean separation of concerns. Respect abstract base interfaces ([`BaseVectorStore`](vectorstores/base.py:230) in [`vectorstores/base.py`](vectorstores/base.py:1) and [`BaseEmbeddingService`](embeddings/base.py:51) in [`embeddings/base.py`](embeddings/base.py:1)).
2. **No Mega Scripts**: If any module or script grows too long, refactor it into smaller, single-responsibility modules.
3. **The "Rounding" Principle**: Adhere strictly to: *"Carry the full value until the final display operation (do rounding/truncation last)."* Never discard or truncate data prematurely during intermediate processing steps.
4. **Direct Streaming for Ingestion**: Do not reintroduce heavy ORM models, Pydantic validation, or dataclasses into bulk ingestion streams. Stream raw JSON dicts via [`JsonlStreamReader`](core/streaming.py:116) to maintain flat memory usage.
5. **Human Readability & Docstrings**: Ensure all classes and functions include clear docstrings and adhere to Python typing standards.

---

## 4. Documentation & Archiving Rules

- Keep formal system documentation updated ([`ARCHITECTURE.md`](docs/ARCHITECTURE.md:1), [`PLANS.md`](docs/PLANS.md:1), [`CHANGELOG.md`](docs/CHANGELOG.md:1), [`DECISIONS.md`](docs/DECISIONS.md:1), [`AGENTS.md`](AGENTS.md:1)).
- Ad-hoc documentation and historical plans should be placed in `docs/archive/`.
