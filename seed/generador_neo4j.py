"""
Generador de nodos y relaciones Neo4j.
Usa los mismos datos base que MongoDB para garantizar coherencia de IDs.
Schema según documento v4: constraints por nombre_comercial/nombre,
incluye MODIFICA_INTERACCION, enzimas_cyp, propiedades en relaciones.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from config import *
from datos_maestros import INTERACCIONES_MAESTRAS, AFECTA_MAESTRO, PATOLOGIAS

fake = Faker("es_AR")
fake.seed_instance(RANDOM_SEED)
random.seed(RANDOM_SEED)

HOY = datetime.now()

ALL_ENZIMAS = ["CYP3A4", "CYP2D6", "CYP2C9", "CYP2C19", "CYP1A2", "CYP2E1"]


class GeneradorNeo4j:
    def __init__(self, pa_docs, pa_id_map, med_docs, ensayo_docs):
        self.pa_docs     = pa_docs
        self.pa_id_map   = pa_id_map   # neo4j_node_id -> ObjectId
        self.med_docs    = med_docs
        self.ensayo_docs = ensayo_docs

    # ── Nodos ────────────────────────────────────────────────────────────────

    def gen_nodos_pa(self) -> list:
        nodos = []
        for pa in self.pa_docs:
            neo4j_id  = pa.get("neo4j_node_id", f"pa_{str(pa['_id'])}")
            enzimas   = pa["metabolismo"].get("enzimas", [])
            # garantizar al menos 1 enzima para consulta (c)
            if not enzimas:
                enzimas = [random.choice(ALL_ENZIMAS)]
            nodos.append({
                "label":           "PrincipioActivo",
                "mongo_id":        str(pa["_id"]),
                "neo4j_node_id":   neo4j_id,
                "nombre":          pa["nombre"],
                "familia_quimica": pa["familia_quimica"],
                "vida_media":      pa["vida_media"],
                "via_metabolismo": pa["metabolismo"]["via_principal"],
                "enzimas_cyp":     enzimas,
            })
        return nodos

    def gen_nodos_medicamento(self) -> list:
        nodos = []
        for med in self.med_docs:
            nodos.append({
                "label":            "Medicamento",
                "mongo_id":         str(med["_id"]),
                "nombre_comercial": med["nombre_comercial"],
                "nombre_generico":  med["nombre_generico"],
                "tipo":             med["tipo"],
                "condicion_venta":  med["condicion_venta"],
                "estado":           med["estado"],
            })
        return nodos

    def gen_nodos_patologia(self) -> list:
        nodos = []
        for pat in PATOLOGIAS:
            nodos.append({
                "label":     "Patologia",
                "nombre":    pat["nombre"],
                "categoria": pat["categoria"],
                "cie10":     pat.get("cie10", "Z99"),
            })
        return nodos

    def gen_nodos_ensayo(self) -> list:
        nodos = []
        for e in self.ensayo_docs:
            nodos.append({
                "label":            "EnsayoClinico",
                "mongo_id":         str(e["_id"]),
                "codigo_protocolo": e["codigo_protocolo"],
                "fase":             e["fase"],
                "estado":           e["estado"],
            })
        return nodos

    def gen_nodos_paciente(self) -> list:
        nodos = []
        usados = set()
        while len(nodos) < CANT_PACIENTES_NEO4J:
            id_pac = f"PAC-{HOY.year}-{str(random.randint(10000, 99999))}"
            if id_pac in usados:
                continue
            usados.add(id_pac)
            nodos.append({
                "label":      "Paciente",
                "id_anonimo": id_pac,
                "edad_aprox": random.randint(18, 85),
                "sexo":       random.choice(["M", "F", "NB", "NE"]),
            })
        return nodos

    # ── Relaciones ───────────────────────────────────────────────────────────

    def gen_relaciones_contiene(self) -> list:
        rels = []
        for med in self.med_docs:
            for pa_emb in med.get("principios_activos", []):
                # buscar PA por ObjectId para obtener su nombre
                pa_nombre = pa_emb["nombre"]
                rels.append({
                    "tipo":       "CONTIENE",
                    "from_nombre_comercial": med["nombre_comercial"],
                    "to_nombre_pa":          pa_nombre,
                    "props": {
                        "dosis": pa_emb["dosis_en_formulacion"],
                        "rol":   pa_emb["rol"],
                    },
                })
        return rels

    def gen_relaciones_interactua(self) -> list:
        """
        Genera 200 relaciones INTERACTUA_CON.
        Garantiza ≥20 con severidad grave o contraindicada.
        """
        rels   = []
        vistos = set()

        # Interacciones maestras reales
        for inter in INTERACCIONES_MAESTRAS:
            pa1_id = inter["pa1"]
            pa2_id = inter["pa2"]
            clave  = tuple(sorted([pa1_id, pa2_id]))
            if clave in vistos:
                continue
            if pa1_id not in self.pa_id_map or pa2_id not in self.pa_id_map:
                continue
            vistos.add(clave)

            # buscar nombres de PA
            pa1_nombre = next((p["nombre"] for p in self.pa_docs if p.get("neo4j_node_id") == pa1_id), pa1_id)
            pa2_nombre = next((p["nombre"] for p in self.pa_docs if p.get("neo4j_node_id") == pa2_id), pa2_id)

            rels.append({
                "tipo":       "INTERACTUA_CON",
                "from_nombre":pa1_nombre,
                "to_nombre":  pa2_nombre,
                "props": {
                    "tipo":      inter["tipo"],
                    "severidad": inter["severidad"],
                    "mecanismo": inter["mecanismo"],
                    "evidencia": inter["evidencia"],
                },
            })

        # Interacciones sintéticas hasta 200, garantizando ≥20 peligrosas
        graves_generadas = sum(1 for r in rels if r["props"]["severidad"] in ["grave", "contraindicada"])
        intentos = 0
        while len(rels) < 200 and intentos < 5000:
            intentos += 1
            pa1 = random.choice(self.pa_docs)
            pa2 = random.choice(self.pa_docs)
            if pa1["_id"] == pa2["_id"]:
                continue
            clave = tuple(sorted([pa1["nombre"], pa2["nombre"]]))
            if clave in vistos:
                continue
            vistos.add(clave)

            # forzar graves hasta cumplir mínimo de 20
            if graves_generadas < 20:
                sev = random.choice(["grave", "contraindicada"])
                graves_generadas += 1
            else:
                sev = random.choices(
                    ["leve", "moderada", "grave", "contraindicada"],
                    weights=[35, 40, 18, 7]
                )[0]

            rels.append({
                "tipo":       "INTERACTUA_CON",
                "from_nombre":pa1["nombre"],
                "to_nombre":  pa2["nombre"],
                "props": {
                    "tipo":      random.choice(["potenciacion","antagonismo","toxicidad","sinergismo"]),
                    "severidad": sev,
                    "mecanismo": f"Interacción entre {pa1['nombre']} y {pa2['nombre']} por metabolismo compartido.",
                    "evidencia": random.choice(["in_vitro","caso_reporte","consenso_experto","ensayo_clinico"]),
                },
            })

        return rels

    def gen_relaciones_afecta(self) -> list:
        rels = []
        pat_nombres = {p["nombre"] for p in PATOLOGIAS}
        for af in AFECTA_MAESTRO:
            if af["pa"] not in self.pa_id_map:
                continue
            if af["pat"] not in pat_nombres:
                continue
            pa_nombre = next((p["nombre"] for p in self.pa_docs if p.get("neo4j_node_id") == af["pa"]), af["pa"])
            rels.append({
                "tipo":      "AFECTA",
                "from_nombre":pa_nombre,
                "to_pat":     af["pat"],
                "props": {
                    "tipo_efecto": af["tipo"],
                    "descripcion": f"Efecto {af['tipo']} sobre {af['pat'].replace('_',' ')}.",
                },
            })
        return rels

    def gen_relaciones_estudia(self) -> list:
        rels = []
        for e in self.ensayo_docs:
            med = next((m for m in self.med_docs if m["_id"] == e["medicamento_id"]), None)
            if not med:
                continue
            rels.append({
                "tipo":            "ESTUDIA",
                "from_codigo":     e["codigo_protocolo"],
                "to_nombre_comercial": med["nombre_comercial"],
                "props":           {},
            })
        return rels

    def gen_relaciones_modifica_interaccion(self, rels_interactua: list) -> list:
        """
        Nueva relación: EnsayoClinico -[:MODIFICA_INTERACCION]-> PrincipioActivo.
        Genera al menos 5 (un ensayo por las primeras 5 interacciones graves).
        """
        rels = []
        peligrosas = [r for r in rels_interactua if r["props"]["severidad"] in ["grave", "contraindicada"]]
        ensayos_activos = [e for e in self.ensayo_docs if e["estado"] == "activo"]

        for i, inter in enumerate(peligrosas[:5]):
            if i >= len(ensayos_activos):
                break
            ensayo = ensayos_activos[i]
            rels.append({
                "tipo":        "MODIFICA_INTERACCION",
                "from_codigo": ensayo["codigo_protocolo"],
                "to_nombre_pa":inter["from_nombre"],
                "props": {
                    "pa1_id":         inter["from_nombre"],
                    "pa2_id":         inter["to_nombre"],
                    "nueva_severidad":random.choice(["moderada", "grave"]),
                    "fecha_evidencia": HOY.strftime("%Y-%m-%d"),
                },
            })
        return rels

    def gen_relaciones_toma(self, pacientes: list, interacciones: list) -> list:
        """
        Relaciones TOMA con propiedades: fecha_inicio, dosis_diaria, prescriptor.
        Garantiza ≥10 pacientes con combinaciones peligrosas.
        """
        rels = []

        # Index: pa_nombre -> medicamentos que lo contienen
        pa_a_meds = {}
        for med in self.med_docs:
            for pa_emb in med.get("principios_activos", []):
                pa_a_meds.setdefault(pa_emb["nombre"], []).append(med)

        pares_peligrosos = []
        for rel in interacciones:
            if rel["props"]["severidad"] in ["grave", "contraindicada"]:
                meds1 = pa_a_meds.get(rel["from_nombre"], [])
                meds2 = pa_a_meds.get(rel["to_nombre"], [])
                if meds1 and meds2:
                    pares_peligrosos.append((meds1[0], meds2[0]))

        for i, pac in enumerate(pacientes):
            n_meds = random.randint(2, 5)

            if i < PACIENTES_CON_INTERACCION and pares_peligrosos:
                par = random.choice(pares_peligrosos)
                meds_asignados = list(par)
                extras = [m for m in random.sample(self.med_docs, k=min(n_meds - 2, len(self.med_docs)))
                          if m not in meds_asignados]
                meds_asignados += extras
            else:
                meds_asignados = random.sample(self.med_docs, k=min(n_meds, len(self.med_docs)))

            fecha_inicio = HOY - timedelta(days=random.randint(10, 365))
            for med in meds_asignados:
                rels.append({
                    "tipo":       "TOMA",
                    "from_pac":   pac["id_anonimo"],
                    "to_nombre_comercial": med["nombre_comercial"],
                    "props": {
                        "fecha_inicio":fecha_inicio.strftime("%Y-%m-%d"),
                        "dosis_diaria":f"{random.choice([100,250,500,750,1000])}mg",
                        "prescriptor": random.choice(["cardiologo","internista","neurologo","clinico","oncologo"]),
                    },
                })
        return rels

    # ── Exportar a Cypher ────────────────────────────────────────────────────

    def exportar_cypher(self, path: str, nodos_pa, nodos_med, nodos_pat,
                         nodos_ensayo, nodos_pac, rels_contiene, rels_interactua,
                         rels_afecta, rels_estudia, rels_toma, rels_modifica=None):
        lines = []

        lines += [
            "// ================================================================",
            "// TP Tema 13 — Empresa Farmacéutica",
            "// Script de carga Neo4j — generado automáticamente (v4)",
            f"// Fecha: {HOY.strftime('%Y-%m-%d %H:%M')}",
            "// ================================================================",
            "",
            "// ── Constraints e índices (según documento v4) ──────────────────",
            "CREATE CONSTRAINT med_nombre IF NOT EXISTS",
            "  FOR (m:Medicamento) REQUIRE m.nombre_comercial IS UNIQUE;",
            "CREATE CONSTRAINT pa_nombre IF NOT EXISTS",
            "  FOR (pa:PrincipioActivo) REQUIRE pa.nombre IS UNIQUE;",
            "CREATE CONSTRAINT pac_id IF NOT EXISTS",
            "  FOR (p:Paciente) REQUIRE p.id_anonimo IS UNIQUE;",
            "CREATE CONSTRAINT ensayo_codigo IF NOT EXISTS",
            "  FOR (e:EnsayoClinico) REQUIRE e.codigo_protocolo IS UNIQUE;",
            "",
            "CREATE INDEX idx_interaccion_severidad IF NOT EXISTS",
            "  FOR ()-[i:INTERACTUA_CON]-() ON (i.severidad);",
            "CREATE INDEX idx_pa_via_metabolismo IF NOT EXISTS",
            "  FOR (pa:PrincipioActivo) ON (pa.via_metabolismo);",
            "CREATE INDEX idx_med_estado IF NOT EXISTS",
            "  FOR (m:Medicamento) ON (m.estado);",
            "",
        ]

        # Nodos PrincipioActivo
        lines += ["// ── Nodos :PrincipioActivo ──────────────────────────────────", ""]
        for n in nodos_pa:
            enzimas_str = "[" + ", ".join(f"'{e}'" for e in n["enzimas_cyp"]) + "]"
            lines.append(
                f"MERGE (pa:PrincipioActivo {{nombre: {_q(n['nombre'])}}}) "
                f"SET pa.familia_quimica = {_q(n['familia_quimica'])}, "
                f"pa.vida_media = {n['vida_media']}, "
                f"pa.via_metabolismo = {_q(n['via_metabolismo'])}, "
                f"pa.enzimas_cyp = {enzimas_str};"
            )
        lines.append("")

        # Nodos Medicamento
        lines += ["// ── Nodos :Medicamento ──────────────────────────────────────", ""]
        for n in nodos_med:
            lines.append(
                f"MERGE (m:Medicamento {{nombre_comercial: {_q(n['nombre_comercial'])}}}) "
                f"SET m.nombre_generico = {_q(n['nombre_generico'])}, "
                f"m.tipo = {_q(n['tipo'])}, "
                f"m.condicion_venta = {_q(n['condicion_venta'])}, "
                f"m.estado = {_q(n['estado'])};"
            )
        lines.append("")

        # Nodos Patologia
        lines += ["// ── Nodos :Patologia ────────────────────────────────────────", ""]
        for n in nodos_pat:
            lines.append(
                f"MERGE (p:Patologia {{nombre: {_q(n['nombre'])}}}) "
                f"SET p.categoria = {_q(n['categoria'])}, "
                f"p.cie10 = {_q(n['cie10'])};"
            )
        lines.append("")

        # Nodos EnsayoClinico
        lines += ["// ── Nodos :EnsayoClinico ────────────────────────────────────", ""]
        for n in nodos_ensayo:
            lines.append(
                f"MERGE (e:EnsayoClinico {{codigo_protocolo: {_q(n['codigo_protocolo'])}}}) "
                f"SET e.mongo_id = {_q(n['mongo_id'])}, "
                f"e.fase = {_q(n['fase'])}, "
                f"e.estado = {_q(n['estado'])};"
            )
        lines.append("")

        # Nodos Paciente
        lines += ["// ── Nodos :Paciente ─────────────────────────────────────────", ""]
        for n in nodos_pac:
            lines.append(
                f"MERGE (pac:Paciente {{id_anonimo: {_q(n['id_anonimo'])}}}) "
                f"SET pac.edad_aprox = {n['edad_aprox']}, "
                f"pac.sexo = {_q(n['sexo'])};"
            )
        lines.append("")

        # Relaciones CONTIENE
        lines += ["// ── Relaciones [:CONTIENE] ──────────────────────────────────", ""]
        for r in rels_contiene:
            lines.append(
                f"MATCH (m:Medicamento {{nombre_comercial: {_q(r['from_nombre_comercial'])}}}), "
                f"(pa:PrincipioActivo {{nombre: {_q(r['to_nombre_pa'])}}}) "
                f"MERGE (m)-[c:CONTIENE]->(pa) "
                f"SET c.dosis = {_q(r['props']['dosis'])}, c.rol = {_q(r['props']['rol'])};"
            )
        lines.append("")

        # Relaciones INTERACTUA_CON
        lines += ["// ── Relaciones [:INTERACTUA_CON] ────────────────────────────", ""]
        for r in rels_interactua:
            lines.append(
                f"MATCH (pa1:PrincipioActivo {{nombre: {_q(r['from_nombre'])}}}), "
                f"(pa2:PrincipioActivo {{nombre: {_q(r['to_nombre'])}}}) "
                f"MERGE (pa1)-[i:INTERACTUA_CON]->(pa2) "
                f"SET i.tipo = {_q(r['props']['tipo'])}, "
                f"i.severidad = {_q(r['props']['severidad'])}, "
                f"i.mecanismo = {_q(r['props']['mecanismo'])}, "
                f"i.evidencia = {_q(r['props']['evidencia'])};"
            )
        lines.append("")

        # Relaciones AFECTA
        lines += ["// ── Relaciones [:AFECTA] ────────────────────────────────────", ""]
        for r in rels_afecta:
            lines.append(
                f"MATCH (pa:PrincipioActivo {{nombre: {_q(r['from_nombre'])}}}), "
                f"(pat:Patologia {{nombre: {_q(r['to_pat'])}}}) "
                f"MERGE (pa)-[a:AFECTA]->(pat) "
                f"SET a.tipo_efecto = {_q(r['props']['tipo_efecto'])}, "
                f"a.descripcion = {_q(r['props']['descripcion'])};"
            )
        lines.append("")

        # Relaciones ESTUDIA
        lines += ["// ── Relaciones [:ESTUDIA] ───────────────────────────────────", ""]
        for r in rels_estudia:
            lines.append(
                f"MATCH (e:EnsayoClinico {{codigo_protocolo: {_q(r['from_codigo'])}}}), "
                f"(m:Medicamento {{nombre_comercial: {_q(r['to_nombre_comercial'])}}}) "
                f"MERGE (e)-[:ESTUDIA]->(m);"
            )
        lines.append("")

        # Relaciones MODIFICA_INTERACCION (nueva en v4)
        if rels_modifica:
            lines += ["// ── Relaciones [:MODIFICA_INTERACCION] (v4) ────────────────", ""]
            for r in rels_modifica:
                lines.append(
                    f"MATCH (e:EnsayoClinico {{codigo_protocolo: {_q(r['from_codigo'])}}}), "
                    f"(pa:PrincipioActivo {{nombre: {_q(r['to_nombre_pa'])}}}) "
                    f"MERGE (e)-[mi:MODIFICA_INTERACCION]->(pa) "
                    f"SET mi.pa1_id = {_q(r['props']['pa1_id'])}, "
                    f"mi.pa2_id = {_q(r['props']['pa2_id'])}, "
                    f"mi.nueva_severidad = {_q(r['props']['nueva_severidad'])}, "
                    f"mi.fecha_evidencia = date({_q(r['props']['fecha_evidencia'])});"
                )
            lines.append("")

        # Relaciones TOMA
        lines += ["// ── Relaciones [:TOMA] ──────────────────────────────────────", ""]
        for r in rels_toma:
            lines.append(
                f"MATCH (pac:Paciente {{id_anonimo: {_q(r['from_pac'])}}}), "
                f"(m:Medicamento {{nombre_comercial: {_q(r['to_nombre_comercial'])}}}) "
                f"MERGE (pac)-[t:TOMA]->(m) "
                f"SET t.fecha_inicio = date({_q(r['props']['fecha_inicio'])}), "
                f"t.dosis_diaria = {_q(r['props']['dosis_diaria'])}, "
                f"t.prescriptor = {_q(r['props']['prescriptor'])};"
            )
        lines.append("")
        lines.append("// ── Fin del script ──────────────────────────────────────────")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def _q(val) -> str:
    if val is None:
        return "null"
    escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
