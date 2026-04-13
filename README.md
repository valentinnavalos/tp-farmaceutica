# TP Farmacéutica - Base de Datos 2

Sistema de gestión de información farmacéutica utilizando MongoDB y Neo4j. Este proyecto implementa un sistema de trazabilidad de medicamentos, gestión de ensayos clínicos, farmacovigilancia y análisis de interacciones medicamentosas.

## Descripción

El sistema está diseñado con arquitectura multi-base de datos:
- **MongoDB**: Almacena datos transaccionales (medicamentos, lotes, distribuidores, ensayos clínicos, efectos adversos)
- **Neo4j**: Gestiona el grafo de relaciones (principios activos, interacciones medicamentosas, patologías, pacientes)

## Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.8+** ([Descargar](https://www.python.org/downloads/))
- **Docker y Docker Compose** ([Descargar](https://www.docker.com/get-started))
- **Git** ([Descargar](https://git-scm.com/downloads))

## Estructura del Proyecto

```
tp-farmaceutica/
├── mongodb/                    # Conexión y queries MongoDB
│   ├── connection.py          # Cliente MongoDB
│   ├── init_indexes.py        # Índices de rendimiento
│   └── queries/               # Consultas MongoDB (a-e)
│       ├── a_trazabilidad.py
│       ├── b_lotes_vencimiento.py
│       ├── c_efectos_adversos.py
│       ├── d_ensayos_fase_iii.py
│       └── e_senal_farmacovigilancia.py
├── neo4j_db/                  # Conexión y queries Neo4j
│   ├── connection.py          # Driver Neo4j
│   ├── init_constraints.py    # Constraints y índices
│   └── queries/               # Consultas Neo4j (a-e)
│       ├── a_interacciones_prescripcion.py
│       ├── b_red_principio_activo.py
│       ├── c_toxicidad_acumulativa.py
│       ├── d_pa_mas_peligroso.py
│       └── e_prediccion_interacciones.py
├── seed/                      # Generador de datos de prueba
│   ├── config.py              # Configuración central
│   ├── generar_datos.py       # Script principal
│   ├── datos_maestros.py      # Datos base de principios activos
│   ├── generador_mongo.py     # Generador para MongoDB
│   └── generador_neo4j.py     # Generador para Neo4j
├── docker-compose.yml         # Orquestación de contenedores
└── requirements.txt           # Dependencias Python
```

## Instalación Paso a Paso

### 1. Clonar el Repositorio

```bash
git clone <url-del-repositorio>
cd tp-farmaceutica
```

### 2. Instalar Dependencias Python

Crea un entorno virtual (recomendado):

```bash
# En macOS/Linux
python3 -m venv venv
source venv/bin/activate

# En Windows
python -m venv venv
venv\Scripts\activate
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

Las dependencias incluyen:
- `pymongo>=4.6` - Driver de MongoDB
- `neo4j>=5.0` - Driver de Neo4j

### 3. Configurar las Bases de Datos

#### Opción A: Usando Docker (Recomendado)

Inicia los contenedores de MongoDB y Neo4j:

```bash
docker-compose up -d
```

Esto levantará:
- **MongoDB** en `localhost:27017`
- **Mongo Express** (UI) en `http://localhost:8081`
- **Neo4j** en `localhost:7687` (Bolt) y `http://localhost:7474` (Browser)
  - Usuario: `neo4j`
  - Contraseña: `farmaceutica`

Verifica que los contenedores estén corriendo:

```bash
docker-compose ps
```

#### Opción B: Instalación Local

Si prefieres no usar Docker, instala MongoDB y Neo4j localmente:

- **MongoDB**: [Guía de instalación](https://www.mongodb.com/docs/manual/installation/)
- **Neo4j**: [Guía de instalación](https://neo4j.com/docs/operations-manual/current/installation/)

Luego, ajusta las credenciales en `seed/config.py`:

```python
MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "farmaceutica_tp"

NEO4J_URI  = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "farmaceutica"
```

### 4. Generar y Cargar Datos de Prueba

El script `generar_datos.py` crea datos coherentes para ambas bases de datos.

#### Opción 1: Generar y Cargar Todo Automáticamente

```bash
cd seed
python generar_datos.py --all
```

Este comando:
1. Genera datos sintéticos coherentes
2. Guarda archivos JSON en `seed/output/mongodb/`
3. Guarda script Cypher en `seed/output/neo4j/carga_neo4j.cypher`
4. Carga automáticamente en MongoDB
5. Carga automáticamente en Neo4j

#### Opción 2: Solo Generar Archivos (Sin Cargar)

```bash
cd seed
python generar_datos.py
```

Luego carga manualmente:

**Para MongoDB:**

```bash
mongoimport --db farmaceutica_tp --collection principios_activos --file output/mongodb/principios_activos.json
mongoimport --db farmaceutica_tp --collection medicamentos --file output/mongodb/medicamentos.json
mongoimport --db farmaceutica_tp --collection distribuidores --file output/mongodb/distribuidores.json
mongoimport --db farmaceutica_tp --collection lotes --file output/mongodb/lotes.json
mongoimport --db farmaceutica_tp --collection ensayos_clinicos --file output/mongodb/ensayos_clinicos.json
mongoimport --db farmaceutica_tp --collection efectos_adversos --file output/mongodb/efectos_adversos.json
```

**Para Neo4j:**

```bash
cypher-shell -u neo4j -p farmaceutica --file output/neo4j/carga_neo4j.cypher
```

#### Opción 3: Cargar Solo en un Motor

```bash
# Solo MongoDB
python generar_datos.py --mongo-load

# Solo Neo4j
python generar_datos.py --neo4j-load
```

### 5. Inicializar Índices y Constraints

Después de cargar los datos, crea los índices y constraints para optimizar las consultas:

**MongoDB:**

```bash
cd ..  # Volver a la raíz del proyecto
python -m mongodb.init_indexes
```

**Neo4j:**

```bash
python -m neo4j_db.init_constraints
```

## Uso del Sistema

### Ejecutar Consultas de MongoDB

Las consultas están en el directorio `mongodb/queries/`:

```bash
# Consulta A: Trazabilidad completa de un lote
python -m mongodb.queries.a_trazabilidad

# Consulta B: Lotes próximos a vencer
python -m mongodb.queries.b_lotes_vencimiento

# Consulta C: Efectos adversos por medicamento
python -m mongodb.queries.c_efectos_adversos

# Consulta D: Ensayos clínicos fase III
python -m mongodb.queries.d_ensayos_fase_iii

# Consulta E: Señales de farmacovigilancia
python -m mongodb.queries.e_senal_farmacovigilancia
```

### Ejecutar Consultas de Neo4j

Las consultas están en el directorio `neo4j_db/queries/`:

```bash
# Consulta A: Interacciones en prescripciones
python -m neo4j_db.queries.a_interacciones_prescripcion

# Consulta B: Red de principios activos
python -m neo4j_db.queries.b_red_principio_activo

# Consulta C: Toxicidad acumulativa
python -m neo4j_db.queries.c_toxicidad_acumulativa

# Consulta D: Principio activo más peligroso
python -m neo4j_db.queries.d_pa_mas_peligroso

# Consulta E: Predicción de interacciones
python -m neo4j_db.queries.e_prediccion_interacciones
```

## Verificación de la Instalación

### Verificar MongoDB

1. **Usando Mongo Express** (si usas Docker):
   - Abre `http://localhost:8081` en tu navegador
   - Navega a la base de datos `farmaceutica_tp`
   - Deberías ver 6 colecciones con datos

2. **Usando mongosh:**

```bash
mongosh
use farmaceutica_tp
show collections
db.medicamentos.countDocuments()
```

### Verificar Neo4j

1. **Usando Neo4j Browser:**
   - Abre `http://localhost:7474` en tu navegador
   - Autentícate con usuario `neo4j` y contraseña `farmaceutica`
   - Ejecuta: `MATCH (n) RETURN count(n)`
   - Deberías ver múltiples nodos

2. **Usando cypher-shell:**

```bash
cypher-shell -u neo4j -p farmaceutica
MATCH (n) RETURN labels(n), count(n);
```

## Datos Generados

El generador crea:

**MongoDB:**
- 80 Principios Activos
- 200 Medicamentos
- 50 Distribuidores
- 150 Lotes (con trazabilidad)
- 20 Ensayos Clínicos
- 300 Efectos Adversos

**Neo4j:**
- 80 Nodos `:PrincipioActivo`
- 200 Nodos `:Medicamento`
- ~40 Nodos `:Patologia`
- 20 Nodos `:EnsayoClinico`
- 50 Nodos `:Paciente`
- Relaciones: `CONTIENE`, `INTERACTUA_CON`, `AFECTA`, `ESTUDIA`, `TOMA`

## Detener y Limpiar

### Detener Contenedores

```bash
docker-compose down
```

### Limpiar Datos (Reinicio Completo)

```bash
# Eliminar volúmenes de datos
docker-compose down -v

# Regenerar datos
cd seed
python generar_datos.py --all
```

## Solución de Problemas

### Error: "No se pudo conectar a MongoDB"

- Verifica que Docker esté corriendo: `docker ps`
- Reinicia los contenedores: `docker-compose restart mongodb`
- Verifica el puerto: `lsof -i :27017` (macOS/Linux) o `netstat -an | findstr 27017` (Windows)

### Error: "No se pudo conectar a Neo4j"

- Espera ~30 segundos después de `docker-compose up` (Neo4j tarda en iniciar)
- Verifica logs: `docker-compose logs neo4j`
- Verifica credenciales en `seed/config.py`

### Error: "pymongo no instalado"

```bash
pip install pymongo neo4j
```

### Error al importar módulos

Asegúrate de estar en la raíz del proyecto y usar el formato `-m`:

```bash
# ✅ Correcto
python -m mongodb.queries.a_trazabilidad

# ❌ Incorrecto
python mongodb/queries/a_trazabilidad.py
```

## Tecnologías Utilizadas

- **Python 3.8+** - Lenguaje de programación
- **MongoDB 7** - Base de datos documental
- **Neo4j 5** - Base de datos de grafos
- **Docker & Docker Compose** - Contenedorización
- **pymongo** - Driver Python para MongoDB
- **neo4j-driver** - Driver Python para Neo4j

## Contribuciones

Este proyecto es parte del Trabajo Práctico de Ingeniería de Datos 2 - UADE.

## Licencia

Proyecto académico
