"""
Consulta (c) — Resumen de efectos adversos por gravedad y país.

Obtiene el resumen de efectos adversos reportados para un medicamento en
el último año, agrupados por gravedad y país, con conteo de
hospitalizaciones. Usa el índice idx_ea_med_gravedad_fecha.

Uso:
    PYTHONPATH=. python3 -m mongodb.queries.c_efectos_adversos <medicamento_id>
"""

import json
import sys
from bson import ObjectId, json_util
from datetime import datetime, timedelta, timezone

from mongodb.connection import get_db


def efectos_adversos_resumen(medicamento_id: str) -> list:
    db = get_db()
    hace_1_anio = datetime.now(tz=timezone.utc) - timedelta(days=365)

    pipeline = [
        {
            "$match": {
                "medicamento_id": ObjectId(medicamento_id),
                "fecha_reporte": {"$gte": hace_1_anio},
            }
        },
        {
            "$group": {
                "_id": {"gravedad": "$gravedad", "pais": "$pais_reporte"},
                "total": {"$sum": 1},
                "hospitalizaciones": {
                    "$sum": {"$cond": ["$requirio_hospitalizacion", 1, 0]}
                },
            }
        },
        {"$sort": {"_id.gravedad": 1, "total": -1}},
        {
            "$group": {
                "_id": "$_id.gravedad",
                "paises": {
                    "$push": {
                        "pais": "$_id.pais",
                        "total": "$total",
                        "hospitalizaciones": "$hospitalizaciones",
                    }
                },
                "total_gravedad": {"$sum": "$total"},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    return list(db.efectos_adversos.aggregate(pipeline))


def main():
    if len(sys.argv) < 2:
        print("Uso: PYTHONPATH=. python3 -m mongodb.queries.c_efectos_adversos <medicamento_id>")
        sys.exit(1)

    med_id = sys.argv[1]
    resultados = efectos_adversos_resumen(med_id)

    print(f"\n=== Efectos adversos (último año) — medicamento: {med_id} ===\n")

    if not resultados:
        print("  (sin reportes)")
        return

    for grupo in resultados:
        g = json_util.loads(json_util.dumps(grupo))
        print(f"  Gravedad: {g['_id']}  (total: {g['total_gravedad']})")
        for p in g.get("paises", []):
            print(f"    {p['pais']:5s}  reportes: {p['total']:3d}  hospitalizaciones: {p['hospitalizaciones']}")
        print()


if __name__ == "__main__":
    main()
