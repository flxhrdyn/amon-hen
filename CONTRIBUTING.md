# Contributing to Amon Hen

Thank you for your interest in contributing to **Amon Hen**! We welcome contributions of all kinds: bug reports, documentation improvements, benchmark evaluations, feature proposals, and code contributions.

---

## Code of Conduct

All contributors and maintainers are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before participating.

---

## Development Setup

Amon Hen uses [`uv`](https://github.com/astral-sh/uv) as the fast Python package and project manager.

### 1. Prerequisites
* Python >= 3.11
* `uv` installed ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
* Git

### 2. Clone and Setup
```bash
git clone https://github.com/flxhrdyn/amon-hen.git
cd amon-hen

# Install dependencies into virtualenv
uv sync --all-groups
```

### 3. Run the Test Suite
```bash
# Run unit and integration tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

### 4. Code Quality & Linting
We use [`ruff`](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
# Check code style and linting rules
uv run ruff check .

# Auto-fix lint errors where possible
uv run ruff check . --fix

# Format code
uv run ruff format .
```

---

## Project Architecture & Structure

```
amon-hen/
├── src/amonhen/
│   ├── cli.py             # Typer CLI application & interactive entry point
│   ├── decode.py          # Video decoding via imageio-ffmpeg
│   ├── encode.py          # Vision & text ONNX embedding pipelines
│   ├── interactive.py     # Tolkien-themed REPL interactive session
│   ├── model_registry.py  # Hugging Face model registry & downloader
│   ├── pipeline.py        # Indexing & search pipeline orchestration
│   ├── player.py          # System media player launcher with timestamp seeking
│   ├── progress.py        # Dual-level Rich progress reporters
│   ├── sample.py          # Adaptive motion-based frame sampling & dedup
│   ├── segment.py         # Temporal segment merging & thresholding
│   ├── store.py           # SQLite vector store powered by sqlite-vec
│   └── theme.py           # Tolkien styling, banners, score bars, & verbs
├── tests/                 # Comprehensive unit & integration tests
├── benchmarks/            # Evaluation benchmarks (Charades-STA metrics & runner)
├── demo/                  # Canonical demo assets & GIF generator
└── tools/                 # ONNX export, INT8 quantization, & HF publishing tools
```

---

## Development Guidelines

1. **Test-Driven Development (TDD):**
   - Write tests for any new features or bug fixes in `tests/`.
   - Ensure 100% of tests pass before submitting a PR.
2. **CPU-First & Low Memory:**
   - Amon Hen is strictly designed to run on CPU without requiring discrete GPUs.
   - Keep memory usage low and avoid loading unnecessary heavy dependencies into runtime.
3. **Typing & Linting:**
   - Use Python 3.11+ type annotations (`int | str`, `list[Segment]`, etc.).
   - Pass all `ruff check .` rules without warnings.

---

## Submitting a Pull Request

1. **Fork** the repository and create your branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Make your changes** with clear, atomic commits.
3. **Verify tests and linter pass:**
   ```bash
   uv run pytest
   uv run ruff check .
   ```
4. **Push** to your fork and submit a Pull Request against `main`.
5. Describe your changes clearly in the PR template, referencing any related issues.

---

## Reporting Issues

If you find a bug or have a feature request:
- Search existing [Issues](https://github.com/flxhrdyn/amon-hen/issues) to avoid duplicates.
- Open an issue using our structured bug report or feature request template.
- Provide minimal reproduction steps, OS version, and video codec details if reporting a video indexing issue.
