#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
connect_agents_to_memory.py — Conecta Hermes y OpenHuman al sistema de memoria compartida 🤖

Este script permite que Hermes y OpenHuman interactúen con el sistema de memoria
compartida de SIMMOON, sincronizando contexto entre todos los agentes.

Uso:
    python connect_agents_to_memory.py --sync-hermes      # Solo Hermes
    python connect_agents_to_memory.py --sync-openhuman   # Solo OpenHuman
    python connect_agents_to_memory.py --sync-all         # Ambos (default)
    python connect_agents_to_memory.py --status           # Ver estado de agentes
    python connect_agents_to_memory.py --daemon           # Modo demonio (sync continuo)
"""

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Configuration ──────────────────────────────────────────────────────────
HERMES_API = "http://localhost:9119"
OPENHUMAN_API = "http://localhost:7788"
DEFAULT_INTERVAL = 300  # 5 minutes in daemon mode


# ── Agent Memory Import ────────────────────────────────────────────────────
try:
    from agent_memory import AgentMemory, get_db_conn
    _MEMORY_OK = True
except ImportError:
    _MEMORY_OK = False
    print("[WARN] agent_memory.py no disponible")


# ── Hermes Integration ─────────────────────────────────────────────────────
def check_hermes() -> Dict[str, Any]:
    """Check if Hermes Gateway is running."""
    try:
        req = urllib.request.Request(f"{HERMES_API}/", method="GET")
        resp = urllib.request.urlopen(req, timeout=3)
        content_type = resp.headers.get('Content-Type', '')
        # Hermes dashboard returns HTML, check for session token in response
        if resp.status == 200:
            content = resp.read(500).decode('utf-8', errors='ignore')
            if 'HERMES_SESSION_TOKEN' in content or '<html' in content.lower():
                return {"status": "running", "url": HERMES_API, "type": "dashboard"}
            return {"status": "running", "url": HERMES_API}
    except Exception:
        pass
    
    return {"status": "not_running", "url": HERMES_API}


def get_hermes_context() -> Optional[str]:
    """Get current context/state from Hermes if available.
    
    Note: Hermes is primarily a CLI tool. We try to get state via HTTP.
    """
    # Try to get session info from Hermes gateway
    try:
        req = urllib.request.Request(f"{HERMES_API}/api/status", method="GET")
        resp = urllib.request.urlopen(req, timeout=5)
        if resp.status == 200:
            data = json.loads(resp.read().decode("utf-8"))
            return json.dumps(data)
    except Exception:
        pass
    
    # If Hermes gateway doesn't expose status, return generic info
    return json.dumps({
        "agent": "hermes",
        "gateway": HERMES_API,
        "note": "Hermes Gateway accessible"
    })


def sync_hermes_to_memory(do_sync_openhuman: bool = False) -> bool:
    """Sync Hermes state to shared memory.
    
    Args:
        do_sync_openhuman: If True, also sync to OpenHuman via agent_memory
    """
    if not _MEMORY_OK:
        return False
    
    try:
        hermes_memory = AgentMemory('hermes', project='SIMMOON')
        
        # Check if Hermes is running
        status = check_hermes()
        
        # Save status
        hermes_memory.save_context(
            'agent_status',
            f"Hermes Gateway: {status['status']}",
            tags=['status', 'hermes', 'system'],
            importance=4,
            content_json=status
        )
        
        # Try to get and store context
        context = get_hermes_context()
        if context:
            try:
                context_data = json.loads(context) if isinstance(context, str) and context.startswith('{') else {"raw": context}
            except (json.JSONDecodeError, TypeError):
                context_data = {"raw": str(context) if context else "empty"}
            
            hermes_memory.save_context(
                'last_known_state',
                f"Hermes state at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                tags=['context', 'hermes', 'sync'],
                importance=3,
                content_json=context_data
            )
        
        # Optionally sync to OpenHuman via the shared function
        if do_sync_openhuman:
            try:
                from agent_memory import sync_hermes_to_openhuman
                sync_hermes_to_openhuman()
            except Exception:
                pass
        
        return True
    except Exception as e:
        print(f"[ERROR] Sync Hermes to memory failed: {e}")
        return False


# ── OpenHuman Integration ─────────────────────────────────────────────────
def check_openhuman() -> Dict[str, Any]:
    """Check if OpenHuman API is running."""
    try:
        req = urllib.request.Request(f"{OPENHUMAN_API}/health", method="GET")
        resp = urllib.request.urlopen(req, timeout=3)
        if resp.status == 200:
            data = json.loads(resp.read().decode("utf-8"))
            return {"status": "running", "url": OPENHUMAN_API, "info": data}
    except Exception:
        pass
    
    return {"status": "not_running", "url": OPENHUMAN_API}


def get_openhuman_context() -> Optional[str]:
    """Get current context/state from OpenHuman.
    
    Uses /health endpoint for efficiency - no chat call needed.
    """
    try:
        req = urllib.request.Request(f"{OPENHUMAN_API}/health", method="GET")
        resp = urllib.request.urlopen(req, timeout=5)
        if resp.status == 200:
            health_data = json.loads(resp.read().decode("utf-8"))
            return json.dumps({
                "agent": "openhuman",
                "api": OPENHUMAN_API,
                "responsive": True,
                "health": health_data
            })
    except Exception as e:
        return json.dumps({
            "agent": "openhuman",
            "api": OPENHUMAN_API,
            "responsive": False,
            "error": str(e)[:100]
        })
    
    return None


def sync_openhuman_to_memory(do_sync_hermes: bool = False) -> bool:
    """Sync OpenHuman state to shared memory.
    
    Args:
        do_sync_hermes: If True, also sync to Hermes via agent_memory
    """
    if not _MEMORY_OK:
        return False
    
    try:
        openhuman_memory = AgentMemory('openhuman', project='SIMMOON')
        
        # Check if OpenHuman is running
        status = check_openhuman()
        
        # Save status
        openhuman_memory.save_context(
            'agent_status',
            f"OpenHuman API: {status['status']}",
            tags=['status', 'openhuman', 'system'],
            importance=4,
            content_json=status
        )
        
        # Get health data for detailed status
        try:
            req = urllib.request.Request(f"{OPENHUMAN_API}/health", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            if resp.status == 200:
                health_data = json.loads(resp.read().decode("utf-8"))
                openhuman_memory.save_context(
                    'health_status',
                    f"OpenHuman healthy at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    tags=['health', 'openhuman', 'sync'],
                    importance=3,
                    content_json=health_data
                )
        except Exception:
            pass
        
        # Optionally sync to Hermes via the shared function
        if do_sync_hermes:
            try:
                from agent_memory import sync_openhuman_to_hermes
                sync_openhuman_to_hermes()
            except Exception:
                pass
        
        return True
    except Exception as e:
        print(f"[ERROR] Sync OpenHuman to memory failed: {e}")
        return False


# ── Sync Synthesis to All Agents ─────────────────────────────────────────
def sync_synthesis_to_agents() -> bool:
    """Distribute Agatha's latest synthesis to Hermes and OpenHuman memory.
    
    Reads the latest daily summary from PostgreSQL (daily_summaries table)
    and saves it as a fact in both Hermes' and OpenHuman's agent_memory,
    so all agents can see the current state of the system.
    
    Returns True if at least one agent received the synthesis.
    """
    if not _MEMORY_OK:
        return False
    
    try:
        # Get latest synthesis from agatha_actas
        from agatha_actas import get_recent_summaries
        summaries = get_recent_summaries(days=2)
        
        if not summaries:
            print("    ⚠️  No hay síntesis de Agatha para distribuir")
            return False
        
        latest = summaries[0]
        
        # Convert date to string if needed (PostgreSQL returns date objects)
        synthesis_date = str(latest['date']) if not isinstance(latest['date'], str) else latest['date']
        
        # Build content_json once (avoid duplicate json-serialization errors)
        synthesis_json = {
            'date': synthesis_date,
            'title': latest['title'],
            'source': 'Agatha Actas',
            'assets_total': latest['assets_total'],
            'services_active': latest['services_active'],
            'services_total': latest['services_total'],
            'agents_active': latest['agents_active'],
            'agents_total': latest['agents_total'],
        }
        
        # Build a compact synthesis text for agent memory
        synthesis_text = (
            f"📊 {latest['title']}\n"
            f"   Assets: {latest['assets_total']} | "
            f"Servicios: {latest['services_active']}/{latest['services_total']} | "
            f"Agentes: {latest['agents_active']}/{latest['agents_total']}"
        )
        
        synced_count = 0
        
        # Push to Hermes memory (existing pattern: each agent has its own memory)
        try:
            hermes_memory = AgentMemory('hermes', project='SIMMOON')
            if hermes_memory.save_fact(
                key_name='agatha_synthesis',
                content=synthesis_text,
                importance=4,
                tags=['synthesis', 'agatha', 'shared', 'system'],
                related_agent='agatha',
                content_json=synthesis_json
            ):
                synced_count += 1
                print(f"    ✅ Síntesis de Agatha → Hermes")
        except Exception as e:
            print(f"    ⚠️  No se pudo sync a Hermes: {e}")
        
        # Push to OpenHuman memory
        try:
            openhuman_memory = AgentMemory('openhuman', project='SIMMOON')
            if openhuman_memory.save_fact(
                key_name='agatha_synthesis',
                content=synthesis_text,
                importance=4,
                tags=['synthesis', 'agatha', 'shared', 'system'],
                related_agent='agatha',
                content_json=synthesis_json
            ):
                synced_count += 1
                print(f"    ✅ Síntesis de Agatha → OpenHuman")
        except Exception as e:
            print(f"    ⚠️  No se pudo sync a OpenHuman: {e}")
        
        # Agents can discover cross-agent synthesis via:
        #   get_shared_context('SIMMOON') or
        #   AgentMemory('hermes').get('agatha_synthesis')
        
        return synced_count > 0
    except Exception as e:
        print(f"    ⚠️  Sync synthesis failed: {e}")
        return False


# ── Combined Sync ──────────────────────────────────────────────────────────
def sync_all_agents_to_memory() -> Dict[str, bool]:
    """Sync all agents (Hermes, OpenHuman, Buffy) to shared memory."""
    results = {}
    
    print("  🔄 Sincronizando Hermes...")
    results['hermes'] = sync_hermes_to_memory()
    
    print("  🔄 Sincronizando OpenHuman...")
    results['openhuman'] = sync_openhuman_to_memory()
    
    print("  🔄 Sincronizando Agatha (sistema)...")
    try:
        from agatha_actas import sync_memory_to_agents
        results['agatha'] = sync_memory_to_agents()
    except Exception as e:
        print(f"    ⚠️  Agatha sync failed: {e}")
        results['agatha'] = False
    
    # Distribuir la síntesis de Agatha a todos los agentes
    print("  🔄 Distribuyendo síntesis de Agatha a Hermes y OpenHuman...")
    results['synthesis'] = sync_synthesis_to_agents()
    
    return results


def print_status():
    """Print current status of all agents."""
    print("\n  🤖 Estado de Agentes Conectados")
    print("  " + "=" * 50)
    
    # Hermes
    hermes_status = check_hermes()
    icon = "✅" if hermes_status['status'] == 'running' else "❌"
    print(f"  {icon} Hermes Gateway ({HERMES_API})")
    print(f"     Estado: {hermes_status['status']}")
    
    # OpenHuman
    openhuman_status = check_openhuman()
    icon = "✅" if openhuman_status['status'] == 'running' else "❌"
    print(f"  {icon} OpenHuman API ({OPENHUMAN_API})")
    print(f"     Estado: {openhuman_status['status']}")
    
    # Memory system
    if _MEMORY_OK:
        print(f"  ✅ Sistema de memoria compartida (PostgreSQL)")
    else:
        print(f"  ❌ Sistema de memoria compartida (no disponible)")
    
    print()


def daemon_mode(interval: int = DEFAULT_INTERVAL):
    """Run in daemon mode, syncing agents periodically."""
    print(f"\n  🤖 Connect Agents — Modo Demonio")
    print(f"  ⏱️  Sync cada {interval // 60} minutos")
    print(f"  {'=' * 50}")
    print(f"  Presiona Ctrl+C para detener.\n")
    
    sync_all_agents_to_memory()
    print_status()
    
    while True:
        next_time = time.time() + interval
        next_str = datetime.fromtimestamp(next_time).strftime("%H:%M:%S")
        print(f"  ⏳ Próximo sync a las {next_str}...")
        
        try:
            while time.time() < next_time:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n  🛑 Demonio detenido.\n")
            break
        
        print("\n  🔄 Sincronizando agentes...")
        results = sync_all_agents_to_memory()
        for agent, success in results.items():
            print(f"     {agent}: {'✅' if success else '⚠️'}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Conectar Hermes y OpenHuman al sistema de memoria compartida"
    )
    parser.add_argument('--sync-hermes', action='store_true', help='Solo sincronizar Hermes')
    parser.add_argument('--sync-openhuman', action='store_true', help='Solo sincronizar OpenHuman')
    parser.add_argument('--sync-all', action='store_true', help='Sincronizar todos los agentes')
    parser.add_argument('--status', action='store_true', help='Ver estado de agentes')
    parser.add_argument('--daemon', action='store_true', help='Modo demonio (sync continuo)')
    parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL,
                        help=f'Intervalo en segundos (default: {DEFAULT_INTERVAL})')
    
    args = parser.parse_args()
    
    # Default: show status
    if args.status:
        print_status()
        return
    
    if args.sync_hermes:
        print("  🔄 Sincronizando Hermes...")
        result = sync_hermes_to_memory()
        print(f"  {'✅' if result else '❌'} Hermes sincronizado")
        return
    
    if args.sync_openhuman:
        print("  🔄 Sincronizando OpenHuman...")
        result = sync_openhuman_to_memory()
        print(f"  {'✅' if result else '❌'} OpenHuman sincronizado")
        return
    
    if args.sync_all or args.daemon:
        if args.daemon:
            daemon_mode(args.interval)
        else:
            print("  🔄 Sincronizando todos los agentes...")
            results = sync_all_agents_to_memory()
            for agent, success in results.items():
                print(f"     {agent}: {'✅' if success else '⚠️'}")
        return
    
    # Default: show status
    print_status()
    print("  Uso: --sync-hermes | --sync-openhuman | --sync-all | --status | --daemon")


if __name__ == "__main__":
    main()