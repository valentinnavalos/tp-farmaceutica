"""
Inicializa las colecciones y los índices del modelo MongoDB farmacéutico.
Ejecutar una sola vez antes de poblar la base de datos.

Uso:
    python mongodb/init_indexes.py
    MONGO_URI=mongodb://user:pass@host:27017/farmaceutica python mongodb/init_indexes.py
"""

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid

from mongodb.connection import get_db

COLLECTIONS = [
    "medicamentos",
    "principios_activos",
    "lotes",
    "ensayos_clinicos",
    "efectos_adversos",
    "distribuidores",
]

INDEXES = [
    {
        "collection": "lotes",
        "keys": [("numero_lote", ASCENDING)],
        "options": {"unique": True, "name": "idx_lotes_numero"},
        "description": "Búsqueda por número de lote (consulta a) — unique",
    },
    {
        "collection": "lotes",
        "keys": [("fecha_vencimiento", ASCENDING), ("estado_stock", ASCENDING)],
        "options": {"name": "idx_lotes_vencimiento_stock"},
        "description": "Lotes próximos a vencer con stock (consulta b)",
    },
    {
        "collection": "efectos_adversos",
        "keys": [
            ("medicamento_id", ASCENDING),
            ("gravedad", ASCENDING),
            ("fecha_reporte", DESCENDING),
        ],
        "options": {"name": "idx_ea_med_gravedad_fecha"},
        "description": "Farmacovigilancia por medicamento, gravedad y período (consultas c y e)",
    },
]


def create_collections(db):
    existing = db.list_collection_names()
    for name in COLLECTIONS:
        if name in existing:
            print(f"  [skip]    Colección '{name}' ya existe")
        else:
            try:
                db.create_collection(name)
                print(f"  [ok]      Colección '{name}' creada")
            except CollectionInvalid:
                print(f"  [skip]    Colección '{name}' ya existe (race condition)")


def create_indexes(db):
    for idx in INDEXES:
        col = db[idx["collection"]]
        result = col.create_index(idx["keys"], **idx["options"])
        print(f"  [ok]      Índice '{result}' en '{idx['collection']}' — {idx['description']}")


def main():
    db = get_db()
    print(f"\nConectado a: {db.client.address} / base: {db.name}\n")

    print("=== Colecciones ===")
    create_collections(db)

    print("\n=== Índices ===")
    create_indexes(db)

    print("\nSetup completado.")


if __name__ == "__main__":
    main()
