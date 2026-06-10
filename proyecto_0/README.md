# proyecto_0 — Memoria del Sistema SIMMOON

> Fecha: 2026-06-04  — Esquema v5.0 (honesto y actual)

---

## Arquitectura Actual

```
Windows 11 ──────────── Freebuff
└── WSL2 Ubuntu 24.04 ─── comfyui … Leonardo.ai, InvokeAI, Scenario.gg ?
    ├── Ollama
    │   └── LangGraph, AutoGen, CrewAI
    ├── Docker
    ├── uv
    ├── pnpm
    ├── Python 3.12
    └── Qwen3-Coder
```

---

## ⚠️ Lectura Obligatoria al Iniciar Sesión

1. **`LEEME_PRIMERO.md`** — Protocolo de memoria para el asistente
2. **`system_agent.html`** — Documento maestro (abrir en Chrome)
3. **`estado_sistema.md`** — Estado verificado de cada componente
4. **`siguiente.md`** — Lo que el usuario quería hacer después

---

## Archivos de Memoria

| Archivo | Contenido | Prioridad |
|---------|-----------|-----------|
| `LEEME_PRIMERO.md` | Protocolo de inicio | 🔴 Alta |
| `system_agent.html` | **Documento maestro** — arquitectura, estado, tutorial visual | 🔴 Alta |
| `estado_sistema.md` | Estado real verificado de cada componente | 🔴 Alta |
| `siguiente.md` | Próximos pasos sugeridos | 🟡 Media |
| `arquitectura.md` | Diagrama honesto de la fábrica de juegos | 🟢 Referencia |
| `acciones_hoy.md` | Log de sesiones anteriores | 🟢 Referencia |

---

## Estado Actual (2026-06-04)

- **7 runs generados** con ComfyUI (todos los checkpoints)
- **Counterfeit-V3.0:** ✅ 108/108 imágenes completado
- **A1111:** ❌ Eliminado — ComfyUI es el backend oficial
- **openclaw:** ❌ Desinstalado
- **Assets totales:** ~800+ PNGs en disco
- **PostgreSQL:** Disponible con 108 assets en DB `simmoon`
