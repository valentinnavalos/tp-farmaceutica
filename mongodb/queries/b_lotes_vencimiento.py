"""
Consulta (b) — Lotes próximos a vencer con stock.

Lista todos los lotes que vencen en menos de 90 días y aún tienen stock
en distribuidores. Ordenados por fecha_vencimiento ascendente.

Usa el índice compuesto idx_lotes_vencimiento_stock para el range scan.

Uso:
    PYTHONPATH=. python3 -m mongodb.queries.b_lotes_vencimiento
    PYTHONPATH=. python3 -m mongodb.queries.b_lotes_vencimiento --dias 60
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from bson import json_util

from mongodb.connection import get_db


def lotes_proximos_a_vencer(dias: int = 90) -> list:
    db = get_db()
    hoy = datetime.now(tz=timezone.utc)
    limite = hoy + timedelta(days=dias)

    cursor = db.lotes.find(
        {
            "fecha_vencimiento": {"$lte": limite, "$gte": hoy},
            "estado_stock": {"$in": ["en_distribucion", "en_planta"]},
            "cantidad_disponible_total": {"$gt": 0},
        },
        {
            "numero_lote": 1,
            "medicamento_nombre": 1,
            "fecha_vencimiento": 1,
            "estado_stock": 1,
            "cantidad_disponible_total": 1,
            "cadena_distribucion.entidad_nombre": 1,
            "cadena_distribucion.stock_actual": 1,
        },
    ).sort("fecha_vencimiento", 1)

    return list(cursor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dias", type=int, default=90, help="Ventana en días (default: 90)")
    args = parser.parse_args()

    resultados = lotes_proximos_a_vencer(args.dias)
    print(f"\n=== Lotes que vencen en los próximos {args.dias} días con stock: {len(resultados)} ===\n")

    for lote in resultados:
        lote_json = json_util.loads(json_util.dumps(lote))
        vencimiento = lote_json.get("fecha_vencimiento", {})
        fecha_str = vencimiento.get("$date", "") if isinstance(vencimiento, dict) else str(vencimiento)
        print(
            f"  {lote_json['numero_lote']:20s}  "
            f"{lote_json.get('medicamento_nombre', ''):30s}  "
            f"vence: {fecha_str[:10]}  "
            f"stock: {lote_json.get('cantidad_disponible_total', 0)}"
        )

    if not resultados:
        print("  (sin resultados)")


if __name__ == "__main__":
    main()
