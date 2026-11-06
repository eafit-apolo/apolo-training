# Imagen de la API: Python 3.12, usuario sin privilegios, gunicorn con
# workers de uvicorn. Se construye desde api/: docker build -t api api/
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Etapa 1: dependencias en un entorno virtual aparte, para copiarlo entero.
FROM base AS dependencias
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install -r requirements.txt

# Etapa de desarrollo (deploy/compose.dev.yaml): las mismas dependencias más
# las de prueba. El código no se copia: se monta desde api/. No entra a la
# imagen que se publica, que es la última etapa.
FROM dependencias AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
# Videos subidos (B-05). El compose de desarrollo monta aquí el volumen
# `media`, que toma estos permisos al crearse: la API corre con tu uid y tiene
# que poder escribir.
RUN install -d -m 1777 /srv/apolo-training/media
WORKDIR /app
EXPOSE 8000
# --reload-dir: vigila solo el código, no un .venv/ que tengas en api/.
CMD ["uvicorn", "app.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--reload-dir", "app", "--reload-dir", "migrations"]

# Etapa 2: la imagen final, sin pip cache ni herramientas de build.
FROM base
ARG VERSION=dev
ENV PATH=/opt/venv/bin:$PATH \
    API_VERSION=$VERSION \
    WEB_CONCURRENCY=2
# La carpeta de los videos subidos (B-05) es de api: así un volumen con nombre
# montado aquí nace con ese dueño. En la 117 la lee también nginx (W-05, W-06).
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin api \
 && install -d -o api -g api -m 755 /srv/apolo-training/media
WORKDIR /app
COPY --from=dependencias /opt/venv /opt/venv
# El código queda de root y solo lectura para el usuario api.
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
USER api
EXPOSE 8000

# python:3.12-slim no trae curl: se usa urllib. Un 503 (sin base de datos)
# también marca el contenedor como no sano.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

# create_app() como fábrica: cada worker lee el entorno y crea su motor.
# WEB_CONCURRENCY fija los workers; GUNICORN_CMD_ARGS permite agregar opciones.
# --no-control-socket: gunicorn 26 abre un socket en $HOME/.gunicorn, y el
# usuario api no tiene home (daría "Permission denied" en el log).
CMD ["gunicorn", "app.main:create_app()", \
     "--worker-class", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--no-control-socket"]
