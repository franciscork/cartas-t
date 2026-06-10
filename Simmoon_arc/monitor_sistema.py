#!/usr/bin/env python3
"""
SIMMOON — Monitor de Sistema
Healthcheck diario: GPU, RAM, disco, servicios, temperatura.

Genera un reporte JSON + resumen en consola.
Ideal para cron diario o monitoreo continuo.

Uso:
    python monitor_sistema.py                    # Reporte en consola
    python monitor_sistema.py --json             # Solo JSON
    python monitor_sistema.py --output reporte.json  # Guardar a archivo
    python monitor_sistema.py --alert            # Solo alertas (exit code != 0 si hay problemas)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Encoding fix for Windows cp1252 ────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Environment Detection ────────────────────────────────────────────────

def _is_wsl() -> bool:
    """Detect if running under WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except FileNotFoundError:
        return False


def _wsl_cmd(cmd: str, timeout: int = 10, as_root: bool = False) -> subprocess.CompletedProcess:
    """Run a command, transparently wrapping for WSL if needed."""
    if _is_wsl():
        # Already in WSL, run directly
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)
    else:
        # Running from Windows - wrap with wsl.exe
        user = "root" if as_root else "docus"
        return subprocess.run(
            ["wsl", "-d", "Ubuntu", "-u", user, "--", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )

# ── Telegram Alert Notifications ──────────────────────────────────────────
# Cooldown: don't send the same alert type more than once every 30 min
_ALERT_COOLDOWN_FILE = SCRIPT_DIR / ".alert_cooldown.json"
_ALERT_COOLDOWN_SECONDS = 1800  # 30 minutes


def _load_alert_cooldowns() -> dict:
    """Load the timestamp of last sent alert per type."""
    try:
        if _ALERT_COOLDOWN_FILE.exists():
            with open(_ALERT_COOLDOWN_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_alert_cooldown(alert_type: str):
    """Save when an alert was last sent."""
    cooldowns = _load_alert_cooldowns()
    cooldowns[alert_type] = time.time()
    try:
        with open(_ALERT_COOLDOWN_FILE, "w") as f:
            json.dump(cooldowns, f)
    except Exception:
        pass


def _can_send_alert(alert_type: str) -> bool:
    """Check if enough time has passed since the last alert of this type."""
    cooldowns = _load_alert_cooldowns()
    last_sent = cooldowns.get(alert_type, 0)
    return (time.time() - last_sent) > _ALERT_COOLDOWN_SECONDS


def _send_alert_telegram(text: str) -> bool:
    """Send an alert notification to Telegram via Agatha's API.
    Uses the same bot token and chat_id as agatha_actas.py
    """
    # Try to load config from agatha_config.json
    config_path = SCRIPT_DIR / "agatha_config.json"
    if not config_path.exists():
        return False

    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
        chat_id = cfg.get("chat_id")
        if not chat_id:
            return False

        # Bot token from env var or from telegram_config.json
        token = os.environ.get("AGATHA_BOT_TOKEN", "")
        if not token:
            tg_cfg_path = SCRIPT_DIR / "telegram_config.json"
            if tg_cfg_path.exists():
                with open(tg_cfg_path, "r") as f:
                    tg_cfg = json.load(f)
                token = tg_cfg.get("telegram_token", "")
            else:
                token = ""

        if not token:
            print("  [WARN] monitor_sistema: No hay token de Telegram configurado. Alerta no enviada.", file=sys.stderr)
            return False

        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }).encode("utf-8")

        req = urllib.request.Request(
            api_url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("ok", False)
    except Exception:
        return False


def _classify_alert_type(alert_text: str) -> str:
    """Classify an alert text into a type for cooldown tracking."""
    if "GPU temp" in alert_text:
        return "gpu_temp"
    if "GPU memory" in alert_text or "memory" in alert_text:
        return "gpu_memory"
    if "GPU no detectada" in alert_text:
        return "gpu_missing"
    if "RAM" in alert_text:
        return "ram"
    if "Disco" in alert_text or "Disk" in alert_text:
        return "disk"
    if "ComfyUI" in alert_text:
        return "comfyui"
    if "Ollama" in alert_text:
        return "ollama"
    if "PostgreSQL" in alert_text or "postgresql" in alert_text:
        return "postgresql"
    return "other"


def notify_alerts(alerts: list, report: dict) -> int:
    """Send alert notifications to Telegram for new alerts.
    Returns the number of notifications sent.
    Uses cooldown to avoid spamming (max 1 per type per 30 min).
    """
    if not alerts:
        return 0

    sent = 0
    gpu = report.get("gpu", {})
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    for alert_text in alerts:
        alert_type = _classify_alert_type(str(alert_text))

        if not _can_send_alert(alert_type):
            continue

        # Build a rich alert message
        msg_lines = [f"🚨 *ALERTA SIMMOON — {now_str}*"]
        msg_lines.append("")
        msg_lines.append(f"{alert_text}")
        msg_lines.append("")

        # Add context
        if gpu.get("available"):
            msg_lines.append(f"🎮 GPU: {gpu.get('temperature_c', '?')}°C · {gpu.get('memory_used_mb', 0)}/{gpu.get('memory_total_mb', 0)}MB")
        ram = report.get("ram", {})
        if ram.get("total_gb"):
            msg_lines.append(f"🧠 RAM: {ram.get('used_percent', 0)}% usado")

        msg_lines.append("")
        msg_lines.append("_Monitor automatico · Agatha Actas_")

        text = "\n".join(msg_lines)
        if _send_alert_telegram(text):
            _save_alert_cooldown(alert_type)
            sent += 1

    return sent


# ── Thresholds for alerts ─────────────────────────────────────────────────
THRESHOLDS = {
    "disk_free_percent": 10,      # Alert below 10% free
    "disk_free_gb": 50,           # Alert below 50 GB free
    "ram_used_percent": 90,       # Alert above 90% RAM used
    "gpu_temp_c": 80,             # Alert above 80°C
    "gpu_mem_used_percent": 90,   # Alert above 90% GPU memory
    "gpu_required": True,          # Alert if no GPU detected
    "comfyui_required": True,     # Alert if ComfyUI down
    "ollama_required": True,      # Alert if Ollama down
    "postgres_required": True,    # Alert if PostgreSQL down
}


# ── GPU Monitoring ────────────────────────────────────────────────────────

def check_gpu(require_gpu: bool = True) -> dict:
    """Check GPU status via nvidia-smi.
    
    Args:
        require_gpu: If False, missing GPU is not treated as an error.
    """
    result = {
        "available": False,
        "name": "",
        "driver_version": "",
        "cuda_version": "",
        "temperature_c": 0,
        "memory_total_mb": 0,
        "memory_used_mb": 0,
        "memory_free_mb": 0,
        "memory_used_percent": 0,
        "utilization_gpu_percent": 0,
        "utilization_memory_percent": 0,
        "fan_speed_percent": 0,
        "power_draw_watts": 0,
        "power_limit_watts": 0,
        "processes": [],
    }

    try:
        proc = _wsl_cmd(
            "nvidia-smi --query-gpu=name,driver_version,temperature.gpu,"
            "memory.total,memory.used,memory.free,"
            "utilization.gpu,utilization.memory,"
            "fan.speed,power.draw,power.limit "
            "--format=csv,noheader,nounits 2>/dev/null",
            timeout=15, as_root=True
        )

        if proc.returncode != 0 or not proc.stdout.strip():
            return result

        parts = [p.strip() for p in proc.stdout.strip().split(",")]
        if len(parts) < 11:
            return result

        result["available"] = True
        result["name"] = parts[0]
        result["driver_version"] = parts[1]
        result["temperature_c"] = int(float(parts[2])) if parts[2] != "[Not Supported]" else 0
        result["memory_total_mb"] = int(float(parts[3]))
        result["memory_used_mb"] = int(float(parts[4]))
        result["memory_free_mb"] = int(float(parts[5]))
        result["utilization_gpu_percent"] = int(float(parts[6])) if parts[6] != "[Not Supported]" else 0
        result["utilization_memory_percent"] = int(float(parts[7])) if parts[7] != "[Not Supported]" else 0
        result["fan_speed_percent"] = int(float(parts[8])) if parts[8] != "[Not Supported]" else 0
        result["power_draw_watts"] = float(parts[9]) if parts[9] != "[Not Supported]" else 0
        result["power_limit_watts"] = float(parts[10]) if parts[10] != "[Not Supported]" else 0

        if result["memory_total_mb"] > 0:
            result["memory_used_percent"] = round(
                result["memory_used_mb"] / result["memory_total_mb"] * 100, 1
            )

        # Get GPU processes
        proc2 = _wsl_cmd(
            "nvidia-smi --query-compute-apps=pid,process_name,used_memory "
            "--format=csv,noheader,nounits 2>/dev/null",
            timeout=10, as_root=True
        )
        if proc2.returncode == 0 and proc2.stdout.strip():
            for line in proc2.stdout.strip().split("\n"):
                proc_parts = [p.strip() for p in line.split(",")]
                if len(proc_parts) >= 3:
                    result["processes"].append({
                        "pid": proc_parts[0],
                        "name": proc_parts[1],
                        "memory_mb": int(float(proc_parts[2])),
                    })

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    return result


# ── System Monitoring ─────────────────────────────────────────────────────

def check_ram() -> dict:
    """Check system RAM usage.

    En WSL, consulta a Windows directamente vía PowerShell para obtener
    la RAM real del host (ej. 32GB), ya que `free` dentro de WSL solo
    reporta la asignación de WSL (~50% de la RAM total).
    """
    result = {
        "total_gb": 0,
        "used_gb": 0,
        "free_gb": 0,
        "available_gb": 0,
        "used_percent": 0,
    }

    # ── En WSL: consultar RAM real desde Windows ──
    # Usamos subprocess.run con lista (sin shell) para evitar que bash
    # interprete los $variables del comando PowerShell.
    if _is_wsl():
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "$os=Get-CimInstance Win32_OperatingSystem; "
                 "$t=[math]::Round($os.TotalVisibleMemorySize/1mb,1); "
                 "$f=[math]::Round($os.FreePhysicalMemory/1mb,1); "
                 "Write-Output \"$t $f\""],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip():
                parts = proc.stdout.strip().split()
                if len(parts) >= 2:
                    total = float(parts[0])
                    free = float(parts[1])
                    if total > 0 and total < 1024:  # sanity check: <1024GB
                        result["total_gb"] = total
                        result["free_gb"] = free
                        result["available_gb"] = free
                        result["used_gb"] = round(total - free, 1)
                        result["used_percent"] = round(
                            result["used_gb"] / total * 100, 1
                        )
                        return result
        except Exception:
            pass

        # Fallback: wmic desde WSL
        try:
            proc = _wsl_cmd(
                'wmic computersystem get TotalPhysicalMemory 2>/dev/null | tail -1',
                timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip():
                total_bytes = int(proc.stdout.strip())
                if total_bytes > 0:
                    result["total_gb"] = round(total_bytes / (1024**3), 1)
        except Exception:
            pass

    # ── Fallback general: usar free (nativo Linux o WSL sin PowerShell) ──
    try:
        proc = _wsl_cmd("free -b | grep Mem", timeout=10)
        if proc.returncode == 0:
            parts = proc.stdout.split()
            if len(parts) >= 7:
                # Solo sobreescribir si no tenemos datos de Windows
                if result["total_gb"] == 0:
                    result["total_gb"] = round(int(parts[1]) / (1024**3), 1)
                result["used_gb"] = round(int(parts[2]) / (1024**3), 1)
                result["free_gb"] = round(int(parts[3]) / (1024**3), 1)
                result["available_gb"] = round(int(parts[6]) / (1024**3), 1)
                if result["total_gb"] > 0:
                    result["used_percent"] = round(
                        result["used_gb"] / result["total_gb"] * 100, 1
                    )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return result


def check_disk() -> dict:
    """Check disk space for key mount points."""
    mounts = ["/home/docus", "/", "/mnt/c"]
    result = {}
    for mount in mounts:
        try:
            proc = _wsl_cmd(f"df -BM {mount} 2>/dev/null | tail -1", timeout=10)
            if proc.returncode == 0 and proc.stdout.strip():
                parts = proc.stdout.split()
                if len(parts) >= 6:
                    total = int(parts[1].replace("M", ""))
                    used = int(parts[2].replace("M", ""))
                    avail = int(parts[3].replace("M", ""))
                    pct = int(parts[4].replace("%", ""))
                    result[mount] = {
                        "total_gb": round(total / 1024, 1),
                        "used_gb": round(used / 1024, 1),
                        "available_gb": round(avail / 1024, 1),
                        "used_percent": pct,
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
    return result


def check_cpu_temp() -> Optional[float]:
    """Check CPU temperature (if available)."""
    try:
        # Try lm-sensors
        proc = _wsl_cmd(
            "sensors 2>/dev/null | grep -E 'Package id|Tctl|temp1' | head -1",
            timeout=10
        )
        if proc.returncode == 0 and proc.stdout.strip():
            match = re.search(r'[\+\-]?(\d+\.?\d*)°C', proc.stdout)
            if match:
                return float(match.group(1))

        # Try /sys/class/thermal
        proc2 = _wsl_cmd(
            "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1",
            timeout=10
        )
        if proc2.returncode == 0 and proc2.stdout.strip():
            temp = int(proc2.stdout.strip()) / 1000.0
            if 0 < temp < 150:
                return temp
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


# ── Service Health ────────────────────────────────────────────────────────

def check_http_service(name: str, url: str, timeout: int = 5) -> dict:
    """Check if an HTTP service is responding."""
    result = {"name": name, "url": url, "healthy": False, "status_code": 0, "latency_ms": 0}
    start = time.time()
    try:
        proc = _wsl_cmd(
            f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout {timeout} {url}",
            timeout=timeout + 5
        )
        result["latency_ms"] = round((time.time() - start) * 1000)
        if proc.returncode == 0:
            code = proc.stdout.strip()
            if code.isdigit():
                result["status_code"] = int(code)
                result["healthy"] = result["status_code"] < 500
    except subprocess.TimeoutExpired:
        result["latency_ms"] = timeout * 1000
    return result


def check_postgresql(pg_user: str = "docus", pg_db: str = "simmoon") -> dict:
    """Check PostgreSQL connectivity.
    
    Args:
        pg_user: PostgreSQL username.
        pg_db: PostgreSQL database name.
    """
    result = {"healthy": False, "version": "", "databases": []}
    try:
        proc = _wsl_cmd(
            f"psql -U {pg_user} -d {pg_db} -t -c \"SELECT version();\" 2>/dev/null | head -1",
            timeout=10
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result["healthy"] = True
            result["version"] = proc.stdout.strip()

            # List databases
            proc2 = _wsl_cmd(
                f"psql -U {pg_user} -t -c \"\\l\" 2>/dev/null | awk '{{print $1}}' | grep -v '^$' | grep -v '^('",
                timeout=10
            )
            if proc2.returncode == 0:
                result["databases"] = [
                    db.strip() for db in proc2.stdout.strip().split("\n") if db.strip()
                ]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return result


def _check_cli_tool(name: str, cmd: str, version_arg: str = "--version") -> dict:
    """Check if a CLI tool is available (binary exists and responds)."""
    result = {"name": name, "healthy": False, "version": "", "type": "cli"}
    try:
        # Use env -i to avoid Windows PATH pollution in WSL
        proc = _wsl_cmd(
            f"env -i HOME=$HOME PATH=/home/docus/.local/bin:/usr/bin:/bin "
            f"{cmd} {version_arg} 2>/dev/null | head -1",
            timeout=5
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result["healthy"] = True
            result["version"] = proc.stdout.strip()
    except Exception:
        pass
    return result


def check_services(pg_user: str = "docus", pg_db: str = "simmoon") -> dict:
    """Check all critical services."""
    services = {}

    # ComfyUI
    services["comfyui"] = check_http_service(
        "ComfyUI", "http://localhost:8188/queue", timeout=5
    )

    # Ollama
    svc = check_http_service("Ollama", "http://localhost:11434/api/tags", timeout=5)
    # Enhance with model info if healthy
    if svc["healthy"]:
        try:
            proc = _wsl_cmd(
                "curl -s http://localhost:11434/api/tags 2>/dev/null | "
                "python3 -c \"import sys,json; d=json.load(sys.stdin); "
                "print(len(d.get('models',[])))\" 2>/dev/null",
                timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip().isdigit():
                svc["model_count"] = int(proc.stdout.strip())
        except subprocess.TimeoutExpired:
            pass
    services["ollama"] = svc

    # PostgreSQL
    services["postgresql"] = check_postgresql(pg_user=pg_user, pg_db=pg_db)

    # OpenHuman (API mode)
    services["openhuman"] = check_http_service(
        "OpenHuman", "http://localhost:7788/health", timeout=5
    )

    return services


# ── Alert Detection ───────────────────────────────────────────────────────

def detect_alerts(report: dict) -> list:
    """Scan report for threshold violations. Returns list of alert strings."""
    alerts = []

    # GPU alerts (only if GPU is expected on this system)
    gpu = report.get("gpu", {})
    if gpu.get("available"):
        if gpu.get("temperature_c", 0) > THRESHOLDS["gpu_temp_c"]:
            alerts.append(f"⚠️  GPU temp: {gpu['temperature_c']}°C (threshold: {THRESHOLDS['gpu_temp_c']}°C)")
        if gpu.get("memory_used_percent", 0) > THRESHOLDS["gpu_mem_used_percent"]:
            alerts.append(f"⚠️  GPU memory: {gpu['memory_used_percent']}% used")
    elif THRESHOLDS.get("gpu_required", True):
        alerts.append("⚠️  GPU no detectada o nvidia-smi no disponible")

    # RAM alerts
    ram = report.get("ram", {})
    if ram.get("used_percent", 0) > THRESHOLDS["ram_used_percent"]:
        alerts.append(f"⚠️  RAM: {ram['used_percent']}% usada ({ram['used_gb']}GB/{ram['total_gb']}GB)")

    # Disk alerts
    for mount, info in report.get("disk", {}).items():
        if info.get("used_percent", 0) > (100 - THRESHOLDS["disk_free_percent"]):
            alerts.append(f"⚠️  Disco {mount}: {info['available_gb']}GB libre ({info['used_percent']}% usado)")
        elif info.get("available_gb", 0) < THRESHOLDS["disk_free_gb"]:
            alerts.append(f"⚠️  Disco {mount}: solo {info['available_gb']:.1f}GB libre")

    # Service alerts
    services = report.get("services", {})
    if THRESHOLDS["comfyui_required"] and not services.get("comfyui", {}).get("healthy"):
        alerts.append("❌ ComfyUI no responde en :8188")
    if THRESHOLDS["ollama_required"] and not services.get("ollama", {}).get("healthy"):
        alerts.append("❌ Ollama no responde en :11434")
    if THRESHOLDS["postgres_required"] and not services.get("postgresql", {}).get("healthy"):
        alerts.append("❌ PostgreSQL no responde")

    return alerts


# ── Report Formatting ─────────────────────────────────────────────────────

def format_report(report: dict) -> str:
    """Format the report as a human-readable string."""
    lines = []
    ts = report.get("timestamp", "")
    lines.append("=" * 65)
    lines.append(f"  SIMMOON — System Health Report")
    lines.append(f"  {ts}")
    lines.append("=" * 65)

    # GPU
    gpu = report.get("gpu", {})
    lines.append(f"\n  🎮 GPU")
    if gpu.get("available"):
        lines.append(f"     Model:       {gpu.get('name', 'Unknown')}")
        lines.append(f"     Driver:      {gpu.get('driver_version', 'Unknown')}")
        lines.append(f"     Temp:        {gpu.get('temperature_c', '?')}°C")
        lines.append(f"     Memory:      {gpu.get('memory_used_mb', 0)}/{gpu.get('memory_total_mb', 0)} MB ({gpu.get('memory_used_percent', 0)}%)")
        lines.append(f"     GPU Util:    {gpu.get('utilization_gpu_percent', 0)}%")
        if gpu.get("fan_speed_percent", 0) > 0:
            lines.append(f"     Fan:         {gpu.get('fan_speed_percent', 0)}%")
        if gpu.get("power_draw_watts", 0) > 0:
            lines.append(f"     Power:       {gpu.get('power_draw_watts', 0):.1f}W / {gpu.get('power_limit_watts', 0):.0f}W")
        if gpu.get("processes"):
            lines.append(f"     Processes:   {len(gpu['processes'])}")
            for p in gpu["processes"][:5]:
                lines.append(f"       - {p['name']} (PID {p['pid']}, {p['memory_mb']}MB)")
    else:
        lines.append(f"     ❌ No GPU detected")

    # RAM
    ram = report.get("ram", {})
    lines.append(f"\n  🧠 RAM")
    lines.append(f"     Total:       {ram.get('total_gb', 0):.1f} GB")
    lines.append(f"     Used:        {ram.get('used_gb', 0):.1f} GB ({ram.get('used_percent', 0)}%)")
    lines.append(f"     Available:   {ram.get('available_gb', 0):.1f} GB")

    # Disk
    lines.append(f"\n  💾 Disk")
    for mount, info in report.get("disk", {}).items():
        icon = "⚠️ " if info.get("available_gb", 0) < 50 else "  "
        lines.append(f"     {icon}{mount}: {info.get('available_gb', 0):.1f} GB free / {info.get('total_gb', 0):.1f} GB total ({info.get('used_percent', 0)}% used)")

    # CPU Temp
    cpu_temp = report.get("cpu_temp_c")
    if cpu_temp is not None:
        lines.append(f"\n  🌡️  CPU Temp: {cpu_temp:.1f}°C")

    # Services
    lines.append(f"\n  🔌 Services")
    for name, svc in report.get("services", {}).items():
        icon = "✅" if svc.get("healthy") else "❌"
        extra = ""
        if name == "ollama" and "model_count" in svc:
            extra = f" ({svc['model_count']} models)"
        elif name == "postgresql" and svc.get("databases"):
            extra = f" (DBs: {', '.join(svc['databases'][:3])})"
        lines.append(f"     {icon} {name:15s} {svc.get('url', '')}{extra}  [{svc.get('latency_ms', '?')}ms]")

    # Alerts
    alerts = report.get("alerts", [])
    if alerts:
        lines.append(f"\n  🚨 ALERTS ({len(alerts)})")
        for alert in alerts:
            lines.append(f"     {alert}")
    else:
        lines.append(f"\n  ✅ No alerts — all systems nominal")

    lines.append(f"\n{'=' * 65}")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────

def collect_report() -> dict:
    """Collect all system metrics into a report dict."""
    # Load config for credentials if available
    pg_user = "docus"
    pg_db = "simmoon"
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
            pg_cfg = cfg.get("postgresql", {})
            pg_user = pg_cfg.get("user", pg_user)
            pg_db = pg_cfg.get("database", pg_db)
        except Exception:
            pass

    report = {
        "timestamp": datetime.now().isoformat(),
        "gpu": check_gpu(require_gpu=THRESHOLDS.get("gpu_required", True)),
        "ram": check_ram(),
        "disk": check_disk(),
        "cpu_temp_c": check_cpu_temp(),
        "services": check_services(pg_user=pg_user, pg_db=pg_db),
    }
    alerts = detect_alerts(report)
    report["alerts"] = alerts
    report["healthy"] = len(alerts) == 0

    # Send Telegram notifications for new alerts (with cooldown)
    if alerts:
        sent = notify_alerts(alerts, report)
        if sent > 0:
            _safe_print(f"  📤 {sent} alerta(s) notificada(s) a Telegram")

    return report


def _safe_print(text: str) -> None:
    """Print text safely, handling encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace unsupported characters with ASCII equivalents
        safe = text.encode('ascii', errors='replace').decode('ascii')
        print(safe)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="SIMMOON — System Health Monitor"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--output", "-o", type=str, help="Save report to file")
    parser.add_argument("--alert", action="store_true", help="Alert mode: exit 1 if issues found")
    parser.add_argument("--watch", "-w", type=int, default=0, metavar="SECONDS",
                        help="Watch mode: repeat every N seconds")
    args = parser.parse_args()

    if args.watch > 0:
        _safe_print(f"Watching every {args.watch}s... (Ctrl+C to stop)")
        try:
            while True:
                report = collect_report()
                os.system("cls" if os.name == "nt" else "clear")
                _safe_print(format_report(report))
                time.sleep(args.watch)
        except KeyboardInterrupt:
            _safe_print("\nStopped.")
        return

    report = collect_report()

    if args.json:
        _safe_print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _safe_print(format_report(report))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        _safe_print(f"\nReport saved to: {args.output}")

    if args.alert:
        sys.exit(0 if report["healthy"] else 1)


if __name__ == "__main__":
    main()
