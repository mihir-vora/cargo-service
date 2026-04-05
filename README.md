# Cargo optimization service

Django REST service that assigns cargo volumes to vessel tanks: cargo may be split across tanks, each tank may only store one cargo id (partial fills allowed), and the goal is to maximize total loaded volume.

## Approach

- **Flow**: `POST /input` stores cargos and tanks and returns a `job_id`. `POST /optimize` runs the allocator for that job. `GET /results?job_id=...` returns the plan.
- **Storage**: SQLite + `OptimizationJob` (JSON fields for cargos, tanks, result).
- **Algorithm**: Iterative greedy matching — each step picks the unused tank + cargo pair that maximizes `min(remaining_cargo, tank_capacity)`, tie-breaking on less wasted tank capacity. Heuristic only; not a proof of global optimality for every instance.

## Assumptions

- Volumes and capacities are non-negative integers.
- Cargo ids are unique among cargos; tank ids are unique among tanks.
- A tank assigned to a cargo may be partially filled; leftover space in that tank cannot be used for another cargo id.

---

## Local setup

### Prerequisites

- Python **3.10+** (3.12 recommended)
- **pip**

### Commands (Windows PowerShell)

```powershell
cd path\to\cargo-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env if you want (optional for local dev; defaults work with DEBUG-style local runs)
python manage.py migrate
python manage.py runserver
```

The API base URL is **http://127.0.0.1:8000** (Django default).

### Commands (Linux / macOS)

```bash
cd path/to/cargo-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret (set in production / Docker) |
| `DJANGO_DEBUG` | `1` / `true` for local debugging |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |

If you do not set these for local dev, `settings.py` uses safe-enough defaults for `runserver`.

### Run tests

```powershell
.\.venv\Scripts\python manage.py test allocation
```

```bash
python manage.py test allocation
```

---

## Docker

From the project root (where the `Dockerfile` is):

```powershell
docker build -t cargo-service .
docker run --rm -p 8000:8000 -e DJANGO_SECRET_KEY=your-long-random-secret cargo-service
```

Then use base URL **http://127.0.0.1:8000**. Migrations run when the container starts.

---

## API reference (Postman / HTTP)

**Base URL (local):** `http://127.0.0.1:8000`

**Common headers**

| Header | Value |
|--------|--------|
| `Content-Type` | `application/json` |

There is no auth; CSRF is not required for these JSON POSTs via DRF `APIView`.

---

### 1. `POST /input`

Stores cargo and tank definitions for a new job.

**Request body**

| Field | Type | Description |
|-------|------|-------------|
| `cargos` | array | Each item: `id` (string), `volume` (integer ≥ 0) |
| `tanks` | array | Each item: `id` (string), `capacity` (integer ≥ 0) |

**Example request body**

```json
{
  "cargos": [
    { "id": "C1", "volume": 50 },
    { "id": "C2", "volume": 30 }
  ],
  "tanks": [
    { "id": "T1", "capacity": 40 },
    { "id": "T2", "capacity": 25 }
  ]
}
```

**Success: `200 OK`**

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

`job_id` is a UUID string. Use it for `/optimize` and `/results`.

**Error examples**

| Status | Body example |
|--------|----------------|
| `400` | `{ "error": "cargos: This field is required." }` or `{ "error": "duplicate cargo id: C1" }` |
| `400` | `{ "error": "cargos.0.volume: Ensure this value is greater than or equal to 0." }` |

---

### 2. `POST /optimize`

Runs allocation for an existing `job_id`.

**Request body**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string (UUID) | Returned by `POST /input` |

**Example request body**

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Success: `200 OK`**

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "ok"
}
```

**Error examples**

| Status | Body example |
|--------|----------------|
| `400` | `{ "error": "job_id: ..." }` (validation) |
| `404` | `{ "error": "job not found" }` |
| `400` | `{ "error": "..." }` (e.g. invalid stored payload from `AllocationError`) |

---

### 3. `GET /results`

Returns the last optimization result for a job.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | UUID string | yes | Same UUID as returned from `/input` |

**Example**

`GET http://127.0.0.1:8000/results?job_id=3fa85f64-5717-4562-b3fc-2c963f66afa6`

**Success: `200 OK`**

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "assignments": [
    {
      "tank_id": "T1",
      "cargo_id": "C1",
      "loaded_volume": 40
    },
    {
      "tank_id": "T2",
      "cargo_id": "C2",
      "loaded_volume": 25
    },
    {
      "tank_id": "T3",
      "cargo_id": "C1",
      "loaded_volume": 10
    }
  ],
  "total_loaded_volume": 75,
  "cargo_remaining": {}
}
```

- **`assignments`**: Each row is one tank used once, bound to a single `cargo_id`, with `loaded_volume` ≤ that tank’s capacity.
- **`total_loaded_volume`**: Sum of `loaded_volume` across assignments.
- **`cargo_remaining`**: Map of cargo id → volume that could not be placed (empty object `{}` if everything that could be loaded under the algorithm was loaded).

**Error examples**

| Status | Body example |
|--------|----------------|
| `400` | `{ "error": "job_id: ..." }` (missing or invalid query param) |
| `404` | `{ "error": "job not found" }` |
| `409` | `{ "error": "optimization has not been run for this job" }` |

---

## Postman collection

Import this file into Postman: **`postman/cargo-service.postman_collection.json`**

1. Postman → **Import** → choose that file.
2. Create an environment (optional) with variable `base_url` = `http://127.0.0.1:8000` (the collection uses `{{base_url}}`).
3. Call **Input** → copy `job_id` from the response into the collection variable `job_id` (or paste manually into **Optimize** and **Results**).

The collection contains three requests matching the endpoints above.

---

## cURL quick flow

```bash
# 1) Input
curl -s -X POST http://127.0.0.1:8000/input \
  -H "Content-Type: application/json" \
  -d '{"cargos":[{"id":"C1","volume":50}],"tanks":[{"id":"T1","capacity":30},{"id":"T2","capacity":40}]}'

# 2) Optimize (replace JOB_ID)
curl -s -X POST http://127.0.0.1:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"job_id":"JOB_ID"}'

# 3) Results
curl -s "http://127.0.0.1:8000/results?job_id=JOB_ID"
```

Replace `JOB_ID` with the UUID from step 1.
