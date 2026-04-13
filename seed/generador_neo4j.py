"""
Generador de nodos y relaciones Neo4j.
Usa los mismos datos base que MongoDB para garantizar coherencia de IDs.
Produce tanto scripts .cypher como carga directa via driver bolt.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from config import *
from datos_maestros import (
    INTERACCIONES_MAESTRAS, AFECTA_MAESTRO, PATOLOGIAS
)

fake = Faker("es_AR")
fake.seed_instance(RANDOM_SEED)
random.seed(RANDOM_SEED)

HOY = datetime.now()


class GeneradorNeo4j:
    """
    Genera los comandos Cypher y/o carga directamente en Neo4j.
    Recibe los documentos MongoDB ya generados para reutilizar IDs.
    """

    def __init__(self, pa_docs, pa_id_map, med_docs, ensayo_docs):
        self.pa_docs     = pa_docs
        self.pa_id_map   = pa_id_map   # neo4j_node_id -> ObjectId (de MongoDB)
        self.med_docs    = med_docs
        self.ensayo_docs = ensayo_docs
        self.cypher_lines = []         # buffer para el archivo .cypher

    # ── Nodos ────────────────────────────────────────────────────────────────

    def gen_nodos_pa(self) -> list:
        """Retorna lista de dicts listos para CREATE en Neo4j."""
        nodos = []
        for pa in self.pa_docs:
            neo4j_id = pa.get("neo4j_node_id", f"pa_{str(pa['_id'])}")
            nodos.append({
                "label":           "PrincipioActivo",
                "mongo_id":        str(pa["_id"]),
                "neo4j_node_id":   neo4j_id,
                "nombre":          pa["nombre"],
                "familia_quimica": pa["familia_quimica"],
                "vida_media_horas":pa["vida_media_horas"],
                "via_metabolismo": pa["metabolismo"]["via_principal"],
            })
        return nodos

    def gen_nodos_medicamento(self) -> list:
        """Retorna nodos :Medicamento — versión liviana de los documentos MongoDB."""
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
                "cie10":     pat["cie10"],
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
        """Genera 50 pacientes ficticios y anonimizados."""
        nodos = []
        for i in range(CANT_PACIENTES_NEO4J):
            nodos.append({
                "label":      "Paciente",
                "id_anonimo": f"PAC-{HOY.year}-{str(random.randint(10000, 99999))}",
                "edad_aprox": random.randint(18, 85),
                "sexo":       random.choice(["M", "F", "NB", "NE"]),
            })
        return nodos

    # ── Relaciones ───────────────────────────────────────────────────────────

    def gen_relaciones_contiene(self) -> list:
        """
        Genera relaciones CONTIENE desde los PA embebidos en cada medicamento.
        Así los IDs son 100% coherentes con MongoDB.
        """
        rels = []
        for med in self.med_docs:
            for pa_emb in med.get("principios_activos", []):
                rels.append({
                    "tipo":       "CONTIENE",
                    "from_label": "Medicamento",
                    "from_key":   "mongo_id",
                    "from_val":   str(med["_id"]),
                    "to_label":   "PrincipioActivo",
                    "to_key":     "mongo_id",
                    "to_val":     str(pa_emb["pa_id"]),
                    "props": {
                        "dosis": pa_emb["dosis_en_formulacion"],
                        "rol":   pa_emb["rol"],
                    },
                })
        return rels

    def gen_relaciones_interactua(self) -> list:
        """
        Genera relaciones INTERACTUA_CON a partir de los datos maestros.
        Filtra duplicados y garantiza el mínimo de interacciones graves.
        """
        rels   = []
        vistos = set()

        # Primero: interacciones maestras (clínicamente reales)
        for inter in INTERACCIONES_MAESTRAS:
            pa1_id = inter["pa1"]
            pa2_id = inter["pa2"]
            clave  = tuple(sorted([pa1_id, pa2_id]))
            if clave in vistos or inter["mecanismo"] == "duplicado":
                continue
            vistos.add(clave)

            if pa1_id not in self.pa_id_map or pa2_id not in self.pa_id_map:
                continue

            rels.append({
                "tipo":       "INTERACTUA_CON",
                "from_label": "PrincipioActivo",
                "from_key":   "neo4j_node_id",
                "from_val":   pa1_id,
                "to_label":   "PrincipioActivo",
                "to_key":     "neo4j_node_id",
                "to_val":     pa2_id,
                "props": {
                    "tipo":      inter["tipo"],
                    "severidad": inter["severidad"],
                    "mecanismo": inter["mecanismo"],
                    "evidencia": inter["evidencia"],
                },
            })

        # Completar con interacciones sintéticas hasta 150 total
        pa_list = self.pa_docs
        intentos = 0
        while len(rels) < 150 and intentos < 2000:
            intentos += 1
            pa1 = random.choice(pa_list)
            pa2 = random.choice(pa_list)
            if pa1["_id"] == pa2["_id"]:
                continue
            id1 = pa1.get("neo4j_node_id", str(pa1["_id"]))
            id2 = pa2.get("neo4j_node_id", str(pa2["_id"]))
            clave = tuple(sorted([id1, id2]))
            if clave in vistos:
                continue
            vistos.add(clave)

            sev = random.choices(
                ["leve", "moderada", "grave", "contraindicada"],
                weights=[35, 40, 20, 5]
            )[0]

            rels.append({
                "tipo":       "INTERACTUA_CON",
                "from_label": "PrincipioActivo",
                "from_key":   "neo4j_node_id",
                "from_val":   id1,
                "to_label":   "PrincipioActivo",
                "to_key":     "neo4j_node_id",
                "to_val":     id2,
                "props": {
                    "tipo":      random.choice(["potenciacion","antagonismo","toxicidad","sinergismo"]),
                    "severidad": sev,
                    "mecanismo": f"Interacción entre {pa1['nombre']} y {pa2['nombre']} vía metabolismo compartido.",
                    "evidencia": random.choice(["in_vitro","caso_reporte","consenso_experto"]),
                },
            })

        return rels

    def gen_relaciones_afecta(self) -> list:
        """Genera relaciones AFECTA entre PA y Patologías."""
        rels        = []
        pat_nombres = {p["nombre"] for p in PATOLOGIAS}

        for af in AFECTA_MAESTRO:
            if af["pa"] not in self.pa_id_map:
                continue
            if af["pat"] not in pat_nombres:
                continue
            rels.append({
                "tipo":       "AFECTA",
                "from_label": "PrincipioActivo",
                "from_key":   "neo4j_node_id",
                "from_val":   af["pa"],
                "to_label":   "Patologia",
                "to_key":     "nombre",
                "to_val":     af["pat"],
                "props": {
                    "tipo_efecto": af["tipo"],
                    "descripcion": f"Efecto {af['tipo']} sobre {af['pat'].replace('_',' ')}.",
                },
            })
        return rels

    def gen_relaciones_estudia(self) -> list:
        """Genera relaciones ESTUDIA entre EnsayoClinico y Medicamento."""
        rels = []
        for e in self.ensayo_docs:
            rels.append({
                "tipo":       "ESTUDIA",
                "from_label": "EnsayoClinico",
                "from_key":   "codigo_protocolo",
                "from_val":   e["codigo_protocolo"],
                "to_label":   "Medicamento",
                "to_key":     "mongo_id",
                "to_val":     str(e["medicamento_id"]),
                "props":      {},
            })
        return rels

    def gen_relaciones_toma(self, pacientes: list, interacciones: list) -> list:
        """
        Genera relaciones TOMA entre Paciente y Medicamento.
        Garantiza que 10 pacientes tengan combinaciones con interacciones conocidas.
        """
        rels = []

        # Obtener pares de medicamentos que interactúan (con riesgo)
        pa_mongo_to_neo4j = {
            str(pa["_id"]): pa.get("neo4j_node_id", str(pa["_id"]))
            for pa in self.pa_docs
        }
        meds_con_interaccion = []
        for rel in interacciones:
            if rel["props"]["severidad"] in ["grave", "contraindicada"]:
                pa_from = rel["from_val"]
                pa_to   = rel["to_val"]
                meds_1 = [m for m in self.med_docs
                          if any(pa_mongo_to_neo4j.get(str(p["pa_id"]),"") == pa_from
                                 for p in m.get("principios_activos", []))]
                meds_2 = [m for m in self.med_docs
                          if any(pa_mongo_to_neo4j.get(str(p["pa_id"]),"") == pa_to
                                 for p in m.get("principios_activos", []))]
                if meds_1 and meds_2:
                    meds_con_interaccion.append((meds_1[0], meds_2[0]))

        for i, pac in enumerate(pacientes):
            n_meds = random.randint(2, 5)

            if i < PACIENTES_CON_INTERACCION and meds_con_interaccion:
                # Asignar combinación peligrosa conocida
                par = random.choice(meds_con_interaccion)
                meds_asignados = list(par)
                # Completar con meds aleatorios
                extras = random.sample(self.med_docs, k=min(n_meds - 2, len(self.med_docs)))
                meds_asignados += [m for m in extras if m not in meds_asignados]
            else:
                meds_asignados = random.sample(self.med_docs, k=min(n_meds, len(self.med_docs)))

            fecha_inicio = HOY - timedelta(days=random.randint(10, 365))
            for med in meds_asignados:
                rels.append({
                    "tipo":       "TOMA",
                    "from_label": "Paciente",
                    "from_key":   "id_anonimo",
                    "from_val":   pac["id_anonimo"],
                    "to_label":   "Medicamento",
                    "to_key":     "mongo_id",
                    "to_val":     str(med["_id"]),
                    "props": {
                        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                        "dosis_diaria": f"{random.choice([100,250,500,750,1000])}mg",
                        "prescriptor":  f"MED-{random.randint(1000,9999)}",
                    },
                })

        return rels

    # ── Exportar a Cypher ────────────────────────────────────────────────────

    def exportar_cypher(self, path: str, nodos_pa, nodos_med, nodos_pat,
                         nodos_ensayo, nodos_pac, rels_contiene, rels_interactua,
                         rels_afecta, rels_estudia, rels_toma):
        """
        Escribe un archivo .cypher listo para ejecutar con neo4j-shell o cypher-shell.
        """
        lines = []

        # Encabezado
        lines += [
            "// ================================================================",
            "// TP Tema 13 — Empresa Farmacéutica",
            "// Script de carga Neo4j — generado automáticamente",
            f"// Fecha: {HOY.strftime('%Y-%m-%d %H:%M')}",
            "// ================================================================",
            "",
            "// ── Constraints e índices ───────────────────────────────────────",
            "CREATE CONSTRAINT pa_neo4j_id IF NOT EXISTS",
            "  FOR (pa:PrincipioActivo) REQUIRE pa.neo4j_node_id IS UNIQUE;",
            "CREATE CONSTRAINT pa_mongo_id IF NOT EXISTS",
            "  FOR (pa:PrincipioActivo) REQUIRE pa.mongo_id IS UNIQUE;",
            "CREATE CONSTRAINT med_mongo_id IF NOT EXISTS",
            "  FOR (m:Medicamento) REQUIRE m.mongo_id IS UNIQUE;",
            "CREATE CONSTRAINT pac_id IF NOT EXISTS",
            "  FOR (p:Paciente) REQUIRE p.id_anonimo IS UNIQUE;",
            "CREATE CONSTRAINT ensayo_codigo IF NOT EXISTS",
            "  FOR (e:EnsayoClinico) REQUIRE e.codigo_protocolo IS UNIQUE;",
            "",
            "CREATE INDEX idx_interaccion_severidad IF NOT EXISTS",
            "  FOR ()-[i:INTERACTUA_CON]-() ON (i.severidad);",
            "CREATE INDEX idx_pa_via IF NOT EXISTS",
            "  FOR (pa:PrincipioActivo) ON (pa.via_metabolismo);",
            "",
        ]

        # Nodos PrincipioActivo
        lines += ["// ── Nodos :PrincipioActivo ──────────────────────────────────", ""]
        for n in nodos_pa:
            lines.append(
                f"MERGE (pa:PrincipioActivo {{neo4j_node_id: {_q(n['neo4j_node_id'])}}}) "
                f"SET pa.mongo_id = {_q(n['mongo_id'])}, "
                f"pa.nombre = {_q(n['nombre'])}, "
                f"pa.familia_quimica = {_q(n['familia_quimica'])}, "
                f"pa.vida_media_horas = {n['vida_media_horas']}, "
                f"pa.via_metabolismo = {_q(n['via_metabolismo'])};"
            )
        lines.append("")

        # Nodos Medicamento
        lines += ["// ── Nodos :Medicamento ──────────────────────────────────────", ""]
        for n in nodos_med:
            lines.append(
                f"MERGE (m:Medicamento {{mongo_id: {_q(n['mongo_id'])}}}) "
                f"SET m.nombre_comercial = {_q(n['nombre_comercial'])}, "
                f"m.nombre_generico = {_q(n['nombre_generico'])}, "
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
                f"MATCH (m:Medicamento {{mongo_id: {_q(r['from_val'])}}}), "
                f"(pa:PrincipioActivo {{mongo_id: {_q(r['to_val'])}}}) "
                f"MERGE (m)-[c:CONTIENE]->(pa) "
                f"SET c.dosis = {_q(r['props']['dosis'])}, c.rol = {_q(r['props']['rol'])};"
            )
        lines.append("")

        # Relaciones INTERACTUA_CON
        lines += ["// ── Relaciones [:INTERACTUA_CON] ────────────────────────────", ""]
        for r in rels_interactua:
            lines.append(
                f"MATCH (pa1:PrincipioActivo {{neo4j_node_id: {_q(r['from_val'])}}}), "
                f"(pa2:PrincipioActivo {{neo4j_node_id: {_q(r['to_val'])}}}) "
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
                f"MATCH (pa:PrincipioActivo {{neo4j_node_id: {_q(r['from_val'])}}}), "
                f"(pat:Patologia {{nombre: {_q(r['to_val'])}}}) "
                f"MERGE (pa)-[a:AFECTA]->(pat) "
                f"SET a.tipo_efecto = {_q(r['props']['tipo_efecto'])}, "
                f"a.descripcion = {_q(r['props']['descripcion'])};"
            )
        lines.append("")

        # Relaciones ESTUDIA
        lines += ["// ── Relaciones [:ESTUDIA] ───────────────────────────────────", ""]
        for r in rels_estudia:
            lines.append(
                f"MATCH (e:EnsayoClinico {{codigo_protocolo: {_q(r['from_val'])}}}), "
                f"(m:Medicamento {{mongo_id: {_q(r['to_val'])}}}) "
                f"MERGE (e)-[:ESTUDIA]->(m);"
            )
        lines.append("")

        # Relaciones TOMA
        lines += ["// ── Relaciones [:TOMA] ──────────────────────────────────────", ""]
        for r in rels_toma:
            lines.append(
                f"MATCH (pac:Paciente {{id_anonimo: {_q(r['from_val'])}}}), "
                f"(m:Medicamento {{mongo_id: {_q(r['to_val'])}}}) "
                f"MERGE (pac)-[t:TOMA]->(m) "
                f"SET t.fecha_inicio = date({_q(r['props']['fecha_inicio'])}), "
                f"t.dosis_diaria = {_q(r['props']['dosis_diaria'])}, "
                f"t.prescriptor = {_q(r['props']['prescriptor'])};"
            )
        lines.append("")
        lines.append("// ── Fin del script ──────────────────────────────────────────")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def _q(val: str) -> str:
    """Escapa strings para Cypher."""
    if val is None:
        return "null"
    escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
