# ⚙️ HarvestIQ Backend Engine

### Python-Based Deterministic Agricultural Calculations & RAG API

This is the backend intelligence module for HarvestIQ, written in **Python 3.12** using **FastAPI** as the API framework, **MongoDB Atlas** as the database layer (via the **Motor** async driver), and **ChromaDB** as the semantic vector database for hybrid Retrieval-Augmented Generation (RAG).

---

## 🛠️ Technology Stack

*   **API Framework:** FastAPI (with `slowapi` rate limiting and async route configurations)
*   **Database:** MongoDB Atlas (asynchronous access via Motor)
*   **Vector Database:** ChromaDB (integrated locally for embedding query matches)
*   **AI Models Integration:** Google Gemini & OpenRouter API (specifically for visual leaf diagnosis & natural language synthesis)
*   **Testing Suite:** Pytest & Pytest-asyncio

---

## 🏗️ Core Architecture & Directory Layout

The backend repository is structured logically around clean architectural principles:

```text
harvestiq-engine/
├── app/
│   ├── api/                    # API Routing and Schema Validations
│   │   └── v1/                 # Version 1 Endpoints (advisory, briefing, weather, sos, sync)
│   ├── core/                   # Shared Configurations & Central Threshold Constants
│   │   ├── constants/          # Static Threshold Values (fsi.py, soil.py, yield_risk.py, etc.)
│   │   ├── config.py           # Environment Configurations (pydantic-settings)
│   │   ├── database.py         # MongoDB connections & indexes initialization
│   │   └── security.py         # Password hashing & JWT generation
│   ├── integrations/           # External API Clients
│   │   ├── gemini_client.py    # OpenRouter & Gemini AI calls
│   │   └── open_meteo_client.py# Meteorological forecasts fetching
│   ├── middleware/             # Security and Localization Request Pipeline handlers
│   ├── models/                 # Database Schema definitions (Pydantic & BSON)
│   └── services/               # Core Agronomic and Data processing services
│       ├── context_compiler_service.py # Single Source of Truth Context Compiler (v3)
│       ├── deterministic_engine.py     # Clean formulas (FSI, Soil Index, Yield Risk, GDD)
│       └── rag_service.py              # Semantic vector search and metadata filter
├── data/
│   └── agri_kb/                # ICAR Reference Manuals for Vector Seeding
├── scripts/                    # Database migrations, seeding scripts, and helper runners
├── tests/                      # 36 Pytest test files
├── requirements.txt            # System dependencies manifest
└── README.md                   # This Documentation
```

---

## 🧠 Services & Intelligence Layer Breakdown

Agronomic evaluations are calculated in a pure deterministic layer. LLM/Vision components are kept isolated to presentation and semantic tag suggestions.

### 1. Context Compiler Service
*   **File:** [context_compiler_service.py](file:///Users/vishaljaiswal/Desktop/HARVESTIQ%20FINAL/harvestiq-engine/app/services/context_compiler_service.py)
*   **Role:** Compiles the complete core snapshot (version `v3`) for a given farm. It is utilized by four core operations:
    1.  `compile_context()`: Packs weather metrics, crop stages, historical reports, RAG documentation chunks, and unread alerts into a markdown context block for the Advisory synthesis model.
    2.  `compile_briefing_context()`: Builds structured summaries of current stress, yield risk, safe operational windows, market price trend alerts, and eligible government schemes.
    3.  `compile_health_snapshot()`: Combines FSI, soil indexes, unread alerts, and nearby outbreaks to calculate the composite farm health score.
    4.  `compile_simulator_snapshots()`: Computes baseline metrics versus delta projections when running scenarios.

### 2. Deterministic Agronomic Calculations
*   **File:** [deterministic_engine.py](file:///Users/vishaljaiswal/Desktop/HARVESTIQ%20FINAL/harvestiq-engine/app/services/deterministic_engine.py)
*   **Core Math & Logic:**
    *   **Growing Degree Days (GDD):**
        $$\text{Daily GDD} = \max\left(\frac{T_{\text{max}} + T_{\text{min}}}{2} - T_{\text{base}}, 0\right)$$
    *   **Field Stress Index (FSI):** Evaluates thermal stress (against optimal $32^\circ\text{C}$ / critical $42^\circ\text{C}$ bounds), rainfall deficit (comparing 3-day forecast rain to expected $5\text{mm}$ daily water requirements), and stage progress vulnerability. FSI is weighted:
        $$\text{FSI} = (0.40 \times S_{\text{temp}}) + (0.35 \times S_{\text{rain\_deficit}}) + (0.25 \times S_{\text{gdd}})$$
    *   **Stress Momentum:** Measures delta change between the latest FSI and the average of the last 5 logs. Delta exceeding $\pm 0.05$ triggers $\text{RISING}$ or $\text{FALLING}$ momentum.
    *   **Soil Health Index (SHI):** Evaluates macro/micro nutrient measurements (N, P, K, pH, Organic Carbon, Electrical Conductivity) relative to reference bounds. It computes a weighted average of individual health mappings.
    *   **Yield Risk:** Combines FSI ($40\%$), stress momentum ($15\%$), growth stage vulnerability ($10\%$), soil health index ($15\%$), and confirmed or radar disease reports ($20\%$).
    *   **Farm Health Rating:** Combines FSI ($25\%$), Soil Index ($25\%$), Disease Radar ($10\%$), Unread alerts ($10\%$), and Yield Risk ($10\%$) into a unified score out of 100. GOOD: $\ge 75.0$, FAIR: $\ge 50.0$, POOR: $< 50.0$.
    *   **Input Windows:** Classifies actions (spraying, fertilizing, irrigating) as SAFE or UNSAFE based on wind speed (limit $20\text{ km/h}$), forecast precipitation (limit $5\text{ mm}$), and FSI stress ratings.
    *   **Decision Simulator:** Simulates delta changes to thermal, irrigation, and nutrient parameters, returning FSI curves and yield projection factors.

### 3. RAG Retrieval & Hybrid Search
*   **File:** [rag_service.py](file:///Users/vishaljaiswal/Desktop/HARVESTIQ%20FINAL/harvestiq-engine/app/services/rag_service.py)
*   **Role:** Queries ChromaDB collection for relevant semantic chunks. It computes a hybrid rank:
    $$\text{Score} = (0.70 \times \text{Semantic Cosine Score}) + (0.30 \times \text{Token Keyword Hit Ratio})$$
    Matches are filtered strictly by metadata in MongoDB (`knowledge_metadata`) to match the crop type, state, district, and season of the user's farm.

### 4. Crop Doctor Vision Pipeline
*   **File:** [disease_detection_service.py](file:///Users/vishaljaiswal/Desktop/HARVESTIQ%20FINAL/harvestiq-engine/app/services/disease_detection_service.py)
*   **Role:** Accepts visual crop uploads. The image is analyzed via OpenRouter's vision model to extract candidate disease labels. The candidate label must pass deterministic confirm rules ([confirm_disease_detection](file:///Users/vishaljaiswal/Desktop/HARVESTIQ%20FINAL/harvestiq-engine/app/services/deterministic_engine.py#L186-L215)) based on regional boundaries. Any visual analysis with confidence $\ge 80\%$ bypasses strict regional allowlist checks.

---

## 🔌 API Endpoints & Interfaces

| Method | Endpoint | Description | Auth Required |
|:---|:---|:---|:---|
| **POST** | `/api/v1/auth/register` | Register a new farmer account | No |
| **POST** | `/api/v1/auth/login` | Authenticate farmer, return JWT & HttpOnly cookies | No |
| **POST** | `/api/v1/auth/refresh` | Re-issue expired JWT using refresh cookies | No |
| **POST** | `/api/v1/onboarding` | Complete onboarding details & initialize first cycle | Yes |
| **GET** | `/api/v1/farms/me` | Fetch active farm profile info | Yes |
| **GET** | `/api/v1/weather/forecast` | Retrieve 7-day weather forecast (cached 30m) | Yes |
| **GET** | `/api/v1/health-card` | Get Compiled Health Score card & yield risk snapshots | Yes |
| **POST** | `/api/v1/disease/detect` | Upload image for Vision detection & validation | Yes |
| **GET** | `/api/v1/disease-radar/nearby` | Query disease outbreaks within a set radius | Yes |
| **POST** | `/api/v1/advisory/ask` | Submit questions for synthesized, grounded advisory | Yes |
| **POST** | `/api/v1/simulator/run` | Execute baseline vs projected "what-if" models | Yes |
| **POST** | `/api/v1/sos/trigger` | Log critical emergency, generate checklist, dispatch SMS | Yes |
| **POST** | `/api/v1/sync` | Process client outbox sync queue & return database ObjectIDs | Yes |

---

## 🛠️ Seeding & Initial Database Population

Before launching the backend, you must seed the required schemas and constants into MongoDB and ChromaDB.

1.  Navigate to the backend directory:
    ```bash
    cd harvestiq-engine
    ```
2.  Install packages inside your virtual environment (refer to Root Setup):
    ```bash
    .venv/bin/pip install -r requirements.txt
    ```
3.  Ensure `.env` matches your MongoDB Atlas string and API credentials.
4.  Run the seeding scripts sequentially:
    *   **Seed Crop Characteristics:** Populates GDD temperature bases and vulnerability stages.
        ```bash
        .venv/bin/python scripts/seed_crop_characteristics.py
        ```
    *   **Seed System Rules:** Populates alerting rules.
        ```bash
        .venv/bin/python scripts/seed_system_rules.py
        ```
    *   **Seed Localization:** Imports bilingual translation dictionaries.
        ```bash
        .venv/bin/python scripts/seed_localization.py
        ```
    *   **Seed Market Prices:** Imports local mandi prices.
        ```bash
        .venv/bin/python scripts/seed_market_prices.py
        ```
    *   **Seed Government Schemes:** Populates eligibility criteria structures.
        ```bash
        .venv/bin/python scripts/seed_schemes.py
        ```
    *   **Seed Agronomic Knowledge Base (RAG):** Parses ICAR reference documents from `data/agri_kb/`, embeds text, and loads files into ChromaDB.
        ```bash
        .venv/bin/python scripts/seed_knowledge_base.py
        ```
    *   **Seeding Mock Radar Data:** Injects regional outbreak case hotspots for radar demonstration.
        ```bash
        .venv/bin/python scripts/inject_mock_disease_reports.py
        ```

---

## 🧪 Testing

The pytest suite includes unit, API integration, middleware, and caching tests.

```bash
# Run the entire test folder
.venv/bin/pytest -v
```

Tests verify:
- Formula limits, GDD accumulation bounds, and FSI weights in `test_deterministic_engine.py`.
- Correct language fallback headers and parsing in `test_localization_middleware.py`.
- Database write consistency, transactions, and index matching in `test_farm_db.py`.
- Outbox replay conflicts and duplicates reconciliation in `test_farm_sync_replay.py`.
