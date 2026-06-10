#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_memory.py — Sistema de Memoria Compartida entre Agentes 🤖

Permite que Hermes, OpenHuman, Buffy y otros agentes compartan contexto
y memoria persistente usando PostgreSQL.

Uso:
    from agent_memory import AgentMemory, get_shared_context
    
    # Guardar memoria
    memory = AgentMemory('hermes')
    memory.save_context('current_task', 'Crear síntesis diaria de actividad')
    memory.save_fact('user_preference', 'Prefiere español', importance=4)
    
    # Leer memoria
    context = memory.get_recent_context(days=3)
    facts = memory.get_facts_by_tag('proyecto')
    
    # Compartida entre agentes
    shared = get_shared_context('simmoon', limit=10)
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── PostgreSQL Connection ──────────────────────────────────────────────────
def get_db_conn():
    """Get PostgreSQL connection."""
    try:
        try:
            import psycopg
            return psycopg.connect(host="localhost", port=5432, dbname="simmoon", user="postgres")
        except ImportError:
            import psycopg2
            return psycopg2.connect(host="localhost", port=5432, database="simmoon", user="postgres")
    except Exception as e:
        print(f"[WARN] PostgreSQL no disponible: {e}")
        return None


# ── AgentMemory Class ──────────────────────────────────────────────────────
class AgentMemory:
    """Sistema de memoria para un agente específico."""
    
    # Tipos de memoria válidos
    MEMORY_TYPES = ['context', 'fact', 'preference', 'conversation', 'task', 'result', 'error']
    
    def __init__(self, agent_name: str, session_id: Optional[str] = None, project: str = 'SIMMOON'):
        """Inicializar memoria de agente.
        
        Args:
            agent_name: Nombre del agente ('hermes', 'openhuman', 'buffy', etc.)
            session_id: ID de sesión opcional
            project: Proyecto al que pertenece
        """
        self.agent_name = agent_name
        self.session_id = session_id or f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.project = project
    
    def save(self, key_name: str, content: str, memory_type: str = 'context',
             content_json: Optional[dict] = None, tags: Optional[List[str]] = None,
             importance: int = 3, expires_at: Optional[datetime] = None,
             related_agent: Optional[str] = None) -> bool:
        """Guardar un dato en la memoria del agente.
        
        Args:
            key_name: Identificador único del dato
            content: Contenido en texto plano
            memory_type: Tipo de memoria (context, fact, preference, conversation, task)
            content_json: Contenido estructurado opcional
            tags: Tags para búsqueda
            importance: 1-5, importancia del dato
            expires_at: Fecha de expiración opcional
            related_agent: Agente relacionado
        
        Returns:
            True si se guardó correctamente
        """
        if memory_type not in self.MEMORY_TYPES:
            raise ValueError(f"Tipo de memoria inválido: {memory_type}. Usar uno de: {self.MEMORY_TYPES}")
        
        conn = get_db_conn()
        if not conn:
            return False
        
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO agent_memory 
                    (agent_name, session_id, memory_type, key_name, content, content_json,
                     tags, importance, expires_at, created_by, project, related_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (agent_name, key_name) DO UPDATE SET
                    content = EXCLUDED.content,
                    content_json = EXCLUDED.content_json,
                    tags = EXCLUDED.tags,
                    importance = EXCLUDED.importance,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
            """, (
                self.agent_name, self.session_id, memory_type, key_name, content,
                json.dumps(content_json) if content_json else None,
                tags, importance, expires_at, self.agent_name, self.project, related_agent
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar memoria: {e}")
            if conn:
                conn.close()
            return False
    
    def save_context(self, key_name: str, content: str, **kwargs) -> bool:
        """Guardar contexto (tipo default)."""
        return self.save(key_name, content, memory_type='context', **kwargs)
    
    def save_fact(self, key_name: str, content: str, importance: int = 3, **kwargs) -> bool:
        """Guardar un hecho importante."""
        return self.save(key_name, content, memory_type='fact', importance=importance, **kwargs)
    
    def save_preference(self, key_name: str, content: str, **kwargs) -> bool:
        """Guardar preferencia del usuario."""
        return self.save(key_name, content, memory_type='preference', **kwargs)
    
    def save_task(self, key_name: str, content: str, **kwargs) -> bool:
        """Guardar estado de tarea."""
        return self.save(key_name, content, memory_type='task', **kwargs)
    
    def get(self, key_name: str) -> Optional[Dict[str, Any]]:
        """Obtener un dato específico por key_name."""
        conn = get_db_conn()
        if not conn:
            return None
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT key_name, content, content_json, memory_type, tags, importance, 
                       created_at, updated_at, related_agent
                FROM agent_memory
                WHERE agent_name = %s AND key_name = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (self.agent_name, key_name))
            
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row:
                return {
                    'key_name': row[0],
                    'content': row[1],
                    'content_json': row[2],
                    'memory_type': row[3],
                    'tags': row[4],
                    'importance': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                    'related_agent': row[8],
                }
            return None
        except Exception as e:
            print(f"[ERROR] No se pudo leer memoria: {e}")
            if conn:
                conn.close()
            return None
    
    def get_recent(self, days: int = 7, memory_type: Optional[str] = None, 
                   limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener memorias recientes del agente.
        
        Args:
            days: Días hacia atrás a buscar
            memory_type: Filtrar por tipo de memoria
            limit: Límite de resultados
        
        Returns:
            Lista de memorias
        """
        conn = get_db_conn()
        if not conn:
            return []
        
        try:
            cur = conn.cursor()
            
            if memory_type:
                cur.execute("""
                    SELECT key_name, content, content_json, memory_type, tags, importance,
                           created_at, updated_at, related_agent
                    FROM agent_memory
                    WHERE agent_name = %s AND memory_type = %s
                      AND created_at >= CURRENT_DATE - (%s || ' days')::INTERVAL
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY importance DESC, updated_at DESC
                    LIMIT %s
                """, (self.agent_name, memory_type, str(days), limit))
            else:
                cur.execute("""
                    SELECT key_name, content, content_json, memory_type, tags, importance,
                           created_at, updated_at, related_agent
                    FROM agent_memory
                    WHERE agent_name = %s
                      AND created_at >= CURRENT_DATE - (%s || ' days')::INTERVAL
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY importance DESC, updated_at DESC
                    LIMIT %s
                """, (self.agent_name, str(days), limit))
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            return [
                {
                    'key_name': row[0],
                    'content': row[1],
                    'content_json': row[2],
                    'memory_type': row[3],
                    'tags': row[4],
                    'importance': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                    'related_agent': row[8],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[ERROR] No se pudieron leer memorias: {e}")
            if conn:
                conn.close()
            return []
    
    def get_context_summary(self, days: int = 7) -> str:
        """Obtener resumen de contexto del agente para context window.
        
        Returns string formateado con las memorias más importantes.
        """
        memories = self.get_recent(days, limit=20)
        
        if not memories:
            return f"[{self.agent_name}] Sin memoria reciente"
        
        lines = [f"=== MEMORIA DE {self.agent_name.upper()} (últimos {days} días) ==="]
        
        # Agrupar por tipo
        by_type = {}
        for m in memories:
            t = m['memory_type']
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m)
        
        for mem_type, items in by_type.items():
            lines.append(f"\n[{mem_type.upper()}]")
            for item in items[:5]:  # Max 5 por tipo
                lines.append(f"  • {item['key_name']}: {item['content'][:100]}")
        
        return "\n".join(lines)
    
    def search_by_tag(self, tag: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Buscar memorias por tag."""
        conn = get_db_conn()
        if not conn:
            return []
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT key_name, content, content_json, memory_type, tags, importance,
                       created_at, updated_at, related_agent
                FROM agent_memory
                WHERE agent_name = %s AND %s = ANY(tags)
                ORDER BY importance DESC, updated_at DESC
                LIMIT %s
            """, (self.agent_name, tag, limit))
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            return [
                {
                    'key_name': row[0], 'content': row[1], 'content_json': row[2],
                    'memory_type': row[3], 'tags': row[4], 'importance': row[5],
                    'created_at': row[6], 'updated_at': row[7], 'related_agent': row[8],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[ERROR] No se pudieron buscar memorias: {e}")
            if conn:
                conn.close()
            return []
    
    def delete(self, key_name: str) -> bool:
        """Eliminar una memoria específica."""
        conn = get_db_conn()
        if not conn:
            return False
        
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM agent_memory WHERE agent_name = %s AND key_name = %s
            """, (self.agent_name, key_name))
            conn.commit()
            deleted = cur.rowcount > 0
            cur.close()
            conn.close()
            return deleted
        except Exception as e:
            print(f"[ERROR] No se pudo eliminar memoria: {e}")
            if conn:
                conn.close()
            return False
    
    def clear_old(self, days: int = 30) -> int:
        """Eliminar memorias antiguas (mayor a days). Retorna cantidad eliminada."""
        conn = get_db_conn()
        if not conn:
            return 0
        
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM agent_memory 
                WHERE agent_name = %s 
                  AND created_at < CURRENT_DATE - (%s || ' days')::INTERVAL
                  AND (expires_at IS NULL OR expires_at < NOW())
            """, (self.agent_name, str(days)))
            conn.commit()
            deleted = cur.rowcount
            cur.close()
            conn.close()
            return deleted
        except Exception as e:
            print(f"[ERROR] No se pudieron eliminar memorias antiguas: {e}")
            if conn:
                conn.close()
            return 0


# ── Shared Memory Functions ────────────────────────────────────────────────
def get_shared_context(project: str = 'SIMMOON', agent_exclude: Optional[str] = None,
                       days: int = 7, limit: int = 30) -> List[Dict[str, Any]]:
    """Obtener contexto compartido entre todos los agentes.
    
    Args:
        project: Proyecto a filtrar
        agent_exclude: Agente a excluir (ej: 'buffy' para no incluir propias memorias)
        days: Días hacia atrás
        limit: Límite de resultados
    
    Returns:
        Lista de memorias compartidas ordenadas por importancia
    """
    conn = get_db_conn()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if agent_exclude:
            cur.execute("""
                SELECT agent_name, key_name, content, content_json, memory_type, tags,
                       importance, created_at, updated_at, related_agent
                FROM agent_memory
                WHERE project = %s 
                  AND agent_name != %s
                  AND created_at >= CURRENT_DATE - (%s || ' days')::INTERVAL
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY importance DESC, created_at DESC
                LIMIT %s
            """, (project, agent_exclude, str(days), limit))
        else:
            cur.execute("""
                SELECT agent_name, key_name, content, content_json, memory_type, tags,
                       importance, created_at, updated_at, related_agent
                FROM agent_memory
                WHERE project = %s 
                  AND created_at >= CURRENT_DATE - (%s || ' days')::INTERVAL
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY importance DESC, created_at DESC
                LIMIT %s
            """, (project, str(days), limit))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            {
                'agent_name': row[0], 'key_name': row[1], 'content': row[2],
                'content_json': row[3], 'memory_type': row[4], 'tags': row[5],
                'importance': row[6], 'created_at': row[7], 'updated_at': row[8],
                'related_agent': row[9],
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[ERROR] No se pudo obtener contexto compartido: {e}")
        if conn:
            conn.close()
        return []


def get_all_agents_memory_summary(project: str = 'SIMMOON', days: int = 7) -> str:
    """Obtener resumen de memoria de todos los agentes (para context window).
    
    Returns string formateado con resumen de memorias por agente.
    """
    conn = get_db_conn()
    if not conn:
        return "[Error] PostgreSQL no disponible"
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT agent_name FROM agent_memory 
            WHERE project = %s AND created_at >= CURRENT_DATE - (%s || ' days')::INTERVAL
            ORDER BY agent_name
        """, (project, str(days)))
        
        agents = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        lines = [f"=== MEMORIA COMPARTIDA DEL PROYECTO {project} (últimos {days} días) ==="]
        
        for agent in agents:
            memory = AgentMemory(agent, project=project)
            summary = memory.get_context_summary(days)
            lines.append(f"\n{summary}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"[Error] No se pudo obtener resumen: {e}"


# ── Hermes ↔ OpenHuman Bridge ─────────────────────────────────────────────
def sync_hermes_to_openhuman() -> bool:
    """Sincronizar memorias importantes de Hermes a OpenHuman."""
    hermes_memory = AgentMemory('hermes')
    openhuman_memory = AgentMemory('openhuman')
    
    # Obtener memorias importantes de Hermes
    hermes_memories = hermes_memory.get_recent(days=7, memory_type='fact', limit=10)
    synced = 0
    for m in hermes_memories:
            if openhuman_memory.save(
                key_name=f"hermes_{m['key_name']}",
                content=m['content'],
                memory_type='context',
                tags=(m.get('tags') or []) + ['synced_from_hermes', 'shared'],
                importance=min(m.get('importance', 3), 4),
                related_agent='hermes'
            ):
                synced += 1

    return synced > 0


def sync_openhuman_to_hermes() -> bool:
    """Sincronizar memorias importantes de OpenHuman a Hermes."""
    openhuman_memory = AgentMemory('openhuman')
    hermes_memory = AgentMemory('hermes')
    
    openhuman_memories = openhuman_memory.get_recent(days=7, memory_type='fact', limit=10)
    
    synced = 0
    for m in openhuman_memories:
        if hermes_memory.save(
            key_name=f"openhuman_{m['key_name']}",
            content=m['content'],
            memory_type='context',
            tags=(m.get('tags') or []) + ['synced_from_openhuman', 'shared'],
            importance=min(m.get('importance', 3), 4),
            related_agent='openhuman'
        ):
            synced += 1
    
    return synced > 0


# ── CLI Interface ──────────────────────────────────────────────────────────
def main():
    """Interfaz CLI para agent_memory."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Memory — Sistema de Memoria Compartida")
    parser.add_argument('--agent', '-a', default='test', help='Nombre del agente')
    parser.add_argument('--save', '-s', nargs=3, metavar=('KEY', 'TYPE', 'CONTENT'),
                        help='Guardar memoria: key_name memory_type content')
    parser.add_argument('--get', '-g', help='Obtener memoria por key_name')
    parser.add_argument('--recent', '-r', type=int, nargs='?', const=7, default=0,
                        help='Ver memorias recientes (días, default 7)')
    parser.add_argument('--sync-hermes', action='store_true', help='Sincronizar Hermes → OpenHuman')
    parser.add_argument('--sync-openhuman', action='store_true', help='Sincronizar OpenHuman → Hermes')
    parser.add_argument('--summary', action='store_true', help='Resumen de todos los agentes')
    parser.add_argument('--project', '-p', default='SIMMOON', help='Nombre del proyecto')
    
    args = parser.parse_args()
    
    memory = AgentMemory(args.agent, project=args.project)
    
    if args.save:
        key, mem_type, content = args.save
        if memory.save(key, content, memory_type=mem_type):
            print(f"✅ Guardado: {key} ({mem_type})")
        else:
            print(f"❌ Error al guardar")
    
    elif args.get:
        result = memory.get(args.get)
        if result:
            print(f"📄 {result['key_name']} [{result['memory_type']}]")
            print(f"   {result['content']}")
            print(f"   Importancia: {result['importance']} | Tags: {result.get('tags', [])}")
        else:
            print(f"❌ No encontrada: {args.get}")
    
    elif args.recent > 0:
        memories = memory.get_recent(days=args.recent)
        print(f"\n📋 Memorias de '{args.agent}' (últimos {args.recent} días):")
        print(f"   {'='*60}")
        for m in memories:
            print(f"   [{m['memory_type']}] {m['key_name']}: {m['content'][:60]}...")
    
    elif args.sync_hermes:
        if sync_hermes_to_openhuman():
            print("✅ Memorias de Hermes sincronizadas a OpenHuman")
        else:
            print("❌ Error en sincronización")
    
    elif args.sync_openhuman:
        if sync_openhuman_to_hermes():
            print("✅ Memorias de OpenHuman sincronizadas a Hermes")
        else:
            print("❌ Error en sincronización")
    
    elif args.summary:
        print(get_all_agents_memory_summary(args.project))
    
    else:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python agent_memory.py --agent hermes --save 'current_task' 'task' 'Generar resumen diario'")
        print("    python agent_memory.py --agent hermes --get current_task")
        print("    python agent_memory.py --agent hermes --recent 7")
        print("    python agent_memory.py --summary")


if __name__ == "__main__":
    main()