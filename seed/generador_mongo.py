"""
Generador de documentos para las 6 colecciones MongoDB.
Produce documentos listos para insertar via pymongo o mongoimport.
"""

import random
from datetime import datetime, timedelta
from bson import ObjectId
from faker import Faker
from config import *
from datos_maestros import PRINCIPIOS_ACTIVOS_MAESTROS, PATOLOGIAS

fake = Faker("es_AR")
fake.seed_instance(RANDOM_SEED)
random.seed(RANDOM_SEED)

# ── Helpers de fecha ─────────────────────────────────────────────────────────
HOY = datetime.now()

def fecha_pasada(dias_min=30, dias_max=1800):
    delta = random.randint(dias_min, dias_max)
    return HOY - timedelta(days=delta)

def fecha_futura(dias_min=90, dias_max=1095):
    delta = random.randint(dias_min, dias_max)
    return HOY + timedelta(days=delta)

def fecha_reciente_semestre():
    """Fecha dentro del último semestre — para garantizar señales en consulta (e)."""
    delta = random.randint(1, 180)
    return HOY - timedelta(days=delta)

def fecha_reciente_anio():
    """Fecha dentro del último año — para consulta (c)."""
    delta = random.randint(1, 365)
    return HOY - timedelta(days=delta)

# ── Generadores ──────────────────────────────────────────────────────────────

def generar_principios_activos(maestros: list) -> list:
    """
    Convierte los PA maestros al formato de documento MongoDB.
    Los PA extras (hasta CANT_PRINCIPIOS_ACTIVOS) se generan sintéticamente.
    Retorna (docs_mongo, map_neo4j_id_a_objectid).
    """
    docs   = []
    id_map = {}  # neo4j_node_id -> ObjectId

    familias_extra = list(CATEGORIAS_TERAPEUTICAS.keys())

    for i, pa_base in enumerate(maestros):
        oid = ObjectId()
        doc = {
            "_id":             oid,
            "nombre":          pa_base["nombre"],
            "nombre_iupac":    f"IUPAC-{pa_base['nombre'].upper().replace(' ', '_')}",
            "familia_quimica": pa_base["familia"],
            "mecanismo_accion":pa_base["mecanismo"],
            "vida_media_horas":pa_base["vida_media_horas"],
            "metabolismo": {
                "via_principal":               pa_base["via_metabolismo"],
                "enzimas":                     pa_base["enzimas"],
                "porcentaje_eliminacion_renal": 80 if pa_base["via_metabolismo"] == "renal" else 20,
            },
            "categorias_terapeuticas": CATEGORIAS_TERAPEUTICAS.get(pa_base["familia"], ["general"]),
            "neo4j_node_id":   pa_base["neo4j_node_id"],
        }
        docs.append(doc)
        id_map[pa_base["neo4j_node_id"]] = oid

    # PA adicionales hasta alcanzar el mínimo requerido
    n_extras = max(0, CANT_PRINCIPIOS_ACTIVOS - len(maestros))
    for i in range(n_extras):
        familia = random.choice(familias_extra)
        nombre  = f"Compuesto-{fake.last_name()}-{random.randint(100, 999)}"
        neo4j_id = f"pa_{nombre.lower().replace(' ', '_').replace('-', '_')}"
        oid = ObjectId()
        via = random.choice(["renal", "hepatica", "mixta"])
        doc = {
            "_id":             oid,
            "nombre":          nombre,
            "nombre_iupac":    f"IUPAC-{nombre.upper().replace(' ', '_')}",
            "familia_quimica": familia,
            "mecanismo_accion":f"Mecanismo de acción de {nombre}. Actúa sobre receptores específicos.",
            "vida_media_horas":round(random.uniform(1.0, 48.0), 1),
            "metabolismo": {
                "via_principal":               via,
                "enzimas":                     random.sample(["CYP3A4","CYP2D6","CYP2C9","CYP2C19"], k=random.randint(0,2)),
                "porcentaje_eliminacion_renal": random.randint(10, 90),
            },
            "categorias_terapeuticas": CATEGORIAS_TERAPEUTICAS.get(familia, ["general"]),
            "neo4j_node_id":   neo4j_id,
        }
        docs.append(doc)
        id_map[neo4j_id] = oid

    return docs, id_map


def generar_medicamentos(pa_docs: list, pa_id_map: dict) -> tuple:
    """
    Genera los documentos de medicamentos.
    Retorna (docs_mongo, map_nombre_a_objectid).
    """
    docs   = []
    id_map = {}

    tipos = ["generico", "biologico", "dispositivo_medico"]
    formas = ["capsula", "comprimido", "jarabe", "inyectable", "crema", "parche", "inhalador"]
    vias   = ["oral", "parenteral", "topica", "inhalatoria", "sublingual"]
    condiciones = ["libre", "bajo_receta", "receta_archivada"]
    estados = ["activo"] * 9 + ["discontinuado"] + ["en_revision"]

    # Contadores para asegurar mix requerido
    tipo_contador = {"generico": 0, "biologico": 0, "dispositivo_medico": 0}
    tipos_forzados = {
        "biologico":       [30, 80],    # rango de índices que serán biológicos
        "dispositivo_medico": [81, 100], # rango que serán dispositivos
    }

    nombres_comerciales_usados = set()

    for i in range(CANT_MEDICAMENTOS):
        # Determinar tipo
        if 30 <= i < 80:
            tipo = "biologico"
        elif 80 <= i < 100:
            tipo = "dispositivo_medico"
        else:
            tipo = "generico"
        tipo_contador[tipo] += 1

        # Seleccionar PA para este medicamento
        n_pa = random.randint(MIN_PA_POR_MEDICAMENTO, MAX_PA_POR_MEDICAMENTO)
        pas_seleccionados = random.sample(pa_docs, k=min(n_pa, len(pa_docs)))

        pa_embebidos = []
        for idx, pa in enumerate(pas_seleccionados):
            pa_embebidos.append({
                "pa_id":               pa["_id"],
                "nombre":              pa["nombre"],
                "dosis_en_formulacion":f"{random.choice([100,200,250,500,750,1000])}mg",
                "rol":                 "activo" if idx == 0 else random.choice(["activo", "excipiente_clave"]),
            })

        # Nombre comercial único
        base_nombre = f"{fake.last_name()} {random.choice([100,200,250,400,500,750,1000])}"
        while base_nombre in nombres_comerciales_usados:
            base_nombre = f"{fake.last_name()} {random.choice([100,200,250,400,500,750,1000])}"
        nombres_comerciales_usados.add(base_nombre)

        oid = ObjectId()

        # Atributos específicos según tipo
        if tipo == "biologico":
            atributos = {
                "origen":                    random.choice(["recombinante", "monoclonal", "derivado_plasma"]),
                "cadena_fria":               True,
                "temperatura_almacenamiento":"2-8°C",
                "numero_biosimilar":         f"BIO-{random.randint(1000,9999)}",
            }
        elif tipo == "dispositivo_medico":
            atributos = {
                "clase_riesgo":  random.choice(["I", "II", "III"]),
                "vida_util_usos":random.randint(1, 100),
                "esteril":       random.choice([True, False]),
            }
        else:  # generico
            atributos = {
                "bioequivalencia_certificada":True,
                "marca_referencia":           f"Marca-{fake.last_name()}",
            }

        doc = {
            "_id":              oid,
            "nombre_comercial": base_nombre,
            "nombre_generico":  pas_seleccionados[0]["nombre"] if pas_seleccionados else "Genérico",
            "forma_farmaceutica":random.choice(formas),
            "dosis":            pa_embebidos[0]["dosis_en_formulacion"] if pa_embebidos else "500mg",
            "via_administracion":random.choice(vias),
            "condicion_venta":  random.choice(condiciones),
            "pais_registro":    random.sample(PAISES, k=random.randint(1, 5)),
            "tipo":             tipo,
            "principios_activos":pa_embebidos,
            "atributos_especificos":atributos,
            "fecha_registro":   fecha_pasada(365, 3650),
            "estado":           random.choice(estados),
        }
        docs.append(doc)
        id_map[base_nombre] = oid

    return docs, id_map


def generar_distribuidores() -> tuple:
    """Genera distribuidores. Retorna (docs, id_map nombre->ObjectId)."""
    docs   = []
    id_map = {}
    tipos  = ["mayorista", "minorista", "hospital", "farmacia"]
    tipos_forzados = (
        ["mayorista"] * 10 + ["minorista"] * 15 +
        ["hospital"] * 12 + ["farmacia"] * 13
    )

    for i in range(CANT_DISTRIBUIDORES):
        tipo = tipos_forzados[i] if i < len(tipos_forzados) else random.choice(tipos)
        pais = random.choice(PAISES)
        nombre = f"{fake.company()} {tipo.title()}"
        oid  = ObjectId()
        doc  = {
            "_id":        oid,
            "nombre":     nombre,
            "tipo":       tipo,
            "pais":       pais,
            "ciudad":     fake.city(),
            "habilitacion":f"HAB-{pais}-{random.randint(2010,2023)}-{random.randint(100,9999)}",
            "lotes_activos": [],  # se rellena al generar lotes
            "contacto": {
                "email":    fake.email(),
                "telefono": fake.phone_number(),
                "direccion":fake.address().replace("\n", ", "),
            },
        }
        docs.append(doc)
        id_map[nombre] = oid
    return docs, id_map


def generar_lotes(med_docs: list, dist_docs: list) -> list:
    """
    Genera lotes con cadena de distribución completamente embebida.
    Garantiza que la consulta (b) tenga resultados: 20 lotes vencen en < 90 días.
    """
    docs = []
    tipos_eslabon = ["planta", "mayorista", "minorista", "farmacia", "hospital"]

    # Distribuidores por tipo para armar cadenas realistas
    dist_por_tipo = {}
    for d in dist_docs:
        dist_por_tipo.setdefault(d["tipo"], []).append(d)

    # Contadores para asegurar la garantía de consulta (b)
    lotes_proximos_vencer = 0

    for i in range(CANT_LOTES):
        med = random.choice(med_docs)
        planta_pais = random.choice(PAISES)
        cantidad_producida = random.randint(5000, 100000)

        # 20 lotes vencen en los próximos 90 días (garantía consulta b)
        if lotes_proximos_vencer < 20:
            vencimiento = HOY + timedelta(days=random.randint(10, 89))
            estado_stock = random.choice(["en_distribucion", "en_planta"])
            lotes_proximos_vencer += 1
        else:
            vencimiento  = fecha_futura(dias_min=91, dias_max=730)
            estado_stock = random.choice(["en_distribucion", "en_planta", "agotado"])

        # Construir cadena de distribución
        n_eslabones = random.randint(MIN_ESLABONES_LOTE, MAX_ESLABONES_LOTE)
        cadena      = []
        stock_total = cantidad_producida

        fecha_actual = fecha_pasada(dias_min=180, dias_max=600)

        for orden in range(1, n_eslabones + 1):
            es_ultimo = (orden == n_eslabones)

            if orden == 1:
                tipo_eslabon   = "planta"
                entidad_nombre = f"Planta {fake.city()}"
                entidad_oid    = ObjectId()
            else:
                # Elegir tipo realista según posición en la cadena
                if orden == 2:
                    tipo_eslabon = "mayorista"
                elif orden == n_eslabones:
                    tipo_eslabon = random.choice(["farmacia", "hospital"])
                else:
                    tipo_eslabon = random.choice(["minorista", "mayorista"])

                # Buscar distribuidor real del tipo correspondiente
                candidatos = dist_por_tipo.get(tipo_eslabon, dist_docs)
                dist = random.choice(candidatos) if candidatos else None
                entidad_nombre = dist["nombre"] if dist else f"{tipo_eslabon.title()} {fake.city()}"
                entidad_oid    = dist["_id"]   if dist else ObjectId()

            transferido = int(stock_total * random.uniform(0.3, 0.9)) if not es_ultimo else stock_total
            stock_actual = transferido if es_ultimo else 0

            duracion_eslabon = timedelta(days=random.randint(3, 30))
            fecha_salida = None if es_ultimo else fecha_actual + duracion_eslabon

            eslabon = {
                "orden":               orden,
                "tipo_eslabon":        tipo_eslabon,
                "entidad_id":          entidad_oid,
                "entidad_nombre":      entidad_nombre,
                "fecha_entrada":       fecha_actual,
                "fecha_salida":        fecha_salida,
                "cantidad_transferida":transferido,
                "stock_actual":        stock_actual if es_ultimo else 0,
                "estado":              "activo" if es_ultimo else "completado",
            }
            cadena.append(eslabon)

            stock_total  = transferido
            fecha_actual = fecha_actual + duracion_eslabon if fecha_salida else fecha_actual

        dias_hasta_vencimiento = (vencimiento - HOY).days
        oid = ObjectId()
        doc = {
            "_id":                     oid,
            "numero_lote":             f"LOT-{HOY.year}-{str(i+1).zfill(5)}",
            "medicamento_id":          med["_id"],
            "medicamento_nombre":      med["nombre_comercial"],
            "fabricacion": {
                "fecha":               fecha_pasada(200, 400),
                "planta":              f"Planta {fake.city()}",
                "pais_fabricacion":    planta_pais,
                "cantidad_producida":  cantidad_producida,
                "responsable_qa":      f"Dr. {fake.last_name()}",
            },
            "fecha_vencimiento":       vencimiento,
            "estado_stock":            estado_stock,
            "cantidad_disponible_total":cadena[-1]["stock_actual"],
            "cadena_distribucion":     cadena,
            "alertas": {
                "proximo_vencimiento": dias_hasta_vencimiento < 90,
                "recalls_activos":     [],
            },
        }
        docs.append(doc)

        # Actualizar referencia en distribuidor (último eslabón)
        ultimo = cadena[-1]
        for dist in dist_docs:
            if dist["_id"] == ultimo.get("entidad_id"):
                dist["lotes_activos"].append({
                    "lote_id":           oid,
                    "numero_lote":       doc["numero_lote"],
                    "medicamento_nombre":doc["medicamento_nombre"],
                    "cantidad_actual":   ultimo["stock_actual"],
                    "fecha_recepcion":   ultimo["fecha_entrada"],
                })
                break

    return docs


def generar_ensayos(med_docs: list, pa_id_map: dict) -> list:
    """
    Genera ensayos clínicos.
    Garantía: al menos 5 en fase III y estado activo (consulta d).
    """
    docs   = []
    fases  = ["I", "II", "III", "IV"]
    estados = ["activo", "suspendido", "completado", "cancelado"]
    paises_ensayo = ["AR", "BR", "UY", "CL", "MX", "CO"]

    pa_node_ids = list(pa_id_map.keys())

    for i in range(CANT_ENSAYOS):
        med = random.choice(med_docs)

        # Garantizar al menos 5 fase III activos (consultas d)
        if i < 5:
            fase   = "III"
            estado = "activo"
        else:
            fase   = random.choice(fases)
            estado = random.choice(estados)

        n_centros = random.randint(MIN_CENTROS_POR_ENSAYO, MAX_CENTROS_POR_ENSAYO)
        centros   = []
        total_pac = 0

        for j in range(n_centros):
            pais_centro = random.choice(paises_ensayo)
            pac         = random.randint(20, 300)
            total_pac  += pac
            centros.append({
                "nombre":               f"Hospital {fake.last_name()} de {fake.city()}",
                "pais":                 pais_centro,
                "ciudad":               fake.city(),
                "investigador_principal":f"Dr. {fake.first_name()} {fake.last_name()}",
                "pacientes_enrolados":  pac,
                "estado_centro":        random.choice(["activo", "completado"]),
            })

        # Interacciones bajo estudio (2 PA aleatorios para nexo con Neo4j)
        ints_bajo_estudio = []
        if len(pa_node_ids) >= 2:
            par = random.sample(pa_node_ids, 2)
            ints_bajo_estudio.append({
                "pa1_id": pa_id_map[par[0]],
                "pa2_id": pa_id_map[par[1]],
            })

        inicio = fecha_pasada(180, 730)
        doc = {
            "_id":              ObjectId(),
            "nombre":           f"{med['nombre_generico'].split()[0][:6].upper()}-{fase}-{HOY.year}-{random.choice(paises_ensayo)}",
            "codigo_protocolo": f"ECA-{HOY.year}-{str(i+1).zfill(3)}",
            "fase":             fase,
            "estado":           estado,
            "hipotesis":        f"El medicamento {med['nombre_comercial']} es no-inferior al tratamiento estándar en fase {fase}.",
            "medicamento_id":   med["_id"],
            "fecha_inicio":     inicio,
            "fecha_fin_estimada":inicio + timedelta(days=random.randint(365, 1095)),
            "centros_participantes": centros,
            "total_pacientes_enrolados": total_pac,
            "resultados_preliminares": {
                "fecha_corte":            HOY - timedelta(days=random.randint(30, 180)),
                "eficacia_observada":     round(random.uniform(0.55, 0.95), 2),
                "eventos_adversos_serios":random.randint(0, 15),
                "resumen":                f"Los datos preliminares muestran resultados {random.choice(['prometedores','consistentes','mixtos'])} con perfil de seguridad aceptable.",
            },
            "interacciones_bajo_estudio": ints_bajo_estudio,
        }
        docs.append(doc)
    return docs


def generar_efectos_adversos(med_docs: list, lote_docs: list, pa_docs: list) -> list:
    """
    Genera efectos adversos.
    Garantía: 6 medicamentos tienen >3 reportes graves en el último semestre (consulta e).
    """
    docs    = []
    graves  = ["leve", "moderada", "grave", "fatal"]
    desenlaces = ["recuperado", "con_secuelas", "fatal", "desconocido"]
    fuentes = ["farmacia", "hospital", "medico", "paciente"]

    # Medicamentos señal — superarán el umbral de la consulta (e)
    meds_señal = random.sample(med_docs, min(MEDS_CON_SEÑAL_FARMACOVIG, len(med_docs)))

    contador = 0

    # Primero: generar reportes graves recientes para los medicamentos señal
    for med_señal in meds_señal:
        lotes_med = [l for l in lote_docs if l["medicamento_id"] == med_señal["_id"]]
        if not lotes_med:
            lotes_med = [random.choice(lote_docs)]

        for _ in range(EFECTOS_POR_MED_SEÑAL):
            lote = random.choice(lotes_med)
            pa_imp = random.choice(med_señal["principios_activos"])
            doc = _crear_efecto_adverso(
                med=med_señal, lote=lote,
                pa_nombre=pa_imp["nombre"], pa_oid=pa_imp["pa_id"],
                gravedad="grave",
                fecha=fecha_reciente_semestre(),
                todos_meds=med_docs,
            )
            docs.append(doc)
            contador += 1

    # Luego: llenar el resto hasta CANT_EFECTOS_ADVERSOS
    while contador < CANT_EFECTOS_ADVERSOS:
        med  = random.choice(med_docs)
        lote = random.choice([l for l in lote_docs if l["medicamento_id"] == med["_id"]] or lote_docs)
        pa_imp = random.choice(med["principios_activos"]) if med["principios_activos"] else None
        doc = _crear_efecto_adverso(
            med=med, lote=lote,
            pa_nombre=pa_imp["nombre"] if pa_imp else "Desconocido",
            pa_oid=pa_imp["pa_id"] if pa_imp else ObjectId(),
            gravedad=random.choices(graves, weights=[40, 35, 20, 5])[0],
            fecha=fecha_reciente_anio(),
            todos_meds=med_docs,
        )
        docs.append(doc)
        contador += 1

    return docs


def _crear_efecto_adverso(med, lote, pa_nombre, pa_oid, gravedad, fecha, todos_meds):
    """Helper interno — crea un documento de efecto adverso."""
    return {
        "_id":                   ObjectId(),
        "medicamento_id":        med["_id"],
        "medicamento_nombre":    med["nombre_comercial"],
        "lote_id":               lote["_id"],
        "lote_numero":           lote["numero_lote"],
        "pa_implicados":         [{"pa_id": pa_oid, "nombre": pa_nombre}],
        "paciente_anonimizado":  f"PAC-{HOY.year}-{random.randint(10000,99999)}",
        "edad_aproximada":       random.randint(18, 85),
        "sexo":                  random.choice(["M", "F", "NB", "NE"]),
        "descripcion":           f"Paciente presentó {random.choice(TERMINOS_MEDDRA).lower()} a las {random.randint(1,48)} horas de inicio de tratamiento.",
        "termino_meddra":        random.choice(TERMINOS_MEDDRA),
        "gravedad":              gravedad,
        "desenlace":             random.choice(["recuperado","recuperado","con_secuelas","desconocido"]),
        "requirio_hospitalizacion": gravedad in ["grave", "fatal"],
        "fecha_reporte":         fecha,
        "pais_reporte":          random.choice(PAISES),
        "fuente":                random.choice(["farmacia","hospital","hospital","medico","paciente"]),
        "combinacion_medicamentos": [random.choice(todos_meds)["_id"]] if random.random() > 0.5 else [],
    }
