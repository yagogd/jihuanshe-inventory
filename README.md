# Jihuanshe Tracker

Aplicación local para importar órdenes de Jihuanshe desde Android mediante ADB, revisar sus cartas y conservar los datos de compra en SQLite.

El proyecto utiliza FastAPI, SQLAlchemy y SQLite en el backend, y React con Vite en el frontend. El alcance y las decisiones técnicas están documentados en [PLAN.md](PLAN.md).

## Requisitos

- Python 3.12 o posterior.
- Node.js 18 o posterior.
- Android Platform Tools (`adb`).
- Un dispositivo Android con depuración USB habilitada y Jihuanshe abierto en el detalle de una orden.

## Instalación

```powershell
git clone <URL_DEL_REPOSITORIO>
cd jihuanshe_tracker
python -m pip install -e ".[dev]"
cd frontend
npm install
```

Si `adb` no está disponible en `PATH`, configura su ruta antes de iniciar el backend:

```powershell
$env:JIHUANSHE_ADB = "C:\Android\platform-tools\adb.exe"
```

Las demás opciones disponibles aparecen en [.env.example](.env.example). La aplicación lee variables de entorno; no carga el archivo `.env` automáticamente.

## Ejecución

Backend, desde la raíz del proyecto:

```powershell
uvicorn app.main:app --reload
```

Frontend, en otra terminal:

```powershell
cd frontend
npm run dev
```

Abre la dirección que muestra Vite, normalmente `http://localhost:5173`.

## Pruebas y compilación

```powershell
pytest
ruff check .
cd frontend
npm run build
```

## Datos locales

La base de datos, las imágenes recortadas y los dumps XML se guardan en `data/`. Ese directorio, los archivos `.env` y los volcados del dispositivo están excluidos de Git para evitar publicar datos personales.

## Estado

Actualmente están implementadas todas las fases del plan (0–12): extracción ADB, revisión, persistencia, edición y ajustes, estados de orden, envíos CN→ES, motor de costes (landed cost), inventario con lotes, listados/ventas con beneficio y ROI, y pantalla de resumen. Consulta [PLAN.md](PLAN.md) para el roadmap completo.
