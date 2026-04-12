# Mercado Publico Intelligence

Proyecto en Python para consumir la API oficial de Mercado Publico / ChileCompra, procesar licitaciones y transformarlas en datasets utiles para analisis.

La idea no es solo descargar datos, sino convertirlos en informacion accionable para detectar oportunidades de negocio, analizar compras publicas y construir un portafolio de Data Analytics / Data Engineering aplicado a un caso real.

## Que Hace Este Proyecto

- Consulta licitaciones desde la API oficial de Mercado Publico.
- Permite traer datos por fecha, codigo o rango de fechas.
- Guarda respuestas crudas en JSON.
- Enriquece licitaciones consultando detalle por `CodigoExterno`.
- Normaliza respuestas resumidas y detalladas a DataFrames de pandas.
- Exporta datasets a CSV.
- Guarda resultados parciales en procesos largos.
- Reutiliza detalles ya descargados para evitar llamadas repetidas.
- Genera datasets listos para analisis.
- Calcula un score basico de oportunidad.

## Estructura Del Proyecto

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

Si `python` no esta disponible en PATH:

```powershell
.venv\Scripts\python.exe -m app.cli --help
```

## Configuracion

Copia `.env.example` a `.env`:

```powershell
Copy-Item .env.example .env
```

Configura el ticket:

```env
MP_TICKET=tu_ticket_real
MP_BASE_URL=https://api.mercadopublico.cl/servicios/v1/publico
REQUEST_TIMEOUT=30
DATA_DIR=./data
DB_URL=sqlite:///./data/mercado_publico.db
LOG_LEVEL=INFO
MAX_RETRIES=3
RETRY_BACKOFF_SECONDS=1.5
```

Importante:

- No subir `.env` a Git.
- `MP_TICKET` es obligatorio para llamar la API.
- La CLI usa fechas `YYYY-MM-DD`; el cliente las convierte al formato requerido por la API.

## Quickstart

Prueba corta recomendada:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-02 --limit 30 --skip-existing-details
python -m app.cli score-dataset
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-02
```

Si quieres solo validar conexion:

```powershell
python -m app.cli fetch-date --date 2026-04-04
```

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

Consultar una licitacion por codigo:

```powershell
python -m app.cli fetch-code --code 1292-6-LE26
```

Generar dataset simple por fecha:

```powershell
python -m app.cli build-dataset --date 2026-04-04
```

## Extraccion Por Rango

Descargar respuestas resumidas por dia:

```powershell
python -m app.cli fetch-range --start-date 2026-04-01 --end-date 2026-04-05
```

Salida:

```text
data/raw/licitaciones_raw_YYYY-MM-DD_timestamp.json
```

## Build Bulk Dataset

Construir datasets de resumen, detalle e items:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05
```

Probar rapido con pocos codigos:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --limit 50
```

Reutilizar detalles ya descargados:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --limit 50 --skip-existing-details
```

Opciones utiles:

- `--limit N`: procesa solo los primeros `N` codigos unicos.
- `--skip-existing-details`: reutiliza `data/raw/details/{codigo}.json` si existe.
- `--sleep-seconds 0.2`: pausa entre requests de detalle. El default actual es `0.2`.
- `--deduplicate-summary`: deduplica el dataset resumen por `codigo_externo`.

Salidas finales:

```text
data/processed/licitaciones_resumen.csv
data/processed/licitaciones_detalladas.csv
data/processed/licitaciones_items.csv
```

Salidas parciales:

```text
data/processed/licitaciones_detalladas_partial.csv
data/processed/licitaciones_items_partial.csv
```

Detalles crudos por codigo:

```text
data/raw/details/{CodigoExterno}.json
```

Logs:

```text
data/logs/bulk_errors.log
```

## Export Analysis Ready

Exportar datasets finales listos para analisis:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-05
```

Si solo existen parciales:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-05 --use-partials
```

Salidas:

```text
data/exports/licitaciones_analysis_ready.csv
data/exports/items_analysis_ready.csv
```

## Scoring De Oportunidades

Generar score sobre el dataset detallado:

```powershell
python -m app.cli score-dataset
```

Input por defecto:

```text
data/processed/licitaciones_detalladas.csv
```

Output por defecto:

```text
data/processed/licitaciones_scored.csv
```

Con rutas explicitas:

```powershell
python -m app.cli score-dataset --input data/processed/licitaciones_detalladas.csv --output data/processed/licitaciones_scored.csv
```

Columnas agregadas:

```text
texto_busqueda
contiene_keyword
contiene_excluida
score
prioridad
```

Reglas principales:

- `+30` si nombre o descripcion contiene keyword industrial.
- `+20` si contiene multiples keywords industriales.
- `+15` si `codigo_estado == 5`.
- `+15` si `fecha_cierre` es futura.
- `+10` si `monto_estimado > 10_000_000`.
- `+10` si `region_unidad` contiene Antofagasta, Tarapaca o Atacama.
- `-25` si contiene keywords excluidas.

Prioridad:

- `alta`: score >= 70
- `media`: score >= 40
- `baja`: score < 40

## Datasets Generados

`licitaciones_resumen.csv`: dataset base desde respuestas diarias resumidas. Puede mantener duplicados si una licitacion aparece en distintos dias.

`licitaciones_detalladas.csv`: dataset principal, deduplicado por `codigo_externo`.

`licitaciones_items.csv`: items asociados a licitaciones cuando la API entrega esa informacion.

`licitaciones_scored.csv`: dataset detallado con score y prioridad.

`licitaciones_analysis_ready.csv`: version enriquecida para analisis.

`items_analysis_ready.csv`: version de items lista para analisis.

## Flujo Recomendado De Trabajo

1. Verifica conexion:

```powershell
python -m app.cli fetch-date --date 2026-04-04
```

2. Ejecuta una prueba pequena:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-02 --limit 30 --skip-existing-details
```

3. Aplica scoring:

```powershell
python -m app.cli score-dataset
```

4. Exporta analysis-ready:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-02
```

5. Si una corrida larga se interrumpe:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-02 --use-partials
```

6. Para reanudar evitando repetir detalles:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --skip-existing-details
```

## Notebooks

Los notebooks estan pensados para exploracion, limpieza y analisis:

- `notebooks/01_exploracion_api.ipynb`
- `notebooks/02_limpieza_licitaciones.ipynb`
- `notebooks/03_eda_oportunidades.ipynb`

## Casos De Uso

- Inteligencia comercial.
- Monitoreo de oportunidades.
- Analisis territorial.
- Priorizacion por rubro, estado, region y monto.
- Reporting institucional.
- Portafolio profesional de Data Analytics / Data Engineering.

## Troubleshooting

Si `python` no se reconoce:

```powershell
.venv\Scripts\python.exe -m app.cli --help
```

Si falta el ticket:

```text
MP_TICKET is empty
```

Revisa tu `.env` y confirma que `MP_TICKET` tenga un valor valido.

Si una corrida bulk demora demasiado:

```powershell
python -m app.cli build-bulk-dataset --start-date 2026-04-01 --end-date 2026-04-05 --limit 50 --skip-existing-details
```

Si solo tienes parciales y no finales:

```powershell
python -m app.cli export-analysis-ready --start-date 2026-04-01 --end-date 2026-04-05 --use-partials
```

## Supuestos Y Consideraciones

- La estructura de la API puede variar entre respuesta resumida y detallada.
- El codigo usa `.get()` y normalizacion defensiva para tolerar campos faltantes.
- Algunos campos pueden quedar como `None` o `NaN` si la API no los entrega.
- El proyecto depende de la disponibilidad y estabilidad de la API oficial de Mercado Publico.

## Futuras Mejoras

- Dashboard Streamlit sobre `licitaciones_scored.csv`.
- Persistencia completa en SQLite.
- Alertas por correo o Telegram.
- Automatizacion local programada.
- Analisis historico por organismo, region, monto y categoria.

## Disclaimer

Este proyecto depende de la disponibilidad, estabilidad y estructura de la API oficial de Mercado Publico / ChileCompra. Cambios en la API pueden requerir ajustes en cliente, transformaciones o scoring.
