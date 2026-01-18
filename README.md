# PRD Testing Phase 1

Data extraction POC - ADT (Autonomous Dev Team) test project.

## Overview

This project serves as a proof-of-concept for data extraction capabilities, managed by the ADT autonomous development system.

## Project Structure

```
PRD_testing_phase_1/
├── src/                    # Source code
│   └── __init__.py
├── tests/                  # Test files
│   └── __init__.py
├── requirements.txt        # Python dependencies
└── README.md
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Development

- Run tests: `pytest`
- Run linting: `ruff check .`
- Run type checking: `mypy src/`

## License

MIT
