# HarvestIQ Intelligence Layers

This document describes the deterministic intelligence layers in HarvestIQ and how they relate to `ContextCompilerService` (single source of truth, snapshot **v3**). Gemini is used only for presentation (advisory/briefing synthesis, vision, voice) — never for agronomic decisions.

---

## 1. Weather Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Provide current conditions and short-range forecast for field decisions |
| **Inputs** | Farm geolocation, Open-Meteo (or cached `weather_cache`) |
| **Outputs** | Current temp/humidity/wind/precipitation, 7-day forecast, daily GDD series |
| **Dependencies** | Farm onboarding, location coordinates |
| **Owner** | **Deterministic** — `WeatherService`, MongoDB `weather_cache` (30 min TTL) |
| **Gemini** | None |

**Consumers:** Field Stress Index, Input Window Optimizer, Crop Stage (GDD), Daily Briefing, ContextCompiler weather sections.

---

## 2. Crop Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Resolve crop type, growth stage, and GDD progress |
| **Inputs** | Active `crop_cycles`, sowing date, `crop_characteristics` stage definitions, weather GDD |
| **Outputs** | Stage name, progress %, GDD timeline, stage vulnerability weights |
| **Dependencies** | Weather Intelligence |
| **Owner** | **Deterministic** — `CropStageService`, `deterministic_engine` (GDD, stage resolution) |
| **Gemini** | None |

**Consumers:** FSI, Yield Risk, Health Card, Simulator, Input Window Optimizer.

---

## 3. Stress Intelligence (Field Stress Index)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Quantify composite field stress from weather and crop progress |
| **Inputs** | Current/forecast temperature, precipitation, accumulated GDD, stage vulnerability |
| **Outputs** | FSI score (0–1), classification (`LOW_STRESS` / `MEDIUM_STRESS` / `HIGH_STRESS`), component breakdown, primary factor |
| **Dependencies** | Weather Intelligence, Crop Intelligence |
| **Owner** | **Deterministic** — `StressIndexService`, `deterministic_engine.compute_fsi()` |
| **Gemini** | None |

**Persistence:** `stress_logs` (historical FSI for momentum).

**Consumers:** Stress Momentum, Yield Risk, Alerts, Health Card, Advisory context, SOS checklist.

---

## 4. Stress Momentum Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Detect whether field stress is worsening, stable, or improving over time |
| **Inputs** | `stress_logs` FSI time series (7-day / last 5 logs); optional projected FSI for simulator |
| **Outputs** | `RISING` / `STABLE` / `FALLING`, `momentum_score`, `fsi_delta`, `insufficient_history` flag |
| **Dependencies** | Stress Intelligence (historical logs) |
| **Owner** | **Deterministic** — `StressMomentumService` → `compute_stress_momentum()` |
| **Gemini** | None |

**Assembly:** Only via `ContextCompilerService._build_core_intelligence()` (v3).

**Consumers:** Yield Risk, Health Card, Daily Briefing, Simulator, Advisory context.

---

## 5. Soil Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Assess soil nutrient status and composite soil health |
| **Inputs** | Lab measurements (N, P, K, pH, OC, EC), crop-specific reference ranges |
| **Outputs** | Soil Health Index (SHI), per-nutrient deficiency status, explainability |
| **Dependencies** | Active crop cycle (for crop-type ranges) |
| **Owner** | **Deterministic** — `SoilHealthService`, `compute_soil_health_index()` |
| **Gemini** | None |

**Consumers:** Yield Risk, Health Card, ContextCompiler soil sections.

---

## 6. Disease Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Detect, confirm, and track disease signals at farm and regional level |
| **Inputs** | Image (vision tag), crop type, state, confidence threshold, `disease_allowed_regions` rules |
| **Outputs** | Disease tag, `CONFIRMED` / `LOW_CONFIDENCE` / `REJECTED`, radar hotspots |
| **Dependencies** | Farm profile, disease reports, disease radar aggregation |
| **Owner** | **Hybrid** — Gemini Vision proposes tag/confidence; **deterministic confirmation** gates all outputs |
| **Gemini** | Vision only (`detect_disease`); confirmation is rule-based |

**Consumers:** Yield Risk (confirmed disease + nearby radar), Health Card, Disease Radar map, Advisory context.

---

## 7. Knowledge Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Retrieve agronomic knowledge excerpts relevant to a query |
| **Inputs** | User query, crop type, state, district, inferred topic |
| **Outputs** | Ranked knowledge chunks, citations, chunk IDs |
| **Dependencies** | ChromaDB vector store, `knowledge_metadata` |
| **Owner** | **Deterministic** — `RagService.hybrid_search()` (embedding + metadata filters) |
| **Gemini** | None for retrieval; synthesis happens in Advisory layer |

**Consumers:** Advisory (`compile_context` only).

---

## 8. Advisory Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Answer farmer questions with grounded natural language |
| **Inputs** | Compiled context package (v3 core + RAG excerpts + user question), language, mitigation lock flag |
| **Outputs** | Synthesis text, citations, explainability, `advisory_logs` audit record |
| **Dependencies** | ContextCompilerService v3, Knowledge Intelligence, all core layers |
| **Owner** | **Hybrid** — context assembly is deterministic; **Gemini synthesizes** from context only |
| **Gemini** | `synthesize_advisory()` — presentation only |

**Rule:** Gemini must not invent facts outside the context package.

---

## 9. Yield Risk Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Estimate harvest/yield risk from multi-signal farm state |
| **Inputs** | FSI, Stress Momentum, crop stage (via stage vulnerability), SHI, disease presence (confirmed reports + nearby radar) |
| **Outputs** | `LOW` / `MEDIUM` / `HIGH` band, `estimated_risk_percent`, contributing factors |
| **Dependencies** | Stress, Momentum, Crop, Soil, Disease layers |
| **Owner** | **Deterministic** — `YieldRiskService` → `compute_yield_risk()` |
| **Gemini** | None |

**Assembly:** Only via `ContextCompilerService._build_core_intelligence()` (v3).

**Consumers:** Health Card, Daily Briefing, Simulator, Advisory context, SOS (read-only health snapshot).

---

## 10. Farm Health Intelligence

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Unified farm health summary for dashboard and emergency response |
| **Inputs** | Full v3 core snapshot: FSI, momentum, yield risk, SHI, alerts, radar; plus `compute_health_risk_rating()` |
| **Outputs** | `health_score`, `health_band`, full Health Card payload, explainability |
| **Dependencies** | All layers above via `compile_health_snapshot()` |
| **Owner** | **Deterministic** — `HealthCardService` maps compiler output; no local assembly |
| **Gemini** | None |

**Consumers:** Dashboard (`GET /health-card`), SOS (`compile_health_snapshot` for emergency checklist).

---

## ContextCompilerService Integration Map

| Compiler mode | Layers included |
|---------------|-----------------|
| `compile_context()` (Advisory) | Weather, Crop, Stress, Momentum, Yield Risk, Soil, Alerts, Disease, Radar, RAG, User question |
| `compile_briefing_context()` | Core v3 + Input Windows + Market + Schemes summary |
| `compile_health_snapshot()` | Core v3 + health score/band |
| `compile_simulator_snapshots()` | Core v3 baseline + projected FSI recomputation |

**intelligence_snapshot_version:** `v3`

---

## Gemini Usage Summary

| Allowed | Not allowed |
|---------|-------------|
| Advisory synthesis | FSI, momentum, yield risk, optimizer, simulator |
| Briefing synthesis | Scheme eligibility, health score |
| Disease image tagging (then confirmed deterministically) | SOS checklist generation |
| Voice transcription | Demo fixture decisions |

---

## Day 7 Resiliency (non-intelligence)

SOS, Demo Mode, PWA caching, and Verification Logging do **not** add new intelligence layers. SOS reads `compile_health_snapshot()`; Demo Mode serves static fixtures; PWA caches last-known compiler outputs.
