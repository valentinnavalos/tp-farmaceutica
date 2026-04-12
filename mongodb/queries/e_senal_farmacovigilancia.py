"""
Consulta (e) — Señal de farmacovigilancia.

Detecta medicamentos con más de 3 reportes de efectos adversos graves
en el último semestre. Clasifica el nivel de alerta:
  - CRITICO  : >= 10 reportes graves
  - ALTO     : >= 6  reportes graves
  - MODERADO : >  3  reportes graves

Usa el índice idx_ea_med_gravedad_fecha.

Uso:
    PYTHONPATH=. python3 -m mongodb.queries.e_senal_farmacovigilancia
    PYTHONPATH=. python3 -m mongodb.queries.e_senal_farmacovigilancia --umbral 5
"""

import argparse
from datetime import datetime, timedelta, timezone
from bson import json_util

from mongodb.connection import get_db


def senal_farmacovigilancia(umbral: int = 3) -> list:
    db = get_db()
    hace_6_meses = datetime.now(tz=timezone.utc) - timedelta(days=180)

    pipeline = [
        {
            "$match": {
                "gravedad": "grave",
                "fecha_reporte": {"$gte": hace_6_meses},
            }
        },
        {
            "$group": {
                "_id": "$medicamento_id",
                "medicamento_nombre": {"$first": "$medicamento_nombre"},
                "total_reportes_graves": {"$sum": 1},
                "paises_afectados": {"$addToSet": "$pais_reporte"},
                "lotes_implicados": {"$addToSet": "$lote_numero"},
            }
        },
        {"$match": {"total_reportes_graves": {"$gt": umbral}}},
        {"$sort": {"total_reportes_graves": -1}},
        {
            "$project": {
                "medicamento_nombre": 1,
                "total_reportes_graves": 1,
                "paises_afectados": 1,
                "cantidad_lotes": {"$size": "$lotes_implicados"},
                "nivel_alerta": {
                    "$switch": {
                        "branches": [
                            {
                                "case": {"$gte": ["$total_reportes_graves", 10]},
                                "then": "CRITICO",
                            },
                            {
                                "case": {"$gte": ["$total_reportes_graves", 6]},
                                "then": "ALTO",
                            },
                        ],
                        "default": "MODERADO",
                    }
                },
            }
        },
    ]

    return list(db.efectos_adversos.aggregate(pipeline))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--umbral", type=int, default=3, help="Mínimo de reportes graves (default: 3)"
    )
    args = parser.parse_args()

    resultados = senal_farmacovigilancia(umbral=args.umbral)
    print(f"\n=== Señales de farmacovigilancia (últimos 6 meses, umbral > {args.umbral}): {len(resultados)} ===\n")

    COLORES = {"CRITICO": "\033[91m", "ALTO": "\033[93m", "MODERADO": "\033[94m", "RESET": "\033[0m"}

    for med in resultados:
        m = json_util.loads(json_util.dumps(med))
        nivel = m.get("nivel_alerta", "MODERADO")
        color = COLORES.get(nivel, "")
        reset = COLORES["RESET"]
        paises = ", ".join(m.get("paises_afectados", []))
        print(
            f"  {color}{nivel:8s}{reset}  "
            f"{m.get('medicamento_nombre', ''):30s}  "
            f"reportes: {m['total_reportes_graves']:3d}  "
            f"lotes: {m.get('cantidad_lotes', 0):2d}  "
            f"países: {paises}"
        )

    if not resultados:
        print("  (sin señales detectadas)")


if __name__ == "__main__":
    main()
