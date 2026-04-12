# mercado-publico-intelligence

Plataforma en Python para extraer, normalizar, enriquecer y analizar oportunidades de licitaciones publicas de Chile usando la API oficial de Mercado Publico.

El proyecto esta pensado como portafolio profesional de Data Analytics / Data Engineering aplicado a un problema real: monitorear oportunidades comerciales, construir datasets reutilizables y generar scoring inicial de licitaciones.

## Problema De Negocio

Las licitaciones publicadas en Mercado Publico cambian a diario y suelen revisarse de forma manual. Esto dificulta:

- detectar oportunidades relevantes a tiempo,
- priorizar licitaciones segun rubro, region, estado y monto,
- construir historicos para analisis posterior,
- monitorear organismos compradores estrategicos,
- preparar reporting comercial o institucional.

## Solucion

El proyecto implementa un pipeline modular que:

- consulta licitaciones por fecha, rango de fechas o codigo,
- guarda respuestas crudas en JSON,
- consolida licitaciones resumidas,
- consulta detalle por `CodigoExterno`,
- reutiliza detalles ya descargados para evitar llamadas repetidas,
- genera datasets CSV de resumen, detalle e items,
- guarda resultados parciales durante procesos largos,
- crea columnas listas para analisis,
- calcula un score de oportunidad de 0 a 100.

## Arquitectura

```text
mercado-publico-intelligence/
|-- app/
|   |-- api/
|   |   |-- client.py
|   |   |-- endpoints.py
|   |   |-- exceptions.py
|   |-- dashboard/
|   |   |-- streamlit_app.py
|   |-- db/
|   |-- models/
|   |-- services/
|   |   |-- extract.py
|   |   |-- extract_bulk.py
|   |   |-- transform.py
|   |   |-- build_dataset.py
|   |   |-- scoring.py
|   |-- cli.py
|   |-- config.py
|   |-- logging_config.py
|-- data/
|   |-- raw/
|   |   |-- details/
|   |-- processed/
|   |-- exports/
|   |-- logs/
|-- notebooks/
|-- tests/
|-- .env.example
|-- requirements.txt
|-- pyproject.toml
|-- README.md
```

## Stack

- Python 3.11+
- requests
- pandas
- pydantic
- SQLAlchemy + SQLite
- python-dotenv
- Typer
- Streamlit
- pytest
- plotly

## Instalacion

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Si `python` no esta disponible en PATH, usa el ejecutable del entorno virtual:

```powershell
.venv\Scripts\python.exe -m app.cli --help
```

## Configuracion

Copia `.env.example` a `.env` y agrega tu ticket:

```env
MP_TICKET=tu_ticket_aqui
MP_BASE_URL=https://api.mercadopublico.cl/servicios/v1/publico
REQUEST_TIMEOUT=30
DATA_DIR=./data
DB_URL=sqlite:///./data/mercado_publico.db
LOG_LEVEL=INFO
MAX_RETRIES=3
RETRY_BACKOFF_SECONDS=1.5
```

Importante:

- No subas tu archivo `.env` a Git.
- El ticket se lee desde `MP_TICKET`.
- La API usa fechas en formato `ddmmaaaa`, pero la CLI acepta `YYYY-MM-DD` en los comandos principales.

## Comandos Principales

Ver ayuda:

```powershell
python -m app.cli --help
```

Consultar licitaciones del dia:

```powershell
python -m app.cli fetch-today
```

Consultar licitaciones por fecha:

```powershell
python -m app.cli fetch-date --date 2026-04-04
```

Consultar licitacion por codigo:

```powershell
python -m app.cli fetch-code --code 1234-56-LQ25
```

Generar dataset simple de una fecha:

```powershell
python -m app.cli build-dataset --date 2026-04-04
```

## Extraccion Bulk

Descargar licitaciones resumidas por rango de fechas:

```powershell
python -m app.cli fetch-range --start-date 2026-04-01 --end-date 2026-04-05
```

Esto guarda JSON diarios en:

```text
data/raw/licitaciones_raw_YYYY-MM-DD_timestamp.json
```

## Construccion Bulk De Datasets

Construir datasets de resumen, detalle e items:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05
```

Para probar rapido con pocos codigos:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --limit 50
```

Para reutilizar detalles ya descargados:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --limit 50 --skip-existing-details
```

Salidas finales:

```text
data/processed/licitaciones_resumen.csv
data/processed/licitaciones_detalladas.csv
data/processed/licitaciones_items.csv
```

Salidas parciales durante procesos largos:

```text
data/processed/licitaciones_detalladas_partial.csv
data/processed/licitaciones_items_partial.csv
```

Detalles crudos por codigo:

```text
data/raw/details/{CodigoExterno}.json
```

Logs de errores bulk:

```text
data/logs/bulk_errors.log
```

## Export Analysis Ready

Crear datasets finales listos para analisis:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-05
```

Si el proceso bulk fue interrumpido y solo existen parciales:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-05 --use-partials
```

Salidas:

```text
data/exports/licitaciones_analysis_ready.csv
data/exports/items_analysis_ready.csv
```

## Scoring De Oportunidades

Generar score de oportunidad sobre el dataset detallado:

```powershell
python -m app.cli score-dataset
```

Entrada por defecto:

```text
data/processed/licitaciones_detalladas.csv
```

Salida por defecto:

```text
data/processed/licitaciones_scored.csv
```

Tambien puedes indicar rutas:

```powershell
python -m app.cli score-dataset --input data/processed/licitaciones_detalladas.csv --output data/processed/licitaciones_scored.csv
```

El score usa reglas simples:

- keywords industriales en nombre o descripcion,
- multiples keywords,
- estado publicada,
- fecha de cierre futura,
- monto estimado mayor a 10 millones,
- regiones mineras prioritarias,
- descuento por keywords excluidas.

Columnas agregadas:

```text
texto_busqueda
contiene_keyword
contiene_excluida
score
prioridad
```

## Flujo Recomendado

Para una primera corrida pequena:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-02 --limit 30 --skip-existing-details
python -m app.cli score-dataset
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-02
```

Para continuar una corrida larga reutilizando detalles ya guardados:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --skip-existing-details
```

## Datasets

`licitaciones_resumen.csv` contiene licitaciones resumidas por fecha de consulta. Puede mantener duplicados si una licitacion aparece en varios dias.

`licitaciones_detalladas.csv` contiene una fila por `codigo_externo`, deduplicada para analisis.

`licitaciones_items.csv` contiene multiples filas por licitacion, una por item cuando la API entrega esa informacion.

`licitaciones_scored.csv` contiene el dataset detallado con score y prioridad.

## Notebooks

Los notebooks estan pensados para exploracion y storytelling:

- `notebooks/01_exploracion_api.ipynb`
- `notebooks/02_limpieza_licitaciones.ipynb`
- `notebooks/03_eda_oportunidades.ipynb`

## Casos De Uso

- Inteligencia comercial.
- Monitoreo de oportunidades.
- Analisis territorial.
- Priorizacion por rubro y estado.
- Reporting institucional.
- Portafolio profesional de Data Analytics / Data Engineering.

## Supuestos Y Consideraciones

- La estructura del JSON puede variar entre respuesta resumida y detallada.
- El proyecto usa `.get()` y normalizacion defensiva para no romper con campos faltantes.
- Algunos campos pueden quedar como `None` o `NaN` si la API no los entrega.
- El pipeline bulk incluye `--limit`, `--skip-existing-details`, pausas entre requests y guardado parcial para evitar perder avance.

## Disclaimer

Este proyecto depende de la disponibilidad, estabilidad y estructura de la API oficial de Mercado Publico / ChileCompra. Cambios en la API pueden requerir ajustes en cliente, transformaciones o scoring.
