"""
Consulta (d) — Ensayos clínicos activos en fase III.

Lista todos los ensayos clínicos activos en fase III con sus centros
participantes y cantidad de pacientes enrolados, ordenados por
total_pacientes_enrolados descendente.

Los centros participantes están embebidos, por lo que no requiere $lookup
para la consulta principal. La variante con --detalle incluye el
medicamento estudiado mediante un $lookup adicional.

Uso:
    PYTHONPATH=. python3 -m mongodb.queries.d_ensayos_fase_iii
    PYTHONPATH=. python3 -m mongodb.queries.d_ensayos_fase_iii --detalle
"""

import argparse
import json
from bson import json_util

from mongodb.connection import get_db


def ensayos_fase_iii(con_detalle_medicamento: bool = False) -> list:
    db = get_db()

    if not con_detalle_medicamento:
        cursor = db.ensayos_clinicos.find(
            {"fase": "III", "estado": "activo"},
            {
                "nombre": 1,
                "codigo_protocolo": 1,
                "hipotesis": 1,
                "centros_participantes": 1,
                "total_pacientes_enrolados": 1,
                "fecha_inicio": 1,
                "fecha_fin_estimada": 1,
            },
        ).sort("total_pacientes_enrolados", -1)
        return list(cursor)

    pipeline = [
        {"$match": {"fase": "III", "estado": "activo"}},
        {
            "$lookup": {
                "from": "medicamentos",
                "localField": "medicamento_id",
                "foreignField": "_id",
                "as": "medicamento",
            }
        },
        {"$unwind": "$medicamento"},
        {
            "$project": {
                "nombre": 1,
                "codigo_protocolo": 1,
                "fase": 1,
                "total_pacientes_enrolados": 1,
                "centros_participantes": 1,
                "fecha_inicio": 1,
                "fecha_fin_estimada": 1,
                "medicamento.nombre_comercial": 1,
                "medicamento.principios_activos": 1,
            }
        },
        {"$sort": {"total_pacientes_enrolados": -1}},
    ]
    return list(db.ensayos_clinicos.aggregate(pipeline))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--detalle", action="store_true", help="Incluir detalle del medicamento estudiado"
    )
    args = parser.parse_args()

    resultados = ensayos_fase_iii(con_detalle_medicamento=args.detalle)
    print(f"\n=== Ensayos clínicos activos fase III: {len(resultados)} ===\n")

    for ensayo in resultados:
        e = json_util.loads(json_util.dumps(ensayo))
        centros = e.get("centros_participantes", [])
        print(
            f"  {e.get('codigo_protocolo', ''):20s}  "
            f"{e.get('nombre', ''):30s}  "
            f"pacientes: {e.get('total_pacientes_enrolados', 0):4d}  "
            f"centros: {len(centros)}"
        )
        if args.detalle and "medicamento" in e:
            med = e["medicamento"]
            print(f"    Medicamento: {med.get('nombre_comercial', '')}")

    if not resultados:
        print("  (sin resultados)")


if __name__ == "__main__":
    main()
