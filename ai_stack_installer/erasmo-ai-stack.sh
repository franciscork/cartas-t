#!/usr/bin/env bash
# ============================================================================
#  ERASMO AI STACK v1.1
#  Orquestador de instalación para WSL2 / BlackArch / Arch-based
#  + Reverse proxy Caddy (HTTPS) con dashboard integrado y Let's Encrypt opcional
#
#  Características:
#    · Menú interactivo (sin args) y sub-comandos: --install|--uninstall|
#      --status|--update-models|--help|--dry-run
#    · Reverse proxy Caddy por defecto (HTTPS auto-TLS); Nginx opcional con
#      ERASMO_AI_USE_NGINX=1 para entornos sin Caddy
#    · Dashboard HTML servido por Caddy en / con healthchecks visuales
#      de Open WebUI, AnythingLLM y Ollama (auto-refresh 30s)
#    · Let's Encrypt automático si ERASMO_AI_DOMAIN resuelve públicamente
#    · Self-signed cert automático en modo dev (sin dominio)
#    · Idempotente: seguro re-ejecutar
#    · Logging a ~/.erasmo-ai-stack.log
#    · Auto-recovery: detecta estado parcial y continúa
#
#  Uso:
#    ./erasmo-ai-stack.sh                → menú interactivo
#    ./erasmo-ai-stack.sh --install      → instalación completa
#    ./erasmo-ai-stack.sh --uninstall    → eliminación guiada
#    ./erasmo-ai-stack.sh --status       · dashboard de salud
#    ./erasmo-ai-stack.sh --update-models→ re-descarga modelos
#    ./erasmo-ai-stack.sh --help         → esta ayuda
#
#  Variables de entorno (override defaults):
#    ERASMO_AI_USER      usuario dedicado (default: aiuser)
#    ERASMO_AI_MODELS    modelos a instalar (separados por espacio)
#    ERASMO_AI_PORT      puerto público HTTPS (default: 8443)
#    ERASMO_AI_DOMAIN    dominio público para Let's Encrypt (auto si resuelve)
#    ERASMO_AI_PROXY     "caddy" (default) | "nginx" (legacy)
#    ERASMO_AI_USE_NGINX "1" alias de PROXY=nginx (back-compat)
#    ERASMO_AI_NOAUTH=1  deshabilita basic-auth (solo dev)
#    ERASMO_AI_SKIP_PROXY=1   no configurar proxy/caddy ni firewall
#    ERASMO_AI_SKIP_DOCKER=1  no levantar contenedores Docker
#    ERASMO_AI_SKIP_MODELS=1  no descargar modelos en --install
# ============================================================================
set -Eeuo pipefail
IFS=$'\n\t'

# ── CONSTANTES ────────────────────────────────────────────────────────────
readonly VERSION="1.1.0"
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_FILE="${HOME}/.erasmo-ai-stack.log"
readonly LOCK_FILE="/tmp/.erasmo-ai-stack.lock"

readonly DEFAULT_MODELS=(
  "qwen3:7b-q4_K_M"
  "deepseek-r1:7b-q4_K_M"
  "mistral:7b-q4_K_M"
  "nomic-embed-text"
)
readonly OLLAMA_URL="http://localhost:11434"
readonly WEBUI_CONTAINER="open-webui"
readonly WEBUI_PORT=3000
readonly ANYTHING_CONTAINER="anythingllm"
readonly ANYTHING_PORT=3001
# Proxy mode: caddy por defecto; nginx con ERASMO_AI_USE_NGINX=1 o PROXY=nginx
if [[ "${ERASMO_AI_USE_NGINX:-0}" == "1" || "${ERASMO_AI_PROXY:-}" == "nginx" ]]; then
  readonly PROXY_MODE="nginx"
else
  readonly PROXY_MODE="caddy"
fi

readonly NGINX_PORT="${ERASMO_AI_PORT:-8443}"     # alias legacy (compat con config nginx)
readonly PUBLIC_PORT="${ERASMO_AI_PORT:-8443}"    # puerto HTTPS principal
readonly NGINX_CONF="/etc/nginx/conf.d/ai.conf"
readonly HTPASSWD_FILE="/etc/nginx/.htpasswd"     # usado por caddy+nginx (mismo formato)
readonly CADDY_BIN="/usr/bin/caddy"
readonly CADDY_HOME="${HOME}/ai_caddy"
readonly CADDYFILE="${CADDY_HOME}/Caddyfile"
readonly CADDY_LOG="${CADDY_HOME}/access.log"
readonly AI_USER="${ERASMO_AI_USER:-aiuser}"
readonly PUBLIC_DOMAIN="${ERASMO_AI_DOMAIN:-}"

# ── COLORES ───────────────────────────────────────────────────────────────
if [[ -t 1 ]] && command -v tput >/dev/null && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RED=$'\033[1;31m'
  C_GREEN=$'\033[1;32m'
  C_YELLOW=$'\033[1;33m'
  C_BLUE=$'\033[1;34m'
  C_CYAN=$'\033[1;36m'
  C_MAGENTA=$'\033[1;35m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_CYAN=""; C_MAGENTA=""
fi

# ── HELPERS ───────────────────────────────────────────────────────────────
_ts()    { date '+%Y-%m-%d %H:%M:%S'; }
_log()   { printf '%s [%s] %s\n' "$(_ts)" "$1" "$2" >>"$LOG_FILE"; }
_print() { printf '%s%s%s\n' "$2" "$1" "$C_RESET" >&2; }

log()  { _print "$1" "$C_CYAN";    _log "INFO"  "$1"; }
warn() { _print "$1" "$C_YELLOW";   _log "WARN"  "$1"; }
err()  { _print "$1" "$C_RED";      _log "ERROR" "$1"; }
ok()   { _print "✔ $1" "$C_GREEN";  _log "OK"    "$1"; }
hdr()  { printf '\n%s━━━ %s ━━━%s\n' "$C_BOLD$C_MAGENTA" "$1" "$C_RESET"; _log "STEP" "$1"; }

die() { err "$*"; exit 2; }

# Trap para mostrar errores limpios
trap 'ec=$?; [[ $ec -ne 0 ]] && err "Fallo inesperado (exit $ec) — revisa $LOG_FILE"' EXIT

# Lock anti-doble-instalación
acquire_lock() {
  if [[ -e "$LOCK_FILE" ]]; then
    local other_pid; other_pid="$(cat "$LOCK_FILE" 2>/dev/null || echo '?')"
    if kill -0 "$other_pid" 2>/dev/null; then
      die "Otra instancia en curso (pid $other_pid). Borra $LOCK_FILE si quedó colgada."
    else
      warn "Lock huérfano encontrado, limpiando."
      rm -f "$LOCK_FILE"
    fi
  fi
  echo "$$" >"$LOCK_FILE"
}
acquire_lock_with_trap() {
  # Toma el lock Y reemplaza el trap global por uno que libera + reporta error.
  acquire_lock
  trap 'release_lock; ec=$?; [[ $ec -ne 0 ]] && err "Comando abortado (exit $ec) — log: $LOG_FILE"' EXIT
}
release_lock() { rm -f "$LOCK_FILE"; }

# ¿Es root o tiene sudo?
have_sudo() { sudo -n true 2>/dev/null; }

# Confirm interactivo (yes/no)
confirm() {
  local prompt="${1:-¿Continuar?}"
  local default="${2:-n}"
  local ans
  if [[ ! -t 0 ]]; then
    [[ "$default" == "y" ]] && return 0 || return 1
  fi
  if [[ "$default" == "y" ]]; then
    read -rp "$(printf '%s%s [Y/n]: %s' "$C_BOLD" "$prompt" "$C_RESET")" ans
    ans="${ans:-y}"
  else
    read -rp "$(printf '%s%s [y/N]: %s' "$C_BOLD" "$prompt" "$C_RESET")" ans
    ans="${ans:-n}"
  fi
  [[ "$ans" =~ ^[Yy]([Ee][Ss])?$ ]]
}

# ── PREFLIGHT ─────────────────────────────────────────────────────────────
preflight() {
  hdr "PREFLIGHT"
  [[ "$(uname -s)" == "Linux" ]] || die "Solo funciona en Linux (detectado: $(uname -s))."
  command -v pacman >/dev/null || die "pacman no encontrado. ¿Seguro que es Arch/BlackArch?"

  if grep -qi microsoft /proc/version 2>/dev/null; then
    ok "WSL2 detectado"
  else
    warn "No parece WSL2 (continuo igualmente)."
  fi

  if command -v nvidia-smi >/dev/null; then
    nvidia-smi --query-gpu=name,memory.total,temperature.gpu --format=csv,noheader \
      | head -1 | awk -F'","' '{printf "  GPU: %s (%s MB, %s)\n",$1,$2,$3}' >&2
  else
    warn "Sin nvidia-smi → Ollama funcionará en CPU (lento)."
  fi

  local avail_gb; avail_gb=$(df --output=avail -BG / 2>/dev/null | tail -1 | tr -dc '0-9' || echo 0)
  if (( avail_gb < 30 )); then
    die "Solo ${avail_gb} GB libres. Necesitas ≥ 30 GB para modelos + UIs."
  else
    ok "Espacio en disco: ${avail_gb} GB disponibles"
  fi

  have_sudo || die "Se requieren permisos sudo. Ejecuta: sudo -v"
  ok "Sudo OK"
}

# ── INSTALL: PAQUETES BASE ───────────────────────────────────────────────
install_packages() {
  hdr "INSTALACIÓN · paquetes base"
  sudo pacman -Syu --noconfirm
  local pkgs=(git python python-virtualenv docker docker-compose base-devel wget fuse2 ufw curl)
  # apache-tools trae htpasswd; útil para Caddy (mismo formato de archivo).
  pkgs+=(apache-tools)
  if [[ "$PROXY_MODE" == "caddy" ]]; then
    pkgs+=(caddy)
  else
    pkgs+=(nginx)
  fi
  sudo pacman -S --noconfirm --needed "${pkgs[@]}"
  sudo systemctl enable --now docker
  ok "Paquetes base instalados (proxy=${PROXY_MODE})"
}

# ── INSTALL: USUARIO DEDICADO (idempotente) ──────────────────────────────
setup_user() {
  hdr "INSTALACIÓN · usuario $AI_USER"
  if id "$AI_USER" &>/dev/null; then
    ok "Usuario $AI_USER ya existe"
  else
    sudo useradd -m -s /bin/bash "$AI_USER"
    ok "Usuario $AI_USER creado"
  fi
  sudo usermod -aG docker "$AI_USER"
  # Asegura que el usuario actual también
  if [[ "$USER" != "$AI_USER" ]]; then
    sudo usermod -aG docker "$USER" 2>/dev/null || true
  fi
  ok "Permisos de docker configurados"
}

# ── INSTALL: OLLAMA ──────────────────────────────────────────────────────
install_ollama() {
  hdr "INSTALACIÓN · Ollama"
  if ! command -v ollama >/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
  else
    ok "Ollama ya está instalado"
  fi
  sudo systemctl enable --now ollama
  wait_ollama
}

wait_ollama() {
  log "Esperando a Ollama…"
  for i in {1..60}; do
    if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
      ok "Ollama responde en :11434"
      return 0
    fi
    sleep 1
  done
  die "Ollama no responde tras 60s. Revisa: journalctl -u ollama -n 50"
}

pull_models() {
  local models=("${@:-${DEFAULT_MODELS[@]}}")
  hdr "DESCARGA · modelos (${#models[@]})"
  for m in "${models[@]}"; do
    log "→ $m"
    if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$m"; then
      ok "  $m ya presente"
    else
      ollama pull "$m"
      ok "  $m descargado"
    fi
  done
}

update_models() {
  hdr "ACTUALIZACIÓN · modelos"
  local models
  if [[ $# -eq 0 ]]; then
    mapfile -t models < <(ollama list 2>/dev/null | awk 'NR>1 && $1!="" {print $1}')
    [[ ${#models[@]} -eq 0 ]] && die "No hay modelos instalados. Usa --install primero."
  else
    models=("$@")
  fi
  for m in "${models[@]}"; do
    log "Re-pull $m"
    ollama pull "$m" && ok "$m actualizado"
  done

  # Mostrar modelos huérfanos (no en DEFAULT_MODELS ni usados recientemente)
  log "Limpieza opcional: "
  ollama list
  echo
  if confirm "¿Borrar modelos no listados en DEFAULT_MODELS? (recomendado: solo si tienes prisa de espacio)" n; then
    local default_list=" ${DEFAULT_MODELS[*]} "
    while read -r line; do
      [[ -z "$line" ]] && continue
      local name; name="$(awk '{print $1}' <<<"$line")"
      [[ -z "${name:-}" ]] && continue
      # '${name}' entrecomillado evita expansión de comodines tipo '*' o '?'
      [[ " $default_list " == *"${name}"* ]] && continue
      if confirm "  ¿Borrar ${name}?" n; then
        ollama rm "${name}"
      fi
    done < <(ollama list | tail -n +2 | awk 'NF')
  fi
}

# ── INSTALL: OPEN WEBUI ──────────────────────────────────────────────────
install_open_webui() {
  hdr "INSTALACIÓN · Open WebUI"
  docker rm -f "$WEBUI_CONTAINER" 2>/dev/null || true
  docker run -d --name "$WEBUI_CONTAINER" --restart unless-stopped \
    -p "${WEBUI_PORT}:8080" \
    --add-host=host.docker.internal:host-gateway \
    -v "${HOME}/open-webui":/app/backend/data \
    ghcr.io/open-webui/open-webui:main
  ok "Open WebUI corriendo en :$WEBUI_PORT"
  sleep 2
}

# ── INSTALL: ANYTHINGLLM ─────────────────────────────────────────────────
install_anythingllm() {
  hdr "INSTALACIÓN · AnythingLLM"
  docker rm -f "$ANYTHING_CONTAINER" 2>/dev/null || true
  docker run -d --name "$ANYTHING_CONTAINER" --restart unless-stopped \
    -p "${ANYTHING_PORT}:3001" \
    -v "${HOME}/anythingllm":/app/server/storage \
    --add-host=host.docker.internal:host-gateway \
    mintplexlabs/anythingllm:latest
  ok "AnythingLLM corriendo en :$ANYTHING_PORT"
  sleep 2
}

# ── INSTALL: JAN.AI ──────────────────────────────────────────────────────
install_jan() {
  hdr "INSTALACIÓN · Jan.ai (AppImage compatible WSL2)"
  mkdir -p "${HOME}/jan"
  if [[ ! -f "${HOME}/jan/jan.AppImage" ]]; then
    log "Descargando Jan.ai…"
    wget -q --show-progress "https://jan.ai/download/latest/linux" -O "${HOME}/jan/jan.AppImage"
    chmod +x "${HOME}/jan/jan.AppImage"
  else
    ok "Jan.AppImage ya descargado"
  fi
  cat >"${HOME}/jan/run-jan.sh" <<'SH'
#!/usr/bin/env bash
# Wrapper WSL2-compatible: --appimage-extract-and-run evita FUSE.
cd "$(dirname "$0")"
exec ./jan.AppImage --appimage-extract-and-run "$@"
SH
  chmod +x "${HOME}/jan/run-jan.sh"
  ok "Jan.ai instalado. Ejecuta con: ~/jan/run-jan.sh"
}

# ── INSTALL: vLLM (opcional y seguro) ───────────────────────────────────
install_vllm() {
  hdr "INSTALACIÓN · vLLM (opcional)"
  local pyv; pyv=$(python -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
  if [[ "$(printf '%s\n3.11\n' "$pyv" | sort -V | head -1)" != "3.11" ]] \
     && [[ "$(printf '%s\n3.10\n' "$pyv" | sort -V | head -1)" != "3.10" ]]; then
    warn "Python ${pyv} detectado: vLLM requiere 3.10/3.11 → omitido"
    warn "Si lo necesitas: instala Python 3.11 (pyenv) y vuelve a correr --install"
    return 0
  fi
  if [[ -d "${HOME}/vllm-env" ]]; then
    ok "venv vLLM ya existe en ~/vllm-env"
    return 0
  fi
  python -m venv "${HOME}/vllm-env"
  # shellcheck source=/dev/null
  source "${HOME}/vllm-env/bin/activate"
  pip install --quiet --upgrade pip wheel
  pip install --quiet vllm
  ok "vLLM en ~/vllm-env. Activar con: source ~/vllm-env/bin/activate"
}

# ── INSTALL: NGINX (LEGACY) ──────────────────────────────────────────────
configure_nginx_legacy() {
  hdr "CONFIGURACIÓN · Nginx legacy + auth (puerto ${NGINX_PORT})"
  if [[ -f /etc/nginx/nginx.conf ]] && [[ ! -f /etc/nginx/nginx.conf.erasmo.bak ]]; then
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.erasmo.bak
    ok "Backup de nginx.conf → /etc/nginx/nginx.conf.erasmo.bak"
  fi

  if [[ ! -f "$HTPASSWD_FILE" ]]; then
    warn "Creando htpasswd inicial. Te pedirá contraseña."
    sudo htpasswd -c "$HTPASSWD_FILE" erasmo
  else
    ok "htpasswd ya existe con usuarios: $(sudo awk -F: '{print $1}' "$HTPASSWD_FILE" | tr '\n' ' ')"
  fi

  local auth_block=""
  if [[ "${ERASMO_AI_NOAUTH:-0}" == "1" ]]; then
    warn "⚠ ERASMO_AI_NOAUTH=1 → auth deshabilitada (solo dev)"
  else
    printf -v auth_block 'auth_basic           "AI Stack — restringido";\n    auth_basic_user_file %s;' "$HTPASSWD_FILE"
  fi

  sudo tee "$NGINX_CONF" > /dev/null <<NGINX
server {
    listen ${NGINX_PORT};
    server_name _;

    ${auth_block}

    client_max_body_size 200m;

    location /webui/ {
        proxy_pass         http://127.0.0.1:${WEBUI_PORT}/;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
    }
    location /rag/ {
        proxy_pass         http://127.0.0.1:${ANYTHING_PORT}/;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
    }
    location /ollama/ {
        proxy_pass         http://127.0.0.1:11434/;
        proxy_set_header   Host              \$host;
    }
}
NGINX

  sudo nginx -t && sudo systemctl restart nginx
  ok "Nginx legacy reiniciado en :$NGINX_PORT"
}

# ── INSTALL: HTPASSWD (compartido caddy + nginx) ──────────────────────────
ensure_htpasswd() {
  hdr "AUTH · htpasswd compartido (Caddy + Nginx)"
  if [[ "${ERASMO_AI_NOAUTH:-0}" == "1" ]]; then
    warn "⚠ ERASMO_AI_NOAUTH=1 → auth deshabilitada (solo dev)"
    return 0
  fi
  if [[ ! -f "$HTPASSWD_FILE" ]]; then
    if [[ ! -t 0 ]]; then
      # Modo no interactivo: crea usuario 'erasmo' con pass aleatorio y la imprime.
      local rpass; rpass="$(openssl rand -hex 12)"
      sudo htpasswd -bcB "$HTPASSWD_FILE" erasmo "$rpass"
      warn "htpasswd creado en modo no-tty con password ALEATORIA."
      warn "═════ ANOTA ESTA CONTRASEÑA ═════"
      warn "  user:     erasmo"
      warn "  password: ${rpass}"
      warn "══════════════════════════════════"
    else
      warn "Creando htpasswd inicial. Te pedirá contraseña."
      sudo htpasswd -cB "$HTPASSWD_FILE" erasmo
    fi
  else
    ok "htpasswd ya existe con usuarios: $(sudo awk -F: '{print $1}' "$HTPASSWD_FILE" | tr '\n' ' ')"
  fi
}

# ── INSTALL: DASHBOARD HTML estático ─────────────────────────────────────
write_dashboard() {
  hdr "CONFIGURACIÓN · dashboard HTML (auto-refresh healthchecks)"
  mkdir -p "${CADDY_HOME}/dashboard"
  local out="${CADDY_HOME}/dashboard/index.html"
  # <<'DASHBOARD' (comilla simple) → NO expande ${} en el heredoc.
  cat >"$out" <<'DASHBOARD'
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Erasmo AI Stack · Dashboard</title>
<style>
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface-2: #21262d;
  --text: #c9d1d9;
  --text-dim: #8b949e;
  --green: #3fb950;
  --yellow: #d29922;
  --red: #f85149;
  --blue: #58a6ff;
  --purple: #d2a8ff;
  --border: #30363d;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;
  background: linear-gradient(135deg, #0d1117 0%, #15192b 70%, #1a1f2e 100%);
  color: var(--text);
  min-height: 100vh;
  padding: 32px 24px;
}
header {
  max-width: 1200px;
  margin: 0 auto 28px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--border);
  padding-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
h1 { margin: 0; font-size: 24px; font-weight: 600; }
h1 .accent { color: var(--purple); }
.last-check { color: var(--text-dim); font-size: 13px; font-family: ui-monospace, 'Cascadia Code', 'Fira Code', monospace; }
main { max-width: 1200px; margin: 0 auto; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px;
  position: relative;
  transition: border-color 180ms ease, transform 180ms ease;
}
.card:hover { border-color: var(--blue); transform: translateY(-2px); }
.card h2 {
  margin: 0 0 6px;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.role { color: var(--text-dim); font-size: 13px; margin: 0 0 18px; }
.badge {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  white-space: nowrap;
}
.badge.ok      { background: rgba(63,185,80,0.15);  color: var(--green); }
.badge.warn    { background: rgba(210,153,34,0.18); color: var(--yellow); }
.badge.err     { background: rgba(248,81,73,0.18);  color: var(--red); }
.badge.loading { background: rgba(88,166,255,0.18); color: var(--blue); animation: pulse 1.5s infinite; }
@keyframes pulse {
  0%,100% { opacity: 1; }
  50%     { opacity: 0.4; }
}
.metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.metric {
  background: var(--surface-2);
  padding: 11px 13px;
  border-radius: 8px;
}
.metric .label {
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 3px;
}
.metric .value {
  font-size: 15px;
  font-weight: 600;
  word-break: break-word;
}
.link { color: var(--blue); text-decoration: none; }
.link:hover { text-decoration: underline; }
footer {
  max-width: 1200px;
  margin: 40px auto 0;
  text-align: center;
  color: var(--text-dim);
  font-size: 12px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}
.refresh-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--green);
  margin-right: 6px;
  vertical-align: middle;
  animation: blink 2s infinite;
}
@keyframes blink {
  0%,100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
</head>
<body>
<header>
  <h1>🏭 Erasmo AI Stack <span class="accent">— Dashboard</span></h1>
  <span class="last-check"><span class="refresh-dot"></span><span id="lastCheck">comprobando…</span></span>
</header>
<main>
  <div class="cards">

    <div class="card" id="ollama">
      <h2>🧠 Ollama <span class="badge loading">…</span></h2>
      <p class="role">Servidor de modelos LLM local</p>
      <div class="metrics">
        <div class="metric">
          <div class="label">API</div>
          <div class="value"><a class="link" href="/ollama/" target="_blank" rel="noopener">/ollama/</a></div>
        </div>
        <div class="metric">
          <div class="label">Modelos</div>
          <div class="value models-count">—</div>
        </div>
        <div class="metric">
          <div class="label">Última probe</div>
          <div class="value latency">—</div>
        </div>
        <div class="metric">
          <div class="label">HTTP</div>
          <div class="value http-status">—</div>
        </div>
      </div>
    </div>

    <div class="card" id="webui">
      <h2>🖥️ Open WebUI <span class="badge loading">…</span></h2>
      <p class="role">Chat tipo ChatGPT con RAG y multi-usuario</p>
      <div class="metrics">
        <div class="metric">
          <div class="label">UI</div>
          <div class="value"><a class="link" href="/webui/" target="_blank" rel="noopener">/webui/</a></div>
        </div>
        <div class="metric">
          <div class="label">Estado</div>
          <div class="value container">—</div>
        </div>
        <div class="metric">
          <div class="label">Latencia</div>
          <div class="value latency">—</div>
        </div>
        <div class="metric">
          <div class="label">HTTP</div>
          <div class="value http-status">—</div>
        </div>
      </div>
    </div>

    <div class="card" id="anything">
      <h2>📚 AnythingLLM <span class="badge loading">…</span></h2>
      <p class="role">Workspaces, agentes, RAG avanzado</p>
      <div class="metrics">
        <div class="metric">
          <div class="label">UI</div>
          <div class="value"><a class="link" href="/rag/" target="_blank" rel="noopener">/rag/</a></div>
        </div>
        <div class="metric">
          <div class="label">Estado</div>
          <div class="value workspace">—</div>
        </div>
        <div class="metric">
          <div class="label">Latencia</div>
          <div class="value latency">—</div>
        </div>
        <div class="metric">
          <div class="label">HTTP</div>
          <div class="value http-status">—</div>
        </div>
      </div>
    </div>
  </div>
</main>
<footer>
  Auto-refresh cada 30 s &middot;
  <a class="link" href="javascript:tick()">probar ahora</a> &middot;
  Erasmo AI Stack &middot;
  <span id="total-probes">0 probes</span>
</footer>
<script>
async function probe(name, url, expectOk, tagSel) {
  const card = document.getElementById(name);
  const badge = card.querySelector('.badge');
  const latencyEl = card.querySelector('.latency');
  const httpEl = card.querySelector('.http-status');
  // tagSel: opcional, nombre de clase de un div interno extra a actualizar
  // con un estado legible ("✓ up" / "✗ down") cuando existe.
  const tagEl = tagSel ? card.querySelector('.' + tagSel) : null;
  const setTag = (down) => { if (tagEl) tagEl.textContent = down ? '✗ down' : '✓ up'; };
  const t0 = performance.now();
  try {
    const r = await fetch(url, { credentials: 'omit', cache: 'no-store', redirect: 'follow' });
    const ms = Math.round(performance.now() - t0);
    latencyEl.textContent = ms + ' ms';
    httpEl.textContent = r.status;
    if (expectOk.includes(r.status) || (r.ok && expectOk === undefined)) {
      badge.className = 'badge ok'; badge.textContent = '✓ UP'; setTag(false);
      return true;
    }
    if (r.status >= 400 && r.status < 500) {
      // 401/403 = requiere auth pero el servicio ESTÁ vivo
      badge.className = 'badge ok'; badge.textContent = '✓ ' + r.status; setTag(false);
      return true;
    }
    if (r.status >= 500) {
      badge.className = 'badge err'; badge.textContent = '✗ ' + r.status; setTag(true);
      return false;
    }
    badge.className = 'badge warn'; badge.textContent = '~ ' + r.status; setTag(true);
    return false;
  } catch (e) {
    latencyEl.textContent = 'timeout';
    httpEl.textContent = '0';
    badge.className = 'badge err'; badge.textContent = '✗ OFFLINE'; setTag(true);
    return false;
  }
}
let probeCount = 0;
async function ollamaProbe() {
  const ok = await probe('ollama', '/ollama/', [200]);
  if (!ok) return;
  try {
    const r = await fetch('/ollama/api/tags', { cache: 'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    const count = d.models ? d.models.length : 0;
    const e = document.querySelector('#ollama .models-count');
    if (e) e.textContent = count + ' cargados';
  } catch (e) {}
}
async function tick() {
  await Promise.all([
    ollamaProbe(),
    probe('webui',    '/webui/', [], 'container'),
    probe('anything', '/rag/',  [], 'workspace'),
  ]);
  const now = new Date();
  const lc = document.getElementById('lastCheck');
  if (lc) lc.textContent = 'última: ' + now.toLocaleString();
  probeCount++;
  const tp = document.getElementById('total-probes');
  if (tp) tp.textContent = probeCount + ' probe' + (probeCount === 1 ? '' : 's');
}
// Segunda def. de tick() eliminada tras review (consolidada arriba).
tick();
setInterval(tick, 30000);
</script>
</body>
</html>
DASHBOARD
  local bytes; bytes=$(wc -c <"$out")
  ok "Dashboard → ${out} (${bytes} bytes)"
}

# ── INSTALL: CADDY + HTTPS + DASHBOARD ────────────────────────────────────
__caddy_basicauth_block() {
  if [[ "${ERASMO_AI_NOAUTH:-0}" == "1" ]]; then
    echo "    basicauth_disabled: true"
    return
  fi
  [[ -f "$HTPASSWD_FILE" ]] || return
  # Usamos sudo + cat para soportar archivos propiedad de root.
  echo "    basicauth {"
  while IFS=: read -r user hash; do
    [[ -z "${user:-}" || -z "${hash:-}" ]] && continue
    echo "        ${user} ${hash}"
  done < <(sudo cat "$HTPASSWD_FILE" 2>/dev/null)
  echo "    }"
}

write_caddyfile() {
  hdr "CONFIGURACIÓN · Caddyfile (HTTPS)"
  mkdir -p "$CADDY_HOME"

  local site_addr tls_line
  if [[ -n "$PUBLIC_DOMAIN" ]]; then
    site_addr="https://${PUBLIC_DOMAIN}"
    tls_line=""  # Caddy intentará Let's Encrypt automáticamente.
    ok "Modo TLS: Let's Encrypt con dominio '${PUBLIC_DOMAIN}'"
    warn "  → requiere que el dominio resuelva a esta IP y puerto 80/443 reachable"
  else
    site_addr="https://:${PUBLIC_PORT}"
    tls_line="    tls internal"  # self-signed cert (Caddy internal CA)
    warn "Modo TLS: cert self-signed (HTTPS, no confiará el navegador hasta aceptar)"
    warn "  → Para Let's Encrypt, define ERASMO_AI_DOMAIN=tu-dominio.ddns.net"
  fi

  local basicauth_block
  basicauth_block="$(__caddy_basicauth_block)"

  cat >"$CADDYFILE" <<CADDYFILE
# Generado por erasmo-ai-stack v${VERSION} · $(date '+%Y-%m-%d %H:%M:%S')
# NO editar a mano — se sobrescribirá en cada --install.

{
    admin off
    auto_https off
}

${site_addr} {
${tls_line}

${basicauth_block}

    # Dashboard HTML en root
    root * ${CADDY_HOME}/dashboard
    encode gzip zstd
    file_server

    # Reverse proxies a backends locales.
    # handle_path STRIPEA el prefijo (/webui/foo → /foo en backend),
    # necesario porque Open WebUI/Ollama/AnythingLLM no esperan el prefijo.
    handle_path /webui/* {
        reverse_proxy 127.0.0.1:${WEBUI_PORT}
    }
    handle_path /rag/* {
        reverse_proxy 127.0.0.1:${ANYTHING_PORT}
    }
    handle_path /ollama/* {
        reverse_proxy 127.0.0.1:11434
    }

    log {
        output file ${CADDY_LOG} {
            roll_size 50mb
            roll_keep 5
        }
    }
}
CADDYFILE

  ok "Caddyfile → ${CADDYFILE}"
}

configure_caddy() {
  write_dashboard
  write_caddyfile

  if ! command -v caddy >/dev/null; then
    die "Binario '${CADDY_BIN}' no encontrado. ¿Fallo install_packages?"
  fi

  # Validar el Caddyfile con 'caddy adapt' antes de levantar.
  log "Validando Caddyfile…"
  caddy adapt --config "$CADDYFILE" --pretty > "${CADDY_HOME}/caddy.json.tmp" 2> "${CADDY_HOME}/caddy.validate.log" \
    || die "Caddyfile inválido. Log: ${CADDY_HOME}/caddy.validate.log"
  mv "${CADDY_HOME}/caddy.json.tmp" "${CADDY_HOME}/caddy.json"

  # Caddy systemd unit simple (sin Homebrew/Docker).
  local unit_file="/etc/systemd/system/erasmo-caddy.service"
  sudo tee "$unit_file" > /dev/null <<UNIT
[Unit]
Description=Erasmo AI Stack · Caddy reverse proxy + HTTPS dashboard
After=network-online.target ollama.service docker.service
Wants=network-online.target

[Service]
Type=notify
User=${USER}
ExecStart=${CADDY_BIN} run --environ --config ${CADDY_HOME}/caddy.json
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
UNIT

  sudo systemctl daemon-reload
  sudo systemctl enable --now erasmo-caddy
  ok "Caddy systemd unit activo (erasmo-caddy). HTTPS en :${PUBLIC_PORT}"
}

# ── INSTALL: ROUTER (selecciona Caddy o Nginx) ─────────────────────────────
configure_proxy() {
  if [[ "$PROXY_MODE" == "caddy" ]]; then
    configure_caddy
  else
    warn "PROXY_MODE=nginx (ERASMO_AI_USE_NGINX=1) → legacy sin dashboard, sin HTTPS auto"
    configure_nginx_legacy
  fi
}

# ── INSTALL: FIREWALL ────────────────────────────────────────────────────
configure_firewall() {
  hdr "CONFIGURACIÓN · firewall (UFW)"
  if ! command -v ufw >/dev/null; then
    warn "ufw no instalado (skip)"
    return 0
  fi
  # NO hacemos 'ufw --force reset' (destruye reglas preexistentes del usuario).
  # Solo añadimos las nuestras encima, y preguntamos antes.
  if ! confirm "¿Aplicar reglas UFW del stack? (NO borra reglas preexistentes)" y; then
    warn "UFW no modificado"
    return 0
  fi
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow from 127.0.0.1 to any port "$WEBUI_PORT"    comment 'Open WebUI (Stack AI)'
  sudo ufw allow from 127.0.0.1 to any port "$ANYTHING_PORT" comment 'AnythingLLM (Stack AI)'
  sudo ufw allow from 127.0.0.1 to any port 11434            comment 'Ollama (Stack AI)'
  if [[ "${ERASMO_AI_NOAUTH:-0}" != "1" ]]; then
    local fw_port; fw_port="$([[ $PROXY_MODE == caddy ]] && echo "$PUBLIC_PORT" || echo "$NGINX_PORT")"
    local fw_label; fw_label="$([[ $PROXY_MODE == caddy ]] && echo 'Caddy HTTPS' || echo 'Nginx HTTP')"
    sudo ufw allow from 127.0.0.1 to any port "$fw_port"     comment "${fw_label} proxy (Stack AI)"
  fi
  sudo ufw --force enable
  ok "Reglas UFW del stack aplicadas (sin reset destructivo)"
}

# ── HEALTH CHECK HELPERS ─────────────────────────────────────────────────
check_port() {
  local port=$1
  local start_ts; start_ts=$(date +%s)
  local code
  code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:${port}/" 2>/dev/null || echo "000")
  local ms=$(( $(date +%s) - start_ts ))
  echo "$code $ms"
}
check_port_unauth() {
  local port=$1
  local code
  code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:${port}/" 2>/dev/null || echo "000")
  echo "$code"
}

# ── STATUS (dashboard) ───────────────────────────────────────────────────
cmd_status() {
  acquire_lock_with_trap
  local now; now="$(date '+%Y-%m-%d %H:%M:%S')"
  hdr "STATUS @ $now"

  # SYSTEM
  echo
  printf '%sSYSTEM%s\n' "$C_BOLD" "$C_RESET"
  printf '  Hostname    : %s\n' "$(hostname)"
  local kernel; kernel=$(uname -r)
  local distro; distro="$(grep -oP '^NAME=\K.*' /etc/os-release 2>/dev/null | tr -d '"')"
  printf '  OS          : %s\n' "$distro"
  printf '  Kernel      : %s\n' "$kernel"
  printf '  Memoria     : %s\n' "$(free -h | awk '/^Mem:/ {print $2" total, "$3" usado, "$7" disp."}')"
  printf '  Disco libre : %s\n' "$(df -h / | tail -1 | awk '{print $4" en "$6}')"
  if command -v nvidia-smi >/dev/null; then
    printf '  GPU         : %s\n' "$(nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total --format=csv,noheader)"
  fi

  # SERVICES
  echo
  printf '%sSERVICIOS%s\n' "$C_BOLD" "$C_RESET"
  local state; state="$(systemctl is-active ollama 2>/dev/null || echo '?')"
  case "$state" in
    active)   printf '  %s●%s Ollama         UP  (systemd)\n'   "$C_GREEN" "$C_RESET" ;;
    *)        printf '  %s○%s Ollama         %s\n' "$C_RED" "$C_RESET" "$state" ;;
  esac

  for c in "$WEBUI_CONTAINER" "$ANYTHING_CONTAINER"; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$c"; then
      printf '  %s●%s %-15s UP  (docker, :%s)\n' "$C_GREEN" "$C_RESET" "$c" "$(_port_of_container "$c")"
    else
      printf '  %s○%s %-15s STOPPED\n' "$C_RED" "$C_RESET" "$c"
    fi
  done

  if [[ "$PROXY_MODE" == "caddy" ]]; then
    local caddy_state; caddy_state="$(systemctl is-active erasmo-caddy 2>/dev/null || echo '?')"
    case "$caddy_state" in
      active) printf '  %s●%s Caddy+HTTPS    UP  (:%s, dashboard en /)\n' "$C_GREEN" "$C_RESET" "$PUBLIC_PORT" ;;
      *)      printf '  %s○%s Caddy+HTTPS    %s\n' "$C_RED" "$C_RESET" "$caddy_state" ;;
    esac
  else
    local nginx_state; nginx_state="$(systemctl is-active nginx 2>/dev/null || echo '?')"
    case "$nginx_state" in
      active) printf '  %s●%s Nginx+auth     UP  (:%s)\n' "$C_GREEN" "$C_RESET" "$NGINX_PORT" ;;
      *)      printf '  %s○%s Nginx+auth     %s\n' "$C_RED" "$C_RESET" "$nginx_state" ;;
    esac
  fi

  if [[ -d "${HOME}/vllm-env" ]]; then
    printf '  %s●%s vLLM           %s\n' "$C_YELLOW" "$C_RESET" "(venv listo, arrancar manualmente)"
  else
    printf '  %s○%s vLLM           no instalado\n' "$C_DIM" "$C_RESET"
  fi

  # MODELS
  echo
  printf '%sMODELOS%s\n' "$C_BOLD" "$C_RESET"
  if command -v ollama >/dev/null && systemctl is-active ollama &>/dev/null; then
    printf '  %s\n' "$(ollama list 2>/dev/null | awk 'BEGIN{print "  NAME                       SIZE      MODIFIED"} NR>1{printf "  %-26s %-9s %s\n",$1,$2,$3}')"
  else
    echo "  (Ollama no responde)"
  fi

  # HEALTHCHECK PUERTOS
  echo
  printf '%sHEALTHCHECK%s\n' "$C_BOLD" "$C_RESET"
  local probe_port
  probe_port="$([[ "$PROXY_MODE" == "caddy" ]] && echo "$PUBLIC_PORT" || echo "$NGINX_PORT")"
  for port in 11434 "$WEBUI_PORT" "$ANYTHING_PORT" "$probe_port"; do
    local result; result=$(check_port "$port")
    local code="${result% *}"; local ms="${result#* }"
    local icon
    case "$code" in
      200|401) icon="$C_GREEN●" ;;
      000)     icon="$C_RED○" ;;
      3*)      icon="$C_YELLOW●" ;;
      *)       icon="$C_YELLOW●" ;;
    esac
    printf '  %s%s :%-5s  HTTP %s (%ss)\n' "$icon" "$C_RESET" "$port" "$code" "$ms"
  done

  # UFW
  echo
  printf '%sFIREWALL%s\n' "$C_BOLD" "$C_RESET"
  if command -v ufw >/dev/null; then
    sudo ufw status 2>/dev/null | head -10 | sed 's/^/  /'
  fi

  echo
  printf '%sLog:%s %s\n' "$C_DIM" "$C_RESET" "$LOG_FILE"
}

_port_of_container() {
  local c=$1
  docker inspect --format '{{json (index (index .NetworkSettings.Ports "8080/tcp") 0) "HostPort" }}' "$c" 2>/dev/null \
    | tr -d '"' \
    || docker inspect --format '{{json (index (index .NetworkSettings.Ports "3001/tcp") 0) "HostPort" }}' "$c" 2>/dev/null | tr -d '"' \
    || echo "?"
}

# ── INSTALL (orquestador) ────────────────────────────────────────────────
cmd_install() {
  acquire_lock_with_trap
  preflight
  install_packages
  setup_user
  install_ollama

  if [[ "${ERASMO_AI_SKIP_MODELS:-0}" != "1" ]]; then
    # ERASMO_AI_MODELS llega como STRING (env vars no son arrays bash).
    # Lo spliteamos por whitespace para soportar "qwen3 deepseek".
    local models
    if [[ -n "${ERASMO_AI_MODELS:-}" ]]; then
      # read -ra SÍ splitea por whitespace — es lo que queremos.
      # Filtramos elementos vacíos (caso ERASMO_AI_MODELS=" " → [""] que rompe ollama pull).
      read -ra models <<<"$ERASMO_AI_MODELS"
      local _filtered=()
      local _e
      for _e in "${models[@]}"; do
        [[ -n "$_e" ]] && _filtered+=("$_e")
      done
      models=("${_filtered[@]}")
      unset _filtered _e
    else
      models=("${DEFAULT_MODELS[@]}")
    fi
    [[ ${#models[@]} -gt 0 ]] || die "Lista de modelos vacía"
    pull_models "${models[@]}"
  fi

  if [[ "${ERASMO_AI_SKIP_DOCKER:-0}" != "1" ]]; then
    install_open_webui
    install_anythingllm
  fi

  install_jan
  install_vllm

  if [[ "${ERASMO_AI_SKIP_PROXY:-0}" != "1" && "${ERASMO_AI_SKIP_NGINX:-0}" != "1" ]]; then
    ensure_htpasswd
    configure_proxy
    configure_firewall
  fi

  hdr "INSTALACIÓN COMPLETA"
  echo
  if [[ "$PROXY_MODE" == "caddy" ]]; then
    if [[ -n "$PUBLIC_DOMAIN" ]]; then
      echo "  Dashboard  : https://${PUBLIC_DOMAIN}/  (Let's Encrypt)"
    else
      echo "  Dashboard  : https://localhost:${PUBLIC_PORT}/  (self-signed, aceptar excepción)"
    fi
    echo "  Con auth   : user=erasmo + contraseña que indicaste (o la generada)"
    echo "  Open WebUI : https://.../webui/"
    echo "  AnythingLLM: https://.../rag/"
    echo "  Ollama API : https://.../ollama/"
  else
    echo "  Open WebUI : http://localhost:$WEBUI_PORT  (o http://localhost:$NGINX_PORT/webui vía auth)"
    echo "  AnythingLLM: http://localhost:$ANYTHING_PORT"
    echo "  Ollama API : http://localhost:11434"
  fi
  echo "  Jan.ai     : ~/jan/run-jan.sh"
  echo "  vLLM       : source ~/vllm-env/bin/activate && python -m vllm.entrypoints.openai.api_server --model qwen2.5-7b --port 8000"
  echo
  ok "¡Listo! '$SCRIPT_NAME --status' para ver el dashboard de salud."
}

# ── UNINSTALL ────────────────────────────────────────────────────────────
cmd_uninstall() {
  acquire_lock_with_trap

  hdr "DESINSTALACIÓN (guiada)"
  if ! confirm "¿Seguro que quieres desinstalar el stack? (operación reversible solo reinstalando)" n; then
    warn "Cancelado por el usuario."
    exit 0
  fi

  hdr "Parando proxy + servicios"
  if confirm "¿Parar Caddy (erasmo-caddy) y limpiar config?" y; then
    sudo systemctl disable --now erasmo-caddy 2>/dev/null || true
    sudo rm -f /etc/systemd/system/erasmo-caddy.service
    sudo systemctl daemon-reload
    ok "Caddy detenido y unit retirada"
  fi

  if confirm "¿Borrar dashboard HTML + Caddyfile (~/ai_caddy/)?" n; then
    rm -rf "$CADDY_HOME"
    ok "~/ai_caddy/ eliminado"
  fi

  if confirm "¿Parar Nginx (legacy)?" n; then
    sudo systemctl disable --now nginx 2>/dev/null || true
    sudo rm -f "$NGINX_CONF"
    [[ -f /etc/nginx/nginx.conf.erasmo.bak ]] && sudo cp /etc/nginx/nginx.conf.erasmo.bak /etc/nginx/nginx.conf && ok "nginx.conf restaurado" || true
    ok "Nginx detenido y config retirada"
  fi

  if confirm "¿Parar y eliminar contenedores Docker (open-webui, anythingllm)?" y; then
    docker rm -f "$WEBUI_CONTAINER" "$ANYTHING_CONTAINER" 2>/dev/null || true
    ok "Contenedores eliminados"
  fi

  if confirm "¿Parar Ollama y deshabilitar el servicio?" y; then
    sudo systemctl disable --now ollama 2>/dev/null || true
    ok "Ollama detenido"
  fi

  if confirm "¿Borrar modelos descargados (~20 GB liberados)?" n; then
    if command -v ollama >/dev/null; then
      ollama list | tail -n +2 | awk '{print $1}' | while read -r m; do
        [[ -n "$m" ]] && ollama rm "$m" 2>/dev/null && log "Modelo $m borrado"
      done
    fi
    ok "Modelos eliminados"
  else
    warn "Modelos conservados"
  fi

  if confirm "¿Borrar entorno vLLM (~/vllm-env)?" y; then
    rm -rf "${HOME}/vllm-env"
    ok "vLLM eliminado"
  fi

  if confirm "¿Borrar Jan.ai (~/jan)?" y; then
    rm -rf "${HOME}/jan"
    ok "Jan.ai eliminado"
  fi

  if confirm "¿Borrar datos persistentes de UIs (~/open-webui, ~/anythingllm)?" n; then
    rm -rf "${HOME}/open-webui" "${HOME}/anythingllm"
    ok "Datos eliminados"
  fi

  if confirm "¿Resetear firewall UFW a defaults? (DESTRUCTIVO: borra TODAS las reglas existentes)" n; then
    sudo ufw --force reset
    warn "UFW reseteado a defaults (todas las reglas eliminadas)"
  fi

  if confirm "¿Borrar el archivo htpasswd ($HTPASSWD_FILE)?" n; then
    sudo rm -f "$HTPASSWD_FILE"
    ok "htpasswd eliminado"
  fi

  if confirm "¿Eliminar el usuario del sistema $AI_USER?" n; then
    sudo userdel -r "$AI_USER" 2>/dev/null || true
    ok "Usuario eliminado"
  fi

  hdr "DESINSTALACIÓN COMPLETA"
  echo
  echo "  Los paquetes instalados con pacman NO se han desinstalado."
  echo "  Para limpieza total: sudo pacman -Rns --noconfirm docker docker-compose caddy nginx apache-tools ufw fuse2"
  echo
}

# ── UPDATE MODELS (wrapper) ──────────────────────────────────────────────
cmd_update_models() {
  acquire_lock_with_trap
  wait_ollama
  update_models "$@"
  ok "Actualización finalizada. Log: $LOG_FILE"
}

# ── MENÚ INTERACTIVO ─────────────────────────────────────────────────────
show_menu() {
  clear
  printf '%s%s
   ____  _____ ____   ___  __  __ ___ ___  _   _
  | __ )  ___/ ___| / _ \|  \/  |_ _/ _ \| \ | |
  |  _ \ |_  \___ \| | | | |\/| || | | | |  \| |
  | |_) || | | ___) | |_| | |  | || | |_| | |\  |
  |____/ |_| |____/  \___/|_|  |_|___\___/|_| \_|%s
   AI Stack v%s · WSL2 / BlackArch

' "$C_BOLD$C_MAGENTA" "$VERSION" "$C_RESET"

  printf '  1) %s   Instalar todo%s\n'        "$C_GREEN"   "$C_RESET"
  printf '  2) %s   Estado (dashboard)%s\n'   "$C_CYAN"    "$C_RESET"
  printf '  3) %s   Actualizar modelos%s\n'   "$C_YELLOW"  "$C_RESET"
  printf '  4) %s   Desinstalar%s\n'          "$C_RED"     "$C_RESET"
  printf '  5) %s   Abrir logs%s\n'           "$C_DIM"     "$C_RESET"
  printf '  0) %s   Salir%s\n\n'             "$C_DIM"     "$C_RESET"

  read -rp "Elige opción [0-5]: " choice
  case "$choice" in
    1) cmd_install ;;
    2) cmd_status ;;
    3) cmd_update_models ;;
    4) cmd_uninstall ;;
    5) ${PAGER:-less} "$LOG_FILE" ;;
    0|q|Q) echo "Bye."; exit 0 ;;
    *) warn "Opción inválida"; sleep 1; show_menu ;;
  esac
}

# ── AYUDA ────────────────────────────────────────────────────────────────
usage() {
  cat <<HELP

${C_BOLD}ERASMO AI STACK v${VERSION}${C_RESET}
Gestor interactivo del stack de IA sobre WSL2/BlackArch.

${C_BOLD}USO${C_RESET}
  $SCRIPT_NAME                Menú interactivo
  $SCRIPT_NAME --install      Instalación completa
  $SCRIPT_NAME --status       Dashboard de salud
  $SCRIPT_NAME --update-models
  $SCRIPT_NAME --uninstall    Desinstalación guiada
  $SCRIPT_NAME --help         Esta ayuda

${C_BOLD}VARIABLES DE ENTORNO${C_RESET}
  ERASMO_AI_USER         Usuario dedicado (default: $AI_USER)
  ERASMO_AI_MODELS       Lista de modelos separados por espacio
  ERASMO_AI_PORT         Puerto HTTPS público (default: $PUBLIC_PORT)
  ERASMO_AI_DOMAIN       Dominio público (Let's Encrypt auto si resuelve)
  ERASMO_AI_PROXY        caddy (default) | nginx (legacy)
  ERASMO_AI_USE_NGINX=1  Alias legacy de PROXY=nginx
  ERASMO_AI_NOAUTH=1     Deshabilita basic-auth (solo dev)
  ERASMO_AI_SKIP_DOCKER=1 No levantar contenedores Docker
  ERASMO_AI_SKIP_MODELS=1 No descargar modelos en --install
  ERASMO_AI_SKIP_PROXY=1  No tocar proxy/Caddy ni firewall

${C_BOLD}LOG${C_RESET}
  $LOG_FILE

${C_BOLD}EJEMPLOS${C_RESET}
  # Instalación estándar con Caddy HTTPS + Let's Encrypt (si dominio resuelve)
  ERASMO_AI_DOMAIN=mi-host.ddns.net $SCRIPT_NAME --install

  # Instalación rápida sin auth (solo dev, sin LE)
  ERASMO_AI_NOAUTH=1 $SCRIPT_NAME --install

  # Modo legacy con Nginx HTTP (sin HTTPS, sin dashboard)
  ERASMO_AI_USE_NGINX=1 $SCRIPT_NAME --install

  # Solo actualizar un modelo
  $SCRIPT_NAME --update-models qwen3:7b-q4_K_M

  # Ver estado del dashboard
  $SCRIPT_NAME --status
HELP
}

# ── ENTRYPOINT ───────────────────────────────────────────────────────────
main() {
  mkdir -p "$(dirname "$LOG_FILE")"
  if [[ $# -eq 0 ]]; then
    show_menu
    exit $?
  fi

  case "$1" in
    -i|--install)       shift; cmd_install "$@" ;;
    -u|--uninstall)     shift; cmd_uninstall "$@" ;;
    -s|--status)        cmd_status ;;
    -U|--update-models) shift; cmd_update_models "$@" ;;
    -h|--help|help)     usage; exit 0 ;;
    -v|--version)       echo "ERASMO AI STACK v$VERSION"; exit 0 ;;
    *)
      err "Opción desconocida: $1"
      usage
      exit 1
      ;;
  esac
}

main "$@"
