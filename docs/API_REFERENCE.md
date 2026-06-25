# HarvestIQ API Endpoints Reference

This document provides a detailed list of the REST API endpoints exposed by the FastAPI backend engine. You can interactively test these endpoints by visiting `https://harvestiq-api.onrender.com/docs` when the server is running.

---

## Authentication

All routes (excluding register, login, and static assets) require a valid JWT Bearer token in the `Authorization` header.

| Method | Endpoint | Description | Slowapi Limit |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register a new user profile. | `20/15minutes` |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain access and refresh tokens. | `20/15minutes` |
| `POST` | `/api/v1/auth/refresh` | Refresh access tokens (via httponly cookie). | `10/15minutes` |
| `POST` | `/api/v1/auth/logout` | Revoke session refresh tokens. | - |

---

## Users & Onboarding

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/users/me` | Fetch public details of current user. | Yes |
| `PUT` | `/api/v1/users/profile` | Update profile settings (name, language). | Yes |
| `GET` | `/api/v1/users/alert-preferences` | Get alert preference configurations. | Yes |
| `PUT` | `/api/v1/users/alert-preferences` | Update alert preferences. | Yes |
| `POST` | `/api/v1/onboarding` | Complete onboarding configuration. | Yes |

---

## Farm Database Management (CRUD)

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/farms/me` | Retrieve the compiled profile for the active farm. | Yes |
| `POST` | `/api/v1/farm-db/farms` | Create a new farm boundary record. | `FarmCreateSchema` (Body) |
| `GET` | `/api/v1/farm-db/farms` | List all farms owned by the user. | Yes |
| `GET` | `/api/v1/farm-db/farms/{farm_id}` | Retrieve specific farm bounds. | `farm_id` (Path) |
| `PUT` | `/api/v1/farm-db/farms/{farm_id}` | Edit farm boundaries and metadata. | `farm_id` (Path) |
| `DELETE` | `/api/v1/farm-db/farms/{farm_id}` | Remove farm records. | `farm_id` (Path) |
| `GET` | `/api/v1/farm-db/plots` | List plots in a farm. | `farm_id` (Query) |
| `POST` | `/api/v1/farm-db/plots` | Create a new plot record. | `PlotCreateSchema` (Body) |
| `GET` | `/api/v1/farm-db/crop-cycles` | List crop cycles for a plot. | `plot_id` (Query) |
| `GET` | `/api/v1/farm-db/crop-cycles/active` | Get all active cycles of the user. | Yes |
| `POST` | `/api/v1/farm-db/expenses` | Log crop expense transactions. | `ExpenseCreateSchema` (Body) |
| `GET` | `/api/v1/farm-db/expenses` | List expenses for a cycle. | `crop_cycle_id` (Query) |
| `POST` | `/api/v1/farm-db/harvests` | Log harvest yield transactions. | `HarvestCreateSchema` (Body) |
| `GET` | `/api/v1/farm-db/harvests` | List harvests for a cycle. | `crop_cycle_id` (Query) |

---

## Weather, Stress & Soil Analytics

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/weather/forecast` | Retrieve forecast data with MongoDB TTL caching. | `farm_id` (Query) |
| `GET` | `/api/v1/stress-index/{farm_id}` | Fetch current Field Stress Index and trajectory. | `farm_id` (Path) |
| `POST` | `/api/v1/soil/records` | Save laboratory soil measurements. | `SoilRecordCreateSchema` (Body) |
| `GET` | `/api/v1/soil/records/latest` | Fetch the latest soil nutrient scores. | `farm_id` (Query) |

---

## Copilot & Advisory

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/briefing/daily` | Compile daily briefing summaries. | `farm_id` (Query) |
| `GET` | `/api/v1/health-card` | Get farm health metrics cards. | `farm_id` (Query) |
| `GET` | `/api/v1/copilot/plan` | Fetch or generate operations schedules. | `farm_id`, `refresh` (Query) |
| `POST` | `/api/v1/copilot/plan/refresh` | Force regenerate copilot plans. | `farm_id` (Query) |
| `PUT` | `/api/v1/copilot/plan/actions/{action_id}/complete` | Mark an action complete. | `action_id` (Path), `farm_id` (Query) |
| `GET` | `/api/v1/copilot/yield-protection` | Retrieve computed yield protection score. | `farm_id` (Query) |
| `POST` | `/api/v1/advisory/ask` | Submit questions to advisory chat. | `AdvisoryAskRequest` (Body) |
| `GET` | `/api/v1/advisory/actions` | Retrieve recommended actions list. | `farm_id` (Query) |

---

## Disease Detection & Outbreak Radar

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/disease/detect` | Upload leaf images for disease screening. | File upload (Multipart) |
| `GET` | `/api/v1/disease/history` | List all historical reports. | `farm_id` (Query) |
| `GET` | `/api/v1/disease/history/{report_id}` | Retrieve specific scan reports. | `report_id` (Path) |
| `GET` | `/api/v1/disease/history/{report_id}/image` | Fetch raw uploaded image bytes. | `report_id` (Path) |
| `GET` | `/api/v1/disease/timeline` | Get merged event timeline records. | `farm_id` (Query) |
| `GET` | `/api/v1/disease-radar/nearby` | Query nearby outbreak coordinates. | `farm_id` (Query) |

---

## Emergency SOS & Sync

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/sos/trigger` | Dispatch emergency SOS alerts to contacts. | `SosTriggerRequest` (Body) |
| `POST` | `/api/v1/sos/dispatch` | Trigger emergency dispatch (alias trigger). | `SosTriggerRequest` (Body) |
| `GET` | `/api/v1/sos/contacts` | Get user emergency contacts list. | Yes |
| `POST` | `/api/v1/sos/contacts` | Save emergency contact configurations. | `EmergencyContactsSchema` (Body) |
| `GET` | `/api/v1/sos/history` | Fetch historical SOS logs. | Yes |
| `POST` | `/api/v1/simulator/run` | Run stress forecast simulation runs. | `SimulatorRequest` (Body) |
| `POST` | `/api/v1/sync` | Replay batch IndexedDB outbox queues. | `SyncBatchRequest` (Body) |
