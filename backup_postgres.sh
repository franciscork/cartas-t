#!/usr/bin/env bash
# =============================================================================
# backup_postgres.sh — Backup automático de PostgreSQL para SIMMOON
#
# Hace pg_dump de la BD 'simmoon', comprime, rota backups, y genera logs.
# 
# Uso manual:   bash backup_postgres.sh
# Uso cron:     0 3 * * * /home/docus/backup_postgres.sh
#
# Política de rotación:
#   - Diarios: últimos 7
#   - Semanales: últimas 4 (domingo)
#   - Mensuales: últimos 3 (día 1)
# =============================================================================

set -euo pipefail

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────
DB_NAME="simmoon"
DB_USER="docus"
DB_HOST="localhost"
DB_PORT="5432"

BACKUP_DIR="$HOME/backups/postgres"
LOG_DIR="$BACKUP_DIR/logs"
RETENTION_DAILY=7
RETENTION_WEEKLY=4
RETENTION_MONTHLY=3

TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
DATE_ONLY=$(date +"%Y-%m-%d")
DAY_OF_WEEK=$(date +"%u")   # 1=Lunes ... 7=Domingo
DAY_OF_MONTH=$(date +"%d")

BACKUP_FILE="$BACKUP_DIR/daily/simmoon_${TIMESTAMP}.sql.gz"
LOG_FILE="$LOG_DIR/backup_${DATE_ONLY}.log"
WEEKLY_FILE="$BACKUP_DIR/weekly/simmoon_week_$(date +%Y-W%V).sql.gz"
MONTHLY_FILE="$BACKUP_DIR/monthly/simmoon_month_$(date +%Y-%m).sql.gz"

# ── INICIALIZACIÓN ─────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/monthly" "$LOG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "══════════════════════════════════════════════════════════════"
echo "  BACKUP PostgreSQL — $(date '+%Y-%m-%d %H:%M:%S')"
echo "══════════════════════════════════════════════════════════════"
echo "  Base de datos : $DB_NAME"
echo "  Usuario       : $DB_USER"
echo "  Destino       : $BACKUP_DIR"
echo "──────────────────────────────────────────────────────────────"

# ── VERIFICACIONES ─────────────────────────────────────────────────────────
if ! command -v pg_dump &>/dev/null; then
    echo "[ERROR] pg_dump no encontrado. Instalar: sudo apt-get install postgresql-client"
    exit 1
fi

# Verificar conexión a la BD
if ! psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -p "$DB_PORT" -c "SELECT 1;" &>/dev/null; then
    echo "[ERROR] No se pudo conectar a $DB_NAME como $DB_USER"
    exit 1
fi

# ── BACKUP ─────────────────────────────────────────────────────────────────
echo ""
echo "[1/3] Ejecutando pg_dump..."

START_TIME=$(date +%s)

if pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" \
    --no-owner --no-acl \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_FILE" \
    "$DB_NAME" 2>&1; then
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo "  ✅ Backup exitoso"
    echo "  📁 Archivo : $(basename "$BACKUP_FILE")"
    echo "  📏 Tamaño  : $SIZE"
    echo "  ⏱️  Tiempo  : ${DURATION}s"
else
    echo "  ❌ ERROR: pg_dump falló"
    exit 1
fi

# ── COPIAS SEMANALES Y MENSUALES ───────────────────────────────────────────
echo ""
echo "[2/3] Gestionando copias semanales/mensuales..."

# Semanal: guardar solo el domingo (day 7)
if [ "$DAY_OF_WEEK" = "7" ]; then
    cp "$BACKUP_FILE" "$WEEKLY_FILE"
    echo "  📅 Copia semanal guardada: $(basename "$WEEKLY_FILE")"
else
    echo "  ⏭️  Hoy no es domingo, se omite copia semanal"
fi

# Mensual: guardar solo el día 1
if [ "$DAY_OF_MONTH" = "01" ]; then
    cp "$BACKUP_FILE" "$MONTHLY_FILE"
    echo "  📅 Copia mensual guardada: $(basename "$MONTHLY_FILE")"
else
    echo "  ⏭️  Hoy no es día 1, se omite copia mensual"
fi

# ── ROTACIÓN ───────────────────────────────────────────────────────────────
echo ""
echo "[3/3] Rotando backups antiguos..."

# Diarios: mantener solo los últimos N
rotate() {
    local dir="$1"
    local keep="$2"
    local label="$3"
    
    local count=$(find "$dir" -name "*.sql.gz" -type f 2>/dev/null | wc -l)
    local remove=$((count - keep))
    
    if [ "$remove" -gt 0 ]; then
        echo "  🗑️  $label: eliminando $remove de $count backups"
        find "$dir" -name "*.sql.gz" -type f | sort | head -n "$remove" | while read -r f; do
            echo "     ─ $(basename "$f")"
            rm -f "$f"
        done
    else
        echo "  ✅ $label: $count backups (límite: $keep) — sin rotación necesaria"
    fi
}

rotate "$BACKUP_DIR/daily" "$RETENTION_DAILY" "Diarios"
rotate "$BACKUP_DIR/weekly" "$RETENTION_WEEKLY" "Semanales"
rotate "$BACKUP_DIR/monthly" "$RETENTION_MONTHLY" "Mensuales"

# ── RESUMEN ────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  RESUMEN DE BACKUPS"
echo "══════════════════════════════════════════════════════════════"
echo "  Diarios   : $(find "$BACKUP_DIR/daily" -name '*.sql.gz' | wc -l) archivos"
echo "  Semanales : $(find "$BACKUP_DIR/weekly" -name '*.sql.gz' | wc -l) archivos"
echo "  Mensuales : $(find "$BACKUP_DIR/monthly" -name '*.sql.gz' | wc -l) archivos"
echo ""
echo "  💾 Espacio usado : $(du -sh "$BACKUP_DIR" | cut -f1)"
echo "  📋 Log           : $LOG_FILE"
echo ""
echo "  ✅ Backup completado — $(date '+%Y-%m-%d %H:%M:%S')"
echo "══════════════════════════════════════════════════════════════"
