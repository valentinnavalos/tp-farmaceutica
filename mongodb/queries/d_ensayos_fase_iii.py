"""
Consulta (d) — Ensayos clínicos activos en Fase III.

Lista todos los ensayos clínicos activos en fase III con sus centros
participantes y cantidad de pacientes enrolados, ordenados por
total de pacientes descendente.

Usa el índice compuesto idx_ensayos_fase_estado sobre {fase, estado}.

Uso:
    PYTHONPATH=. python3 -m mongodb.queries.d_ensayos_fase_iii
"""

import sys

from mongodb.connection import get_db


PIPELINE_FASE_III = [
    {
        # Paso 1: Filtrado multivariante.
        # Selecciona documentos que cumplen simultaneamente
        # con la Fase "III" y el Estado "activo".
        "$match": {"fase": "III", "estado": "activo"}
    },
    {
        # Paso 2: Proyeccion con detalle de centros.
        # Expone el array completo de centros_participantes
        # junto al total consolidado de pacientes enrolados.
        "$project": {
            "_id": 0,
            "nombre_ensayo": "$nombre",
            "fase": 1,
            "estado": 1,
            "centros_participantes": 1,
            "total_pacientes_enrolados": 1,
            "fecha_inicio": 1,
            "fecha_fin_estimada": 1,
        }
    },
    {"$sort": {"total_pacientes_enrolados": -1}},
]


def ensayos_fase_iii() -> list:
    db = get_db()
    return list(db.ensayos_clinicos.aggregate(PIPELINE_FASE_III))


def main():
    resultados = ensayos_fase_iii()

    print(f"\n=== Ensayos clínicos activos Fase III: {len(resultados)} ===\n")

    if not resultados:
        print("  (sin ensayos Fase III activos)")
        return

    for r in resultados:
        centros = r.get("centros_participantes", [])
        print(f"  Ensayo:    {r['nombre_ensayo']}")
        print(f"  Pacientes: {r['total_pacientes_enrolados']}")
        print(f"  Centros:   {len(centros)}")
        for c in centros:
            print(f"    - {c.get('nombre','?')} ({c.get('pais','?')}) — {c.get('pacientes_enrolados',0)} pacientes")
        print()


if __name__ == "__main__":
    main()
