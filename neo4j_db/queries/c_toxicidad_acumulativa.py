"""
Consulta (c) — Toxicidad acumulativa en combinaciones de 3+ PA.

Detecta tríos de principios activos que comparten la misma vía metabólica
(mismas enzimas CYP) pero ningún par tiene interacción directa grave o
contraindicada. El riesgo surge de la saturación enzimática acumulativa.

Por qué es mejor en grafo: la condición NOT (a)-[:rel]-(b) es un patrón
nativo de Cypher evaluado como ausencia de arista. En SQL requiere un
NOT EXISTS sobre un self-join, extremadamente difícil de optimizar.

Uso:
    PYTHONPATH=. python3 -m neo4j_db.queries.c_toxicidad_acumulativa
    PYTHONPATH=. python3 -m neo4j_db.queries.c_toxicidad_acumulativa --via hepatica
"""

import argparse
from neo4j_db.connection import get_driver

CYPHER = """
MATCH (pa1:PrincipioActivo), (pa2:PrincipioActivo), (pa3:PrincipioActivo)
WHERE pa1.via_metabolismo = pa2.via_metabolismo
  AND pa2.via_metabolismo = pa3.via_metabolismo
  AND ($via IS NULL OR pa1.via_metabolismo = $via)
  AND id(pa1) < id(pa2) AND id(pa2) < id(pa3)
  AND NOT (pa1)-[:INTERACTUA_CON {severidad: 'grave'}]-(pa2)
  AND NOT (pa1)-[:INTERACTUA_CON {severidad: 'contraindicada'}]-(pa2)
  AND NOT (pa1)-[:INTERACTUA_CON {severidad: 'grave'}]-(pa3)
  AND NOT (pa1)-[:INTERACTUA_CON {severidad: 'contraindicada'}]-(pa3)
  AND NOT (pa2)-[:INTERACTUA_CON {severidad: 'grave'}]-(pa3)
  AND NOT (pa2)-[:INTERACTUA_CON {severidad: 'contraindicada'}]-(pa3)
MATCH (m1:Medicamento)-[:CONTIENE]->(pa1)
MATCH (m2:Medicamento)-[:CONTIENE]->(pa2)
MATCH (m3:Medicamento)-[:CONTIENE]->(pa3)
WHERE m1 <> m2 AND m2 <> m3 AND m1 <> m3
RETURN
  pa1.nombre                              AS pa1,
  pa2.nombre                              AS pa2,
  pa3.nombre                              AS pa3,
  pa1.via_metabolismo                     AS via_compartida,
  collect(DISTINCT m1.nombre_comercial)   AS meds_con_pa1,
  collect(DISTINCT m2.nombre_comercial)   AS meds_con_pa2,
  collect(DISTINCT m3.nombre_comercial)   AS meds_con_pa3,
  'toxicidad_acumulativa_' + pa1.via_metabolismo AS tipo_alerta
LIMIT 50
"""


def toxicidad_acumulativa(via: str | None = None) -> list:
    driver = get_driver()
    with driver.session() as session:
        result = session.run(CYPHER, via=via)
        rows = [r.data() for r in result]
    driver.close()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--via", default=None, help="Filtrar por vía metabólica (ej: hepatica, renal, mixta)")
    args = parser.parse_args()

    rows = toxicidad_acumulativa(via=args.via)
    filtro = f" — vía: {args.via}" if args.via else ""
    print(f"\n=== Combinaciones con toxicidad acumulativa{filtro}: {len(rows)} ===\n")

    if not rows:
        print("  (sin combinaciones detectadas)")
        return

    for r in rows:
        print(f"  {r['pa1']} + {r['pa2']} + {r['pa3']}")
        print(f"    Vía compartida : {r['via_compartida']}")
        print(f"    Meds con PA1   : {', '.join(r['meds_con_pa1'][:3])}")
        print(f"    Meds con PA2   : {', '.join(r['meds_con_pa2'][:3])}")
        print(f"    Meds con PA3   : {', '.join(r['meds_con_pa3'][:3])}")
        print()


if __name__ == "__main__":
    main()
