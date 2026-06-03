# Generador de datos — TP Farmacéutica (Tema 13)

## Estructura
```
seed/
├── config.py            # Parámetros de volumen y conexión
├── datos_maestros.py    # PA, interacciones y patologías reales
├── generador_mongo.py   # Generador de documentos MongoDB
├── generador_neo4j.py   # Generador de nodos y relaciones Neo4j
├── generador_redis.py   # Generador de datos Redis (alertas, streams, control de acceso)
├── generar_datos.py     # Script principal (entry point)
└── output/
    ├── mongodb/         # JSONs para mongoimport
    └── neo4j/           # Script .cypher para cypher-shell
```

## Uso rápido (con Docker — flujo recomendado)
```bash
# Generar + cargar en las 3 bases (MongoDB + Neo4j + Redis)
docker compose exec api python seed/generar_datos.py --all --redis-load

# Solo MongoDB y Neo4j (sin Redis)
docker compose exec api python seed/generar_datos.py --all

# Solo MongoDB
docker compose exec api python seed/generar_datos.py --mongo-load

# Solo Neo4j
docker compose exec api python seed/generar_datos.py --neo4j-load
```

## Carga manual (alternativa)
```bash
# MongoDB
mongoimport --db farmaceutica_tp --collection principios_activos --file output/mongodb/principios_activos.json
mongoimport --db farmaceutica_tp --collection medicamentos       --file output/mongodb/medicamentos.json
mongoimport --db farmaceutica_tp --collection distribuidores     --file output/mongodb/distribuidores.json
mongoimport --db farmaceutica_tp --collection lotes              --file output/mongodb/lotes.json
mongoimport --db farmaceutica_tp --collection ensayos_clinicos   --file output/mongodb/ensayos_clinicos.json
mongoimport --db farmaceutica_tp --collection efectos_adversos   --file output/mongodb/efectos_adversos.json

# Neo4j
cypher-shell -u neo4j -p password --file output/neo4j/carga_neo4j.cypher
```

## Garantías del enunciado
- 80 principios activos (35 reales + 45 sintéticos)
- 200 medicamentos (genéricos, biológicos, dispositivos)
- 150 lotes con cadenas de 3 a 8 eslabones
- 20 ensayos clínicos (7 fase III activos)
- 300 efectos adversos
- 6 medicamentos con señal de farmacovigilancia (>3 EA graves en semestre)
- 20 lotes próximos a vencer (<90 días)
- 150 relaciones INTERACTUA_CON (30 maestras reales + 120 sintéticas)
- 10 pacientes con combinaciones peligrosas para validar consulta (a)
