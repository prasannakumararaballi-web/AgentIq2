# AgentIQ v2

AgentIQ v2 is an enterprise-grade data-quality and AI-assisted data-cleaning platform.

## Architecture Overview

AgentIQ v2 is structured as a clean, decoupled monorepo:

```
AgentIQ-v2/
├── apps/
│   ├── api/               # FastAPI backend service, routers, and middlewares
│   └── worker/            # Procrastinate background worker process & tasks
├── packages/
│   └── agentiq_core/      # Core domain models, Pydantic v2 schemas, engine & provider abstractions
├── contracts/             # Contract-first artifacts (openapi.json, api-spec.yaml)
├── docs/                  # API, architecture, and frontend integration specifications
├── migrations/            # Alembic database migrations
├── scripts/               # Automation, build, and contract generation scripts
├── storage/               # Local/ephemeral dataset storage (.gitkeep)
└── tests/                 # Unit, integration, and contract test suites
```

### Key Design Tenets
1. **Contract-First Development**: OpenAPI 3.1 specification serves as the single source of truth for backend implementation and frontend TypeScript client generation.
2. **Decoupled Engine**: The data cleaning engine (`DuckDB`, `pandas`, `pyarrow`) and AI reasoning layers (`Gemini API`) remain independently testable without database or network dependencies.
3. **Decoupled Worker**: Heavy ETL, batch profiling, and LLM reasoning run on a separate worker process powered by PostgreSQL queues (`Procrastinate`).
4. **Zero Frontend-Python Coupling**: The Next.js 16 frontend integrates exclusively over standard REST/JSON with Supabase JWT authentication.

---

## Getting Started (Phase 1)

### Prerequisites
- Python 3.12+ (or 3.13+)
- Git

### Installation
1. Clone or navigate to the repository:
   ```bash
   cd AgentIQ-v2
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. Install Phase 1 dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   ```

### Running the API
Start the FastAPI development server:
```bash
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Running Tests
Execute the automated test suite:
```bash
pytest
```

### Regenerating the OpenAPI Contract
To export the live FastAPI OpenAPI schema to `contracts/`:
```bash
python scripts/generate_openapi.py
```

---

## API Contract & Frontend Integration

For in-depth integration guides, see:
- [`docs/API.md`](docs/API.md): Comprehensive endpoint specification, request/response bodies, permissions, and error codes.
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md): Frontend developer integration guide, authentication details, polling strategies, and TypeScript client generation instructions.
