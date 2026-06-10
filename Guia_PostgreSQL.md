# 🗄️ Guía Rápida - PostgreSQL

## ¿Qué es?
Base de datos relacional open-source. Backend principal para Simmoon (datos de juego, assets, votos). Corre en WSL2 con acceso desde Windows.

## Puertos y Conexión
| Recurso | Valor |
|----------|-------|
| Puerto | `5432` |
| Host | `localhost` |
| Usuario | `docus` |
| Base de datos | `simmoon` |

## Iniciar / Detener
```bash
# Desde ias (recomendado)
ias start postgres
ias stop postgres

# Manual
sudo systemctl start postgresql
sudo systemctl stop postgresql

# Verificar estado
pg_isready -h localhost -p 5432
```

## Conexión
```bash
# Cliente psql
psql -h localhost -U docus -d simmoon

# Desde Python
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="simmoon",
    user="docus"
)

# Desde Windows (DBeaver, PGAdmin, etc.)
# Host: localhost, Puerto: 5432, User: docus
```

## Esquema Simmoon
```sql
-- Tablas principales (schema.sql en ~/Simmoon_arc/)
- assets       -- Imágenes generadas
- votes        -- Votos de usuarios
- players      -- Jugadores del juego
- game_state   -- Estado del juego
```

## Comandos Útiles
```bash
# Listar bases de datos
psql -l

# Conectar
psql -U docus -d simmoon

# Backup
pg_dump simmoon > simmoon_backup.sql

# Restaurar
psql simmoon < simmoon_backup.sql

# Ver tablas
psql -U docus -d simmoon -c "\dt"
```

## Poblar Base de Datos
```bash
cd ~/Simmoon_arc
python3 populate_db.py
```

## Ubicaciones
- **Datos**: `/var/lib/postgresql/`
- **Config**: `/etc/postgresql/*/main/postgresql.conf`
- **Logs**: `/var/log/postgresql/`

## Solución de Problemas
- **No arranca**: `sudo systemctl start postgresql`
- **Conexión rechazada**: Verificar `pg_hba.conf` y puerto
- **pg_isready no existe**: `sudo apt install postgresql-client`
