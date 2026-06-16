#!/usr/bin/env bash
# ============================================================================
#  ERASMO AI STACK * One-line bootstrap
#  Detecta ansible-playbook y dispatcha playbook o bash directo.
#
#  USO:
#    curl -fsSL https://YOUR-HOST/bootstrap.sh | bash
#    curl -fsSL ... | bash -s -- --domain erasmo.duckdns.org
#    ERASMO_AI_DOMAIN=foo curl -fsSL ... | bash
#
#  COMPORTAMIENTO:
#    1. Crea ~/.erasmo-ai-stack/ (workdir)
#    2. Descarga ai_stack_installer/erasmo-ai-stack.sh desde el repo
#    3. Si hay ansible-playbook instalado:
#         * descarga tambien ai_stack_installer/ansible/deploy.yml
#         * ejecuta ansible-playbook con --extra-vars desde las env vars del shell
#    4. Si no:
#         * ejecuta el bash script directamente con las env vars
#
#  REPO por defecto: raw.githubusercontent.com/erasmo/ai-stack-installer/main
#  Override con --repo=URL o ERASMO_AI_REPO.
# ============================================================================
set -Eeuo pipefail
IFS=$'\n\t'

# --- Prerrequisitos -------------------------------------------------------
command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 \
  || { printf '\nERROR: necesitas "curl" o "wget" instalado.\n  Instalalo con: sudo pacman -S curl wget\n\n' >&2; exit 1; }
command -v bash >/dev/null 2>&1 \
  || { printf '\nERROR: se requiere bash >= 4.0\n\n' >&2; exit 1; }

# --- Constantes -----------------------------------------------------------
readonly REPO_URL_DEFAULT="https://raw.githubusercontent.com/erasmo/ai-stack-installer/main"
readonly TARGET_DIR_NAME="ai_stack_installer"
readonly SCRIPT_NAME="erasmo-ai-stack.sh"
readonly ANSIBLE_DIR_NAME="ansible"
readonly ANSIBLE_PLAYBOOK_NAME="deploy.yml"

REPO_URL="${ERASMO_AI_REPO:-$REPO_URL_DEFAULT}"
WORK_DIR="${ERASMO_AI_WORKDIR:-$HOME/.erasmo-ai-stack}"
FORCE_BASH="${ERASMO_AI_NO_ANSIBLE:-}"
SHA256_EXPECTED=""

# --- show_help (definido ANTES del arg parser para que -h funcione) --------
show_help() {
  cat <<'HELP'
ERASMO AI STACK * One-line bootstrap

USO
  curl -fsSL URL/bootstrap.sh | bash
  curl -fsSL URL/bootstrap.sh | bash -s -- --domain foo.duckdns.org
  ERASMO_AI_DOMAIN=foo curl -fsSL URL/bootstrap.sh | bash

DETECCION
  Si ansible-playbook esta instalado   -> descarga ansible/deploy.yml y lo ejecuta
  Si NO                                  -> ejecuta el bash installer directamente
  Mismo resultado identico.

ARGUMENTOS (se traducen internamente a env vars del bash installer)
  --domain=foo.duckdns.org   ERASMO_AI_DOMAIN    (Let's Encrypt si resuelve)
  --port=8443                ERASMO_AI_PORT      (default 8443)
  --models="qwen3 llama3"    ERASMO_AI_MODELS    (default = 4 modelos)
  --user=aiuser              ERASMO_AI_USER
  --use-nginx                modo legacy Nginx HTTP sin Caddy/dashboard
  --no-auth                  deshabilita htpasswd (solo dev)
  --skip-docker              no levanta contenedores
  --skip-models              no descarga modelos
  --skip-proxy               no toca Caddy/Nginx/firewall
  --repo=URL                 repo remoto (default raw.githubusercontent.com/.../main)
  --workdir=DIR              dir destino (default ~/.erasmo-ai-stack)
  --sha256=HASH              verifica SHA256 del installer descargado
  --no-ansible               fuerza bash aunque haya ansible-playbook
  -h, --help                 esta ayuda

EJEMPLOS
  # Default (HTTPS self-signed, sin auth, prompts interactivos)
  curl -fsSL URL/bootstrap.sh | bash

  # Produccion con Let's Encrypt
  curl -fsSL URL/bootstrap.sh | bash -s -- --domain erasmo.duckdns.org

  # Dev sin auth
  curl -fsSL URL/bootstrap.sh | bash -s -- --no-auth --port 9000

  # Override completo sin prompts
  curl -fsSL URL/bootstrap.sh | bash -s -- \
      --domain erasmo.duckdns.org \
      --models "qwen3:7b-q4_K_M llama3.1:8b" \
      --no-ansible
HELP
  exit 0
}

# --- Args -----------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain=*)        export ERASMO_AI_DOMAIN="${1#*=}" ;;
    --domain)          export ERASMO_AI_DOMAIN="$2"; shift ;;
    --port=*)          export ERASMO_AI_PORT="${1#*=}" ;;
    --port)            export ERASMO_AI_PORT="$2"; shift ;;
    --models=*)        export ERASMO_AI_MODELS="${1#*=}" ;;
    --models)          export ERASMO_AI_MODELS="$2"; shift ;;
    --user=*)          export ERASMO_AI_USER="${1#*=}" ;;
    --user)            export ERASMO_AI_USER="$2"; shift ;;
    --use-nginx)       export ERASMO_AI_USE_NGINX=1 ;;
    --no-auth)         export ERASMO_AI_NOAUTH=1 ;;
    --skip-docker)     export ERASMO_AI_SKIP_DOCKER=1 ;;
    --skip-models)     export ERASMO_AI_SKIP_MODELS=1 ;;
    --skip-proxy)      export ERASMO_AI_SKIP_PROXY=1 ;;
    --repo=*)          REPO_URL="${1#*=}" ;;
    --repo)            REPO_URL="$2"; shift ;;
    --workdir=*)       WORK_DIR="${1#*=}" ;;
    --workdir)         WORK_DIR="$2"; shift ;;
    --sha256=*)        SHA256_EXPECTED="${1#*=}" ;;
    --no-ansible)      FORCE_BASH=1 ;;
    -h|--help)         show_help ;;
    *) printf '%s unknown argument: %s\n' "$0" "$1" >&2; exit 2 ;;
  esac
  shift
done

# --- Banner ---------------------------------------------------------------
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

cat <<BANNER

============================================================
   ERASMO AI STACK * One-line bootstrap
============================================================
  * Workdir:  $WORK_DIR
  * Repo:     $REPO_URL
  * Args:
      domain   = ${ERASMO_AI_DOMAIN:-<vacio -> self-signed>}
      port     = ${ERASMO_AI_PORT:-8443}
      models   = ${ERASMO_AI_MODELS:-<vacio -> defaults>}
      user     = ${ERASMO_AI_USER:-aiuser}
      auth     = $([[ "${ERASMO_AI_NOAUTH:-0}" == "1" ]] && echo disabled || echo enabled)
      nginx?   = $([[ "${ERASMO_AI_USE_NGINX:-0}" == "1" ]] && echo legacy || echo Caddy_HTTPS_dashboard)

BANNER

# --- 1. Descargar ---------------------------------------------------------
echo "[1/3] Downloading installer -> $WORK_DIR/$TARGET_DIR_NAME/$SCRIPT_NAME"
mkdir -p "$TARGET_DIR_NAME"
if ! curl -fsSL "$REPO_URL/$TARGET_DIR_NAME/$SCRIPT_NAME" \
       -o "$TARGET_DIR_NAME/$SCRIPT_NAME"; then
  printf '\n  ERROR: no se pudo descargar el installer desde:\n  %s\n\n' "$REPO_URL/$TARGET_DIR_NAME/$SCRIPT_NAME" >&2
  printf '  * Comprueba tu conexion\n' >&2
  printf '  * Comprueba que la URL/branch sea valida (--repo=URL)\n' >&2
  printf '  * Repo privado? Define ERASMO_AI_REPO con token: https://user:TOKEN@raw.githubusercontent.com/...\n' >&2
  exit 1
fi
chmod +x "$TARGET_DIR_NAME/$SCRIPT_NAME"
echo "      OK Installer descargado"

# --- 1b. SHA256 verification (opcional pero recomendado) -------------------
if [[ -n "$SHA256_EXPECTED" || -n "${ERASMO_AI_SHA256:-}" ]]; then
  local_sha_expected="${SHA256_EXPECTED:-${ERASMO_AI_SHA256}}"
  echo "[1b/3] Verifying SHA256..."
  local_sha_actual="$(sha256sum "$TARGET_DIR_NAME/$SCRIPT_NAME" | awk '{print $1}')"
  if [[ "$local_sha_actual" != "$local_sha_expected" ]]; then
    printf '\n  ERROR: SHA256 mismatch.\n  - Esperado: %s\n  - Obtenido: %s\n' "$local_sha_expected" "$local_sha_actual" >&2
    exit 3
  fi
  echo "      OK SHA256"
fi

# --- 2. Detectar Ansible y dispatchar -------------------------------------
USE_ANSIBLE=0
if [[ -z "$FORCE_BASH" ]] && command -v ansible-playbook >/dev/null; then
  USE_ANSIBLE=1
fi

if [[ "$USE_ANSIBLE" == "1" ]]; then
  # Modo declarativo
  echo "[2/3] ansible-playbook detectado -> modo declarativo"
  mkdir -p "$TARGET_DIR_NAME/$ANSIBLE_DIR_NAME"
  if curl -fsSL "$REPO_URL/$TARGET_DIR_NAME/$ANSIBLE_DIR_NAME/$ANSIBLE_PLAYBOOK_NAME" \
        -o "$TARGET_DIR_NAME/$ANSIBLE_DIR_NAME/$ANSIBLE_PLAYBOOK_NAME"; then
    chmod +r "$TARGET_DIR_NAME/$ANSIBLE_DIR_NAME/$ANSIBLE_PLAYBOOK_NAME"
    echo "      OK Playbook descargado"

    # Mapear env vars -> Ansible --extra-vars (solo las que difieren del default)
    declare -a ex=()
    [[ -n "${ERASMO_AI_DOMAIN:-}" ]]    && ex+=("erasmo_ai_domain=${ERASMO_AI_DOMAIN}")
    [[ -n "${ERASMO_AI_PORT:-}" ]]      && ex+=("erasmo_ai_port=${ERASMO_AI_PORT}")
    [[ -n "${ERASMO_AI_MODELS:-}" ]]    && ex+=("erasmo_ai_models=${ERASMO_AI_MODELS}")
    [[ -n "${ERASMO_AI_USER:-}" ]]      && ex+=("erasmo_ai_user=${ERASMO_AI_USER}")
    [[ "${ERASMO_AI_USE_NGINX:-0}" == "1" ]] && ex+=("erasmo_ai_use_nginx=1")
    [[ "${ERASMO_AI_NOAUTH:-0}" == "1" ]]    && ex+=("erasmo_ai_noauth=1")
    [[ "${ERASMO_AI_SKIP_DOCKER:-0}" == "1" ]] && ex+=("erasmo_ai_skip_docker=1")
    [[ "${ERASMO_AI_SKIP_MODELS:-0}" == "1" ]] && ex+=("erasmo_ai_skip_models=1")
    [[ "${ERASMO_AI_SKIP_PROXY:-0}" == "1" ]]  && ex+=("erasmo_ai_skip_proxy=1")

    if (( ${#ex[@]} > 0 )); then
      ansible-playbook -i "localhost," -c local \
        "$TARGET_DIR_NAME/$ANSIBLE_DIR_NAME/$ANSIBLE_PLAYBOOK_NAME" \
        --extra-vars "${ex[*]}"
    else
      ansible-playbook -i "localhost," -c local \
        "$TARGET_DIR_NAME/$ANSIBLE_DIR_NAME/$ANSIBLE_PLAYBOOK_NAME"
    fi
  else
    echo "      AVISO: no pude descargar el playbook -> fallback a bash directo"
    bash "$TARGET_DIR_NAME/$SCRIPT_NAME" --install
  fi
else
  # Modo bash directo
  if [[ -n "$FORCE_BASH" ]]; then
    echo "[2/3] --no-ansible forzado -> modo bash directo"
  else
    echo "[2/3] Ansible no detectado -> modo bash directo"
  fi
  bash "$TARGET_DIR_NAME/$SCRIPT_NAME" --install
fi

# --- 3. Footer ------------------------------------------------------------
cat <<FOOTER

[3/3] Instalacion (probablemente) completada en $WORK_DIR.

  Comandos utiles:
    bash $WORK_DIR/$TARGET_DIR_NAME/$SCRIPT_NAME --status
    bash $WORK_DIR/$TARGET_DIR_NAME/$SCRIPT_NAME --update-models
    bash $WORK_DIR/$TARGET_DIR_NAME/$SCRIPT_NAME --uninstall

  Dashboard (si instalaste Caddy):
    https://localhost:${ERASMO_AI_PORT:-8443}/
    (self-signed: aceptar excepcion del navegador; Let's Encrypt si usaste --domain)
FOOTER
