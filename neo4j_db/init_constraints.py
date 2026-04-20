"""
Inicializa los constraints de unicidad e índices del modelo Neo4j farmacéutico.
Ejecutar una sola vez antes de poblar la base de datos.

Uso:
    PYTHONPATH=. python3 neo4j_db/init_constraints.py
    NEO4J_URI=bolt://host:7687 NEO4J_PASSWORD=pass PYTHONPATH=. python3 neo4j_db/init_constraints.py
"""

from neo4j_db.connection import get_driver

# Constraints de unicidad — crean índice B-tree automáticamente
CONSTRAINTS = [
    (
        "med_nombre",
        "FOR (m:Medicamento) REQUIRE m.nombre_comercial IS UNIQUE",
        "Medicamento.nombre_comercial — unicidad de nombre comercial",
    ),
    (
        "pa_nombre",
        "FOR (pa:PrincipioActivo) REQUIRE pa.nombre IS UNIQUE",
        "PrincipioActivo.nombre — unicidad del principio activo",
    ),
    (
        "pac_id",
        "FOR (pac:Paciente) REQUIRE pac.id_anonimo IS UNIQUE",
        "Paciente.id_anonimo — unicidad de paciente anonimizado",
    ),
    (
        "ensayo_codigo",
        "FOR (e:EnsayoClinico) REQUIRE e.codigo_protocolo IS UNIQUE",
        "EnsayoClinico.codigo_protocolo — identificador único de protocolo",
    ),
]

# Índices adicionales para optimizar traversals
INDEXES = [
    (
        "idx_interaccion_severidad",
        "FOR ()-[i:INTERACTUA_CON]-() ON (i.severidad)",
        "Consultas (a) y (d): filtrar interacciones por severidad grave/contraindicada",
    ),
    (
        "idx_pa_via_metabolismo",
        "FOR (pa:PrincipioActivo) ON (pa.via_metabolismo)",
        "Consulta (c): agrupar PA por vía metabólica compartida",
    ),
    (
        "idx_med_estado",
        "FOR (m:Medicamento) ON (m.estado)",
        "Consultas (a) y (e): filtrar medicamentos activos rápidamente",
    ),
]


def create_constraints(session):
    for name, definition, description in CONSTRAINTS:
        cypher = f"CREATE CONSTRAINT {name} IF NOT EXISTS {definition}"
        session.run(cypher)
        print(f"  [ok]  Constraint '{name}' — {description}")


def create_indexes(session):
    for name, definition, description in INDEXES:
        cypher = f"CREATE INDEX {name} IF NOT EXISTS {definition}"
        session.run(cypher)
        print(f"  [ok]  Índice '{name}' — {description}")


def main():
    driver = get_driver()
    with driver.session() as session:
        server_info = driver.get_server_info()
        print(f"\nConectado a Neo4j {server_info.agent} en {server_info.address}\n")

        print("=== Constraints de unicidad ===")
        create_constraints(session)

        print("\n=== Índices adicionales ===")
        create_indexes(session)

    driver.close()
    print("\nSetup completado.")


if __name__ == "__main__":
    main()
