#!/usr/bin/env bash
# =============================================================================
# restore_postgres.sh — Restaura un backup de PostgreSQL para SIMMOON
#
# Uso: bash restore_postgres.sh <archivo_backup.sql.gz>
# Ej:  bash restore_postgres.sh ~/backups/postgres/daily/simmoon_2026-06-07_030000.sql.gz
#
# ⚠️  ATENCIÓN: Esto SOBRESCRIBE la base de datos actual.
# =============================================================================

set -euo pipefail

DB_NAME="simmoon"
DB_USER="docus"
DB_HOST="localhost"
DB_PORT="5432"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── VALIDACIONES ───────────────────────────────────────────────────────────
if [ $# -ne 1 ]; then
    echo "Uso: bash restore_postgres.sh <archivo_backup.sql.gz>"
    echo ""
    echo "Backups disponibles:"
    find ~/backups/postgres -name "*.sql.gz" -type f 2>/dev/null | sort | tail -20
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}[ERROR] Archivo no encontrado: $BACKUP_FILE${NC}"
    exit 1
fi

# ── CONFIRMACIÓN ───────────────────────────────────────────────────────────
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  ⚠️  RESTAURAR BASE DE DATOS — OPERACIÓN DESTRUCTIVA        ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Base de datos : $DB_NAME"
echo "  Backup        : $(basename "$BACKUP_FILE")"
echo "  Tamaño        : $(du -h "$BACKUP_FILE" | cut -f1)"
echo "  Fecha backup  : $(stat -c '%y' "$BACKUP_FILE" 2>/dev/null || echo 'desconocida')"
echo ""
echo -e "${RED}  ⚠️  Se SOBRESCRIBIRÁ la base de datos '$DB_NAME' actual.${NC}"
echo ""
read -rp "  ¿Continuar? (escribe 'SI' en mayúsculas): " confirm

if [ "$confirm" != "SI" ]; then
    echo "  Cancelado."
    exit 0
fi

# ── RESTAURAR ──────────────────────────────────────────────────────────────
echo ""
echo "[1/3] Verificando conexión..."

if ! psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -p "$DB_PORT" -c "SELECT 1;" &>/dev/null; then
    echo -e "${RED}[ERROR] No se pudo conectar a $DB_NAME${NC}"
    exit 1
fi

echo "  ✅ Conexión OK"

echo ""
echo "[2/3] Cerrando conexiones activas..."

psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -p "$DB_PORT" -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '$DB_NAME'
      AND pid <> pg_backend_pid();
" &>/dev/null

echo "  ✅ Conexiones cerradas"

echo ""
echo "[3/3] Restaurando desde $BACKUP_FILE..."

START_TIME=$(date +%s)

# Para backups en formato custom (--format=custom de pg_dump)
if pg_restore -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" \
    --clean --if-exists \
    --no-owner --no-acl \
    --dbname="$DB_NAME" \
    "$BACKUP_FILE" 2>&1; then
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ RESTAURACIÓN COMPLETADA                                  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo "  ⏱️  Tiempo: ${DURATION}s"
    echo "  📋 Verificar: psql -U $DB_USER -d $DB_NAME -c '\\\\dt'"
else
    echo -e "${RED}  ❌ ERROR: pg_restore falló${NC}"
    exit 1
fi
