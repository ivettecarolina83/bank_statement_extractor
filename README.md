# Bank Statement Extractor (MVP)

Módulo para extraer movimientos bancarios desde estados de cuenta (PDF digital inicialmente).

## Setup (Windows)

Activar entorno:
- .venv\Scripts\activate

Instalar el proyecto en modo editable:
- pip install -e .

Ejecutar extractor (Wells Fargo MVP):
- python -m extractor.pipeline samples\wells_fargo_sample.pdf --out out.json

Correr tests:
- pytest
