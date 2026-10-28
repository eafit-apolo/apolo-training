# Imagen del gateway de terminal: Python 3.12, usuario sin privilegios y
# uvicorn con un solo proceso (las sesiones abiertas viven en memoria).
# Se construye desde terminal/: docker build -t terminal terminal/
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

# Etapa 2: la imagen final, sin pip cache ni herramientas de build.
FROM base
ARG VERSION=dev
ENV PATH=/opt/venv/bin:$PATH \
    TERMINAL_VERSION=$VERSION
RUN useradd --system --uid 10002 --no-create-home --shell /usr/sbin/nologin terminal
WORKDIR /app
COPY --from=dependencias /opt/venv /opt/venv
# El código queda de root y solo lectura para el usuario terminal.
COPY app ./app
USER terminal
EXPOSE 8001

# python:3.12-slim no trae curl: se usa urllib.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8001/health', timeout=4)"]

# Un solo proceso a propósito: con varios, cada uno tendría su propio registro
# de sesiones y «una sesión por usuario» dejaría de cumplirse.
CMD ["uvicorn", "app.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8001", \
     "--no-server-header"]
