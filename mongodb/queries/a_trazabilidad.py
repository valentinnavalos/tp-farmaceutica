"""
Consulta (a) — Trazabilidad completa de un lote.

Dado un número de lote, reconstruye el camino completo desde la planta
de producción hasta los distribuidores y puntos de dispensación actuales.

La cadena de distribución está embebida en el documento del lote, por lo
que basta un único findOne() — sin $lookup ni $graphLookup.

Uso:
    PYTHONPATH=. python3 -m mongodb.queries.a_trazabilidad LOT-2024-00451
"""

import json
import sys
from bson import json_util

from mongodb.connection import get_db


def trazabilidad_lote(numero_lote: str) -> dict | None:
    db = get_db()
    return db.lotes.find_one(
        {"numero_lote": numero_lote},
        {
            "numero_lote": 1,
            "medicamento_nombre": 1,
            "fabricacion": 1,
            "fecha_vencimiento": 1,
            "cadena_distribucion": 1,
            "cantidad_disponible_total": 1,
        },
    )


def main():
    if len(sys.argv) < 2:
        print("Uso: PYTHONPATH=. python3 -m mongodb.queries.a_trazabilidad <numero_lote>")
        sys.exit(1)

    numero_lote = sys.argv[1]
    resultado = trazabilidad_lote(numero_lote)

    if resultado is None:
        print(f"No se encontró el lote '{numero_lote}'")
        sys.exit(1)

    print(f"\n=== Trazabilidad del lote: {numero_lote} ===\n")
    print(json.dumps(json_util.loads(json_util.dumps(resultado)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
