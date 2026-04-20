#!/usr/bin/env python3
"""
run_demo.py — Ejecuta las 10 consultas del TP con IDs reales de las bases de datos.

Uso:
    PYTHONPATH=. python run_demo.py

Requiere que ambas bases estén corriendo con datos ya cargados.
"""

import sys

# ── Obtener IDs reales ────────────────────────────────────────────────────────

def obtener_ids_mongodb():
    from mongodb.connection import get_db
    db = get_db()

    lote = db.lotes.find_one({}, {"numero_lote": 1})
    if not lote:
        print("[ERROR] No hay lotes en MongoDB. Ejecuta: cd seed && python generar_datos.py --all")
        sys.exit(1)
    numero_lote = lote["numero_lote"]

    med = db.medicamentos.find_one({}, {"_id": 1})
    medicamento_id = str(med["_id"])

    return numero_lote, medicamento_id


def obtener_ids_neo4j():
    from neo4j_db.connection import get_driver
    driver = get_driver()
    with driver.session() as s:
        # Paciente con interacciones
        r = s.run(
            "MATCH (p:Paciente)-[:TOMA]->(:Medicamento)-[:CONTIENE]->(pa1:PrincipioActivo) "
            "MATCH (pa1)-[:INTERACTUA_CON]-(:PrincipioActivo) "
            "RETURN p.id_anonimo AS id LIMIT 1"
        )
        row = r.single()
        pac_id = row["id"] if row else None

        if not pac_id:
            # fallback: cualquier paciente
            r2 = s.run("MATCH (p:Paciente) RETURN p.id_anonimo AS id LIMIT 1")
            row2 = r2.single()
            pac_id = row2["id"] if row2 else "PAC-2024-00001"

        # Principio activo con interacciones
        r3 = s.run(
            "MATCH (pa:PrincipioActivo)-[:INTERACTUA_CON]-() RETURN pa.nombre AS n LIMIT 1"
        )
        row3 = r3.single()
        pa_nombre = row3["n"] if row3 else None

        if not pa_nombre:
            r4 = s.run("MATCH (pa:PrincipioActivo) RETURN pa.nombre AS n LIMIT 1")
            row4 = r4.single()
            pa_nombre = row4["n"] if row4 else "Amoxicilina"

        # Dos PA para predicción de interacciones
        r5 = s.run(
            "MATCH (pa:PrincipioActivo)-[:INTERACTUA_CON]-() RETURN DISTINCT pa.nombre AS n LIMIT 2"
        )
        pa_nuevos = [row["n"] for row in r5]
        if len(pa_nuevos) < 2:
            pa_nuevos = [pa_nombre]

    driver.close()
    return pac_id, pa_nombre, pa_nuevos


# ── Runner ────────────────────────────────────────────────────────────────────

def separador(titulo):
    print("\n" + "=" * 70)
    print(f"  {titulo}")
    print("=" * 70)


def main():
    print("\n" + "=" * 70)
    print("  TP FARMACÉUTICA — Demo de las 10 consultas (v4)")
    print("=" * 70)

    print("\nObteniendo IDs desde las bases de datos...")
    numero_lote, medicamento_id = obtener_ids_mongodb()
    pac_id, pa_nombre, pa_nuevos = obtener_ids_neo4j()

    print(f"  numero_lote   = {numero_lote}")
    print(f"  medicamento_id= {medicamento_id}")
    print(f"  pac_id        = {pac_id}")
    print(f"  pa_nombre     = {pa_nombre}")
    print(f"  pa_nuevos     = {pa_nuevos}")

    # ── MongoDB ───────────────────────────────────────────────────────────────

    separador("MongoDB (a) — Trazabilidad completa de un lote")
    from mongodb.queries.a_trazabilidad import trazabilidad_lote
    from bson import json_util
    resultado = trazabilidad_lote(numero_lote)
    if resultado:
        print(json_util.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print(f"  Lote '{numero_lote}' no encontrado")

    separador("MongoDB (b) — Lotes próximos a vencer con stock")
    from mongodb.queries.b_lotes_vencimiento import lotes_proximos_vencer
    resultados_b = lotes_proximos_vencer(90)
    print(f"  {len(resultados_b)} lotes vencen en los próximos 90 días")
    print(f"  {'Lote':<20} {'Medicamento':<30} {'Días':>6} {'Estado'}")
    print("  " + "-" * 75)
    for r in resultados_b[:10]:
        print(f"  {r['numero_lote']:<20} {r['medicamento_nombre']:<30} {r['dias_para_vencer']:>6} {r['estado_stock']}")
    if len(resultados_b) > 10:
        print(f"  ... ({len(resultados_b) - 10} más)")

    separador("MongoDB (c) — Efectos adversos por país y gravedad")
    from mongodb.queries.c_efectos_adversos import resumen_efectos_adversos
    resultados_c = resumen_efectos_adversos(medicamento_id)
    print(f"  Medicamento: {medicamento_id[:8]}…  —  {len(resultados_c)} grupos")
    print(f"  {'Territorio':<15} {'Gravedad':<15} {'Total':>8}")
    print("  " + "-" * 42)
    for r in resultados_c:
        print(f"  {r['territorio']:<15} {r['nivel_gravedad']:<15} {r['total_casos_reportados']:>8}")

    separador("MongoDB (d) — Ensayos clínicos activos Fase III")
    from mongodb.queries.d_ensayos_fase_iii import ensayos_fase_iii
    resultados_d = ensayos_fase_iii()
    print(f"  {len(resultados_d)} ensayos en Fase III activos")
    for r in resultados_d:
        centros = r.get("centros_participantes", [])
        print(f"  {r['nombre_ensayo']}  —  {r['total_pacientes_enrolados']} pacientes  —  {len(centros)} centros")

    separador("MongoDB (e) — Señal de farmacovigilancia")
    from mongodb.queries.e_senal_farmacovigilancia import senal_farmacovigilancia
    resultados_e = senal_farmacovigilancia(3)
    print(f"  {len(resultados_e)} medicamentos con señal de alerta (>3 reportes graves en 6 meses)")
    for r in resultados_e:
        print(f"  [{r['nivel_alerta']:8s}]  {r['medicamento']}  —  {r['reportes_detectados']} reportes")

    # ── Neo4j ─────────────────────────────────────────────────────────────────

    separador("Neo4j (a) — Interacciones para una prescripción")
    from neo4j_db.queries.a_interacciones_prescripcion import interacciones_prescripcion
    rows_a = interacciones_prescripcion(pac_id)
    print(f"  Paciente: {pac_id}  —  {len(rows_a)} interacciones detectadas")
    for r in rows_a:
        print(f"  [{r['severidad']:15s}]  {r['principio_1']} ↔ {r['principio_2']}")

    separador("Neo4j (b) — Red completa de un principio activo")
    from neo4j_db.queries.b_red_principio_activo import red_principio_activo
    data_b = red_principio_activo(pa_nombre)
    if data_b:
        meds = [m for m in data_b["en_medicamentos"] if m]
        ints = [i for i in data_b["interacciones"] if i.get("con")]
        print(f"  PA: {data_b['principio_activo']}  —  {len(meds)} medicamentos  —  {len(ints)} interacciones")
        for i in ints[:5]:
            print(f"    [{i.get('severidad','?'):15s}]  ↔ {i.get('con','')}")
    else:
        print(f"  PA '{pa_nombre}' no encontrado en Neo4j")

    separador("Neo4j (c) — Toxicidad acumulativa (combinaciones de 3+ PA)")
    from neo4j_db.queries.c_toxicidad_acumulativa import toxicidad_acumulativa
    rows_c = toxicidad_acumulativa()
    print(f"  {len(rows_c)} combinaciones de 3 PA con vía metabólica compartida sin interacción directa grave")
    for r in rows_c[:5]:
        print(f"  {r['pa1']} + {r['pa2']} + {r['pa3']}  (vía: {r['via_compartida']})")

    separador("Neo4j (d) — El PA más peligroso de la red")
    from neo4j_db.queries.d_pa_mas_peligroso import pa_mas_peligroso
    rows_d = pa_mas_peligroso(10)
    print(f"  Top 10 por score de riesgo sistémico:")
    print(f"  {'PA':30s}  {'peligrosas':>10}  {'meds':>6}  {'score':>8}")
    print("  " + "-" * 60)
    for r in rows_d:
        print(
            f"  {r['principio_activo']:30s}  "
            f"{r['total_peligrosas']:>10}  "
            f"{r['presente_en_n_medicamentos']:>6}  "
            f"{r['score_riesgo_sistemico']:>8}"
        )

    separador("Neo4j (e) — Predicción de interacciones para nuevo medicamento")
    from neo4j_db.queries.e_prediccion_interacciones import prediccion_interacciones
    rows_e = prediccion_interacciones(pa_nuevos)
    print(f"  Nuevo med con PA: {', '.join(pa_nuevos)}")
    print(f"  {len(rows_e)} conflictos detectados")
    for r in rows_e[:10]:
        meds_af = ", ".join(r["medicamentos_afectados"][:3])
        print(f"  [{r['severidad']:15s}]  {r['pa_propio']} ↔ {r['pa_en_conflicto']}  →  {meds_af}")

    print("\n" + "=" * 70)
    print("  Demo completado. Todas las consultas ejecutadas correctamente.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
