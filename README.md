# PharmaWatch API

> Polyglot persistence system for pharmacovigilance — **MongoDB · Neo4j · Redis** orchestrated via **FastAPI** with a distributed **Saga pattern**.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?logo=mongodb&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5-008CC1?logo=neo4j&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

*Academic project — Ingeniería de Datos II, UADE*

---

## What it does

PharmaWatch is a REST API that simulates a real-world pharmacovigilance platform. It consolidates data across three purpose-fit databases to handle drug safety monitoring, prescription verification, cold-chain tracking, and drug interaction analysis — all in a single request lifecycle.

---

## Architecture

```
                          ┌─────────────────────────────────┐
     HTTP                 │        FastAPI (port 8000)      │
    Client ────────────── │  routers/ · models/ · saga.py   │
                          └───────────┬────────┬────────┬───┘
                                      │        │        │
                          ┌───────────▼─┐ ┌────▼───┐ ┌──▼─────────┐
                          │   MongoDB   │ │  Neo4j │ │   Redis    │
                          │  Port 27017 │ │  7474  │ │   6379     │
                          └─────────────┘ └────────┘ └────────────┘
                          Historical data    Graph   Operational state
```

| Database | Role | Data |
|----------|------|------|
| **MongoDB** | Source of truth | Drugs, batches, distributors, clinical trials, adverse effects |
| **Neo4j** | Relationship engine | Drug interactions, active ingredient networks |
| **Redis** | Real-time operational state | Alerts (Sorted Set), cold chain (Stream), access control (Hash/List) |

### Design decisions

Each database was chosen deliberately for the access pattern it needs to serve:

- **MongoDB** stores document-shaped pharmaceutical records where the schema evolves (clinical trials, adverse effects with nested reactions). Flexible documents beat rigid relational tables here.
- **Neo4j** powers interaction detection — finding all drugs that conflict with a given active ingredient requires N-depth graph traversal. This is a JOIN explosion in SQL but a natural path query in Cypher.
- **Redis** handles sub-millisecond alert lookups and cold-chain temperature streams. Using a Sorted Set for alerts gives instant priority ranking; using a Stream for temperature readings gives an append-only, replayable log.
- **Saga pattern** (`api/saga.py`) coordinates writes across all three databases without a global transaction. If any step fails, compensating transactions execute in LIFO order — eventual consistency without distributed locks.

---

## Quick start

```bash
# 1. Start all services (databases + API)
docker compose up -d

# 2. Seed test data (first run only)
docker compose exec api python seed/generar_datos.py --all --redis-load
```

Services:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | — |
| **Swagger docs** | http://localhost:8000/docs | — |
| **Dashboard** | http://localhost:8000/dashboard | — |
| Mongo Express | http://localhost:8081 | — |
| Redis Commander | http://localhost:8082 | — |
| Neo4j Browser | http://localhost:7474 | `neo4j` / `farmaceutica` |

```bash
# Stop services
docker compose down

# Full reset (wipes volumes)
docker compose down -v
```

---

## API endpoints

### `GET /panel` — Real-time pharmacovigilance panel

Consolidates system risk state: active alerts and queue (Redis), most-reported drugs in the last month (MongoDB), most dangerous active ingredients (Neo4j).

---

### `POST /prescripcion/verificar` — Prescription verification

```json
{ "paciente_id": "PAC-2024-00001", "medicamento_id": "<ObjectId>" }
```

Detects interactions in Neo4j → checks active alerts in Redis → retrieves patient history in MongoDB → publishes a Redis alert if severe risk is found.

---

### `GET /lote/{numero_lote}/trazabilidad` — Batch traceability + cold chain

Reads the vehicle temperature Stream (Redis); if a cold-chain breach is detected, publishes an alert. Returns full batch traceability from MongoDB.

---

### `GET /medicamento/{medicamento_id}/interacciones` — Interaction analysis

Retrieves a drug's active ingredients (MongoDB) and maps all known interactions with existing drugs (Neo4j), ordered by severity.

Supports hypothetical drugs without a DB record:
```
GET /medicamento/nuevo/interacciones?principios_activos=Amoxicilina&principios_activos=Clavulanato
```

---

### `POST /alerta/cerrar` — Alert closure

```json
{
  "alerta_id": "ALT-A1B2C3D4",
  "medicamento_id": "MED001",
  "resultado": "confirmado",
  "investigador_id": "INV001",
  "acciones_tomadas": "Suspensión del lote y notificación a ANMAT",
  "nueva_interaccion": {
    "pa1": "Warfarina", "pa2": "Ibuprofeno",
    "tipo": "farmacocinetica", "severidad": "grave",
    "mecanismo": "Desplazamiento de proteínas plasmáticas"
  }
}
```

Removes the alert from Redis → persists the ruling in MongoDB → if a new interaction is confirmed, creates the relationship in the Neo4j graph.

---

## Project structure

```
.
├── api/                        # FastAPI application
│   ├── main.py
│   ├── models.py               # Pydantic schemas
│   ├── saga.py                 # Distributed saga orchestrator
│   └── routers/                # One file per business operation
├── mongodb/                    # MongoDB layer
│   ├── connection.py
│   └── queries/                # Standalone queries (a–e)
├── neo4j_db/                   # Neo4j layer
│   ├── connection.py
│   └── queries/                # Standalone queries (a–e)
├── redis_db/                   # Redis layer
│   ├── connection.py
│   └── queries/
│       ├── a_alertas_farmacovigilancia.py  # Sorted Set
│       ├── b_cadena_frio.py                # Stream
│       └── c_control_acceso.py            # Hash + List + String
├── seed/                       # Faker-based data generator
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Dataset

| Engine | Entity | Count |
|--------|--------|-------|
| MongoDB | Active ingredients | 80 |
| MongoDB | Drugs | 200 |
| MongoDB | Distributors | 50 |
| MongoDB | Batches | 150 |
| MongoDB | Clinical trials | 20 |
| MongoDB | Adverse effects | 300 |
| Neo4j | `:PrincipioActivo` nodes | 80 |
| Neo4j | `:Medicamento` nodes | 200 |
| Neo4j | `:Patologia` nodes | ~40 |
| Neo4j | `:Paciente` nodes | 50 |
| Redis | Alerts (Sorted Set) | 10 |
| Redis | Temperature readings (Stream) | 30 (VEH002 with breach) |
| Redis | Pending reports (List) | 5 |
| Redis | Access log (Hash) | 4 |

---

## Standalone queries (module mode)

```bash
# MongoDB
PYTHONPATH=. python -m mongodb.queries.a_trazabilidad <numero_lote>
PYTHONPATH=. python -m mongodb.queries.b_lotes_vencimiento
PYTHONPATH=. python -m mongodb.queries.c_efectos_adversos <medicamento_id>
PYTHONPATH=. python -m mongodb.queries.d_ensayos_fase_iii
PYTHONPATH=. python -m mongodb.queries.e_senal_farmacovigilancia

# Neo4j
PYTHONPATH=. python -m neo4j_db.queries.a_interacciones_prescripcion <paciente_id>
PYTHONPATH=. python -m neo4j_db.queries.b_red_principio_activo <nombre_pa>
PYTHONPATH=. python -m neo4j_db.queries.c_toxicidad_acumulativa
PYTHONPATH=. python -m neo4j_db.queries.d_pa_mas_peligroso --top 10
PYTHONPATH=. python -m neo4j_db.queries.e_prediccion_interacciones Amoxicilina Clavulanato

# Redis
PYTHONPATH=. python -m redis_db.queries.a_alertas_farmacovigilancia
PYTHONPATH=. python -m redis_db.queries.b_cadena_frio
PYTHONPATH=. python -m redis_db.queries.c_control_acceso

# Full demo
PYTHONPATH=. python run_demo.py
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| Cannot connect to MongoDB | `docker compose restart mongodb` |
| Cannot connect to Neo4j | Neo4j takes ~30s to start. Check: `docker compose logs neo4j` |
| Cannot connect to Redis | `docker compose restart redis && redis-cli ping` |
| Module import error | Always run from project root with `PYTHONPATH=.` |
