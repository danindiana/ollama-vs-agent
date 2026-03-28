# Project Roadmap & Architecture Review

This document captures a comprehensive breakdown, structural observations, and planned maturity phases for the `ollama-vs-agent` local orchestration environment.

---

## 🔍 Code Analysis

**What it is:** A dual-project repo exploring local LLM agentic workflows on a dual-GPU workstation. 100% Python. Two core subprojects:

1. **CHM (Codebase Health Monitor)** — SQLite-backed scanner for technical debt/duplication with an ASCII dashboard
2. **Research Summary pipeline** — PDF → `pdftotext` → 32B model → multi-paradigm formal refactoring (predicate calculus, lambda calculus, Haskell, C++ TMP)

**Structural observations:**
- The model tier assignment (32B for logic, 14B for codegen, 8B for agent/chat) is architecturally sound given the VRAM split.
- `OLLAMA_KEEP_ALIVE=-1` is used for persistent model residency, which maximizes session throughput.

---

## 🛠️ Suggestions & Improvements

**Code quality / robustness:**
- **Add a `requirements.txt` or `pyproject.toml`** for reproducibility.
- **Replace `pdftotext` shell invocation with `pymupdf` (fitz)** — it's faster, handles more edge cases, and returns structured text with page metadata.
- **The `._` macOS resource fork filter** should be expanded to filter `__MACOSX/` directory prefixes.
- **CHM SQLite schema** — Use `WAL` journal mode (`PRAGMA journal_mode=WAL`) for better concurrent read performance.
- **Dashboard (`dashboard.py`)**: Harden to handle empty/null metric rows and use `shutil.get_terminal_size()` for responsive layout.

**Pipeline reliability:**
- Add a validation step that checks each output section (logic, lambda, Haskell, C++) is actually present before writing to disk.
- Add retry logic with exponential backoff for Ollama API calls.

---

## ⚡ Optimizations

**GPU / VRAM:**
- **CUDA_VISIBLE_DEVICES pinning** — Explicitly assign models to GPUs rather than relying on Ollama's default allocation.
- **Batch the research pipeline**: Queue multiple PDFs and process them with async Ollama calls using `asyncio` + `httpx`.
- **Context window tuning**: Make sure `num_ctx` is set explicitly (e.g. `16384` for the 32B) for wide context refactoring.

**CHM scanner:**
- Parallelize the file walker using `concurrent.futures.ThreadPoolExecutor`.
- Consider adding **AST-level duplication detection** (using Python's `ast` module).

---

## 📋 Immediate Next Steps
1. Add `requirements.txt` and a `Makefile`.
2. Expose CHM as a CLI tool using `argparse` or `click`.
3. Persist research pipeline state in the SQLite DB (tracking filename, model used, timestamp, output hash).
4. Version the model configs (quantization, `num_ctx`).
5. Write smoke tests for CHM (`pytest`).

---

## 🚀 Future Directions

**Near-term:**
- **Continue.dev custom slash commands** (`/refactor-paper`).
- **Embedding-based semantic search** over PROCESSED files using `nomic-embed-text` and local vector stores.
- **CHM trend visualization** web UI (FastAPI + HTML).

**Medium-term:**
- **Multi-agent debate pipeline** (32B generates, 14B critiques, 8B summarizes).
- **Tree-sitter integration** in CHM for language-aware structural analysis.
- **Self-improving CHM** that feeds scan results to the 14B coder to auto-generate patches.

**Longer-term:**
- **Formal verification integration** (exporting formal outputs to Lean 4 / Coq).
- **Knowledge graph** of paper concepts (RDF / NetworkX).
- **Benchmarking** local stack against Hosted APIs using standard datasets (HumanEval/MBPP).
