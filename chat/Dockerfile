# syntax=docker/dockerfile:1
#
# Ratatoskr — de chat als image. Twee lagen, en de eerste is de enige die uitleg nodig
# heeft: de chat praat met de relay via de `buzz`-CLI, en die publiceert upstream
# alleen als broncode (de relay-image bevat buzz-relay/-admin/-pair, geen CLI).
# Daarom bouwen we 'm hier, uit DEZELFDE upstream-commit als de draaiende relay:
# één commit, één waarheid. Bump je BUZZ_REF, bump dan ook BUZZ_IMAGE.
#
# Bouwen:  docker build -f chat/Dockerfile -t ratatoskr-chat:<versie> .
# (context = de repo-root, want we kopiëren alleen chat/.)

ARG BUZZ_REF=4baccd5394d6166bb68ff03b24e376e322281a59

FROM rust:1.95-bookworm AS buzz-cli
ARG BUZZ_REF
RUN apt-get update && apt-get install -y --no-install-recommends \
      git pkg-config libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
# Shallow fetch van precies één commit: geen historie, geen drift.
RUN git init -q . \
 && git remote add origin https://github.com/block/buzz.git \
 && git fetch -q --depth 1 origin "$BUZZ_REF" \
 && git checkout -q FETCH_HEAD
RUN cargo build --release -p buzz-cli && strip target/release/buzz

FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.source="https://github.com/MWest2020/boomhuis"
LABEL org.opencontainers.image.description="Ratatoskr — chat (PWA + API) voor een zelf-gehoste buzz-relay"
LABEL org.opencontainers.image.licenses="MIT"

COPY --from=buzz-cli /src/target/release/buzz /usr/local/bin/buzz

# Non-root. De staat (auth.db, push-abonnees) staat in /var/lib/ratatoskr en komt
# uit een volume; de code in /app is read-only voor de gebruiker die 'm draait.
RUN useradd --system --uid 10001 --home /var/lib/ratatoskr --create-home ratatoskr \
 && chmod 0700 /var/lib/ratatoskr

WORKDIR /app
COPY chat/ /app/
RUN rm -rf /app/__pycache__ /app/e2e /app/test_*.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8090 \
    BIND_HOST=0.0.0.0 \
    BUZZ_BIN=/usr/local/bin/buzz \
    RATATOSKR_AUTH_DB=/var/lib/ratatoskr/auth.db \
    PUSH_SUBS_PATH=/var/lib/ratatoskr/push_subs.json

USER ratatoskr
EXPOSE 8090
VOLUME ["/var/lib/ratatoskr"]

# Geen curl/wget in slim, en die willen we er ook niet bij: stdlib doet het.
# /api/status is een open route (geen sessie nodig) — precies wat een probe hoort
# te raken.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD python3 -c "import os,urllib.request,sys; \
urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8090')+'/api/status', timeout=4).read(); sys.exit(0)" \
  || exit 1

CMD ["python3", "server.py"]
