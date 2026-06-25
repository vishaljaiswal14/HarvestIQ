# HarvestIQ Intelligence Layers

This document details the different data and calculations modules (what we call our "intelligence layers") in HarvestIQ, showing how they connect to the `ContextCompilerService` (snapshot version **v3**). A key design goal we stuck to is that Gemini is only used to format, transcribe, or translate information—never to make actual crop decisions.

---

## 1. Weather Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Gets the current weather and forecast coordinates to help the farm engines make decisions |
| **Inputs** | Farm geolocation, Open-Meteo API (or cached `weather_cache` logs) |
| **Outputs** | Current temp, humidity, wind, rainfall, 7-day forecast series, and GDD parameters |
| **Dependencies** | Farm location coordinates |
| **Owner** | **Deterministic Code** — managed by `WeatherService` with a 30-minute MongoDB cache TTL to avoid hitting API rate limits |
| **Gemini** | None |

**Consumers:** Field Stress Index, Input Window Optimizer, Crop Stage (GDD), Daily Briefing, ContextCompiler weather sections.

---

## 2. Crop Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Determines the active crop type, current development stage, and GDD percentage |
| **Inputs** | Active `crop_cycles`, sowing date, `crop_characteristics` stage definitions, weather GDD logs |
| **Outputs** | Stage name, progress percentage, accumulated GDD, stage vulnerability weights |
| **Dependencies** | Weather Intelligence |
| **Owner** | **Deterministic Code** — `CropStageService` calculates heat units and matches them to stage boundaries |
| **Gemini** | None |

**Consumers:** FSI, Yield Risk, Health Card, Simulator, Input Window Optimizer.

---

## 3. Stress Intelligence (Field Stress Index)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Calculates a composite stress index score based on hot/cold snaps, dry spells, and GDD stage vulnerabilities |
| **Inputs** | Forecast temperatures, precipitation forecasts, accumulated GDD, and current growth stages |
| **Outputs** | FSI score (0–1), stress classification band (`LOW_STRESS` / `MEDIUM_STRESS` / `HIGH_STRESS`), and dominant stress factors |
| **Dependencies** | Weather Intelligence, Crop Intelligence |
| **Owner** | **Deterministic Code** — `StressIndexService` triggers the `compute_fsi()` Python function |
| **Gemini** | None |

**Persistence:** `stress_logs` (stores historical FSI ratings to track trends).

**Consumers:** Stress Momentum, Yield Risk, Alerts, Health Card, Advisory context, SOS checklist.

---

## 4. Stress Momentum Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Checks if the stress trend is getting worse, staying stable, or getting better compared to recent days |
| **Inputs** | Historical FSI numbers from `stress_logs` (last 5 logs / 7 days); projected FSI values for simulations |
| **Outputs** | Trend status (`RISING` / `STABLE` / `FALLING`), calculated momentum score, and change delta |
| **Dependencies** | Stress Intelligence (historical log indexes) |
| **Owner** | **Deterministic Code** — `StressMomentumService` calculates differences against historical logs |
| **Gemini** | None |

**Assembly:** Handled only via `ContextCompilerService._build_core_intelligence()` (v3).

**Consumers:** Yield Risk, Health Card, Daily Briefing, Simulator, Advisory context.

---

## 5. Soil Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Scores lab report metrics against reference guidelines to measure soil nutrient status |
| **Inputs** | Raw chemical metrics (NPK, pH, Organic Carbon, Electrical Conductivity) and crop-specific reference guidelines |
| **Outputs** | Soil Health Index (SHI) score out of 100, nutrient deficiency status flags, and explainability report logs |
| **Dependencies** | Active crop cycle details (to match against the right crop thresholds) |
| **Owner** | **Deterministic Code** — `SoilHealthService` maps NPK, pH, organic carbon, and EC metrics |
| **Gemini** | None |

**Consumers:** Yield Risk, Health Card, ContextCompiler soil sections.

---

## 6. Disease Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Identifies leaf diseases, cross-references findings with local records, and charts outbreak coordinates |
| **Inputs** | Leaf image (vision tag), crop type, coordinates (state/district), and state allowlist validation rules |
| **Outputs** | Disease tag, diagnostic state (`CONFIRMED` / `LOW_CONFIDENCE` / `REJECTED`), and nearby outbreak coordinates |
| **Dependencies** | Farm location profile, disease scans collection, and regional alert radars |
| **Owner** | **Hybrid** — Gemini Vision does the visual symptom scan, but a deterministic state allowlist filters the outputs before reporting |
| **Gemini** | Only for symptom tag suggestions (`detect_disease`); regional rules must confirm it |

**Consumers:** Yield Risk (confirmed disease + nearby radar), Health Card, Disease Radar map, Advisory context.

---

## 7. Knowledge Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Retrieves research documents and expert advice related to a user's question |
| **Inputs** | Inferred query topic, crop type, state, district, and raw text keywords |
| **Outputs** | Relevancy-ranked research excerpts, citations, and metadata details |
| **Dependencies** | ChromaDB collections, MongoDB `knowledge_metadata` index logs |
| **Owner** | **Deterministic Code** — `RagService.hybrid_search()` runs similarity math and local tag checks in ChromaDB |
| **Gemini** | None for retrieval; synthesis happens in the Advisory layer |

**Consumers:** Advisory (`compile_context` gathering step only).

---

## 8. Advisory Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Synthesizes data inputs and research sheets into a clear reply in local languages |
| **Inputs** | Grounded context template (v3 state snapshot + retrieved research papers + query text) and local language key |
| **Outputs** | Advice response text, verified doc citations, explainability parameters, and database audit logs |
| **Dependencies** | ContextCompilerService v3, Knowledge Intelligence, and core farm telemetry engines |
| **Owner** | **Hybrid** — Context gathering is strictly code-based, and Gemini formats the text payload without adding outside assumptions |
| **Gemini** | Used inside `synthesize_advisory()` only for formatting and language translation |

**Rule:** Gemini is strictly blocked from making up suggestions or facts outside the compiled context package.

---

## 9. Yield Risk Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Calculates a final yield risk score by checking weather stress, crop age, soil logs, and nearby pests |
| **Inputs** | FSI, Stress Momentum trends, crop growth vulnerability factors, Soil Health Index, and regional disease radar hits |
| **Outputs** | Yield danger rating (`LOW` / `MEDIUM` / `HIGH`), risk percentage, and primary contributing signals |
| **Dependencies** | Stress Index, Momentum, Crop Stage, Soil, and Disease modules |
| **Owner** | **Deterministic Code** — calculated by `YieldRiskService` using standard logic weights |
| **Gemini** | None |

**Assembly:** Handled only via `ContextCompilerService._build_core_intelligence()` (v3).

**Consumers:** Health Card, Daily Briefing, Simulator, Advisory context, SOS emergency snap.

---

## 10. Farm Health Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Aggregates the entire farm snapshot to render dashboard health cards and emergency guides |
| **Inputs** | Full v3 core snapshot variables: FSI, trends, yield risk, soil rating, alerts, nearby outbreaks |
| **Outputs** | Combined health score rating (0–100), health band tag, and health card details |
| **Dependencies** | Core snapshot compiled via `compile_health_snapshot()` |
| **Owner** | **Deterministic Code** — `HealthCardService` maps compiler metrics directly (no custom data changes) |
| **Gemini** | None |

**Consumers:** Dashboard (`GET /health-card`), SOS emergency checklist compilation.

---

## ContextCompilerService Integration Map

Here is a map of what data the `ContextCompilerService` pulls together depending on the page or request:

| Compiler mode | Layers included |
|---------------|-----------------|
| `compile_context()` (Advisory) | Weather, Crop, Stress, Momentum, Yield Risk, Soil, Alerts, Disease, Radar, RAG, User question |
| `compile_briefing_context()` | Core v3 + Input Windows + Market + Schemes summary |
| `compile_health_snapshot()` | Core v3 + health score/band |
| `compile_simulator_snapshots()` | Core v3 baseline + projected FSI recomputation |

**intelligence_snapshot_version:** `v3`

---

## Gemini Usage Summary

This table acts as our rules guide for where AI is allowed vs where we must use code:

| Allowed | Not allowed |
|---------|-------------|
| Advisory synthesis | FSI, momentum, yield risk, optimizer, simulator |
| Briefing synthesis | Scheme eligibility, health score |
| Disease image tagging (then confirmed deterministically) | SOS checklist generation |
| Voice transcription | Demo fixture decisions |

---

## Day 7 Resiliency (non-intelligence)

Things like our emergency SOS logs, demo mode mocks, browser caches, and validation checklists don't build new calculation models. SOS checks the current health score, demo mode serves simple JSON files, and PWA caches the latest backend reports.
