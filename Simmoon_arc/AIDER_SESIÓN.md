# 🎮 SIMMOON — Sesión para Aider + Ollama

> Copia y pega esto en Aider para que entienda el contexto completo del juego.

## 📋 Estado del Proyecto

Eres un asistente de programación trabajando en **SIMMOON**, un constructor de colonias lunares en 2.5D isométrico hecho con Pygame.

### Stack técnico:
- **Motor**: Pygame 2.6.1
- **Grid**: 40×40 tiles isométricos (dimétrica 2:1)
- **Archivo principal**: `juego_simmoon.py` (~2200 líneas)
- **Terreno**: `simmoon_terrain.py` — 7 biomas procedurales (FBM noise + cráteres)
- **Mecánicas**: `simmoon_mecanicas.py` — turnos, población, recursos
- **Pipeline IA**: `simmoon_pipeline.py` — LangGraph: Prompts → ComfyUI → Pixel Art → PostgreSQL
- **Backend generación**: ComfyUI en WSL2 (puerto 8188)
- **LLM local**: Ollama en WSL2 (puerto 11434) — modelos qwen2.5-coder:14b, qwen3:14b
- **Base de datos**: PostgreSQL en WSL2 (puerto 5432), DB `simmoon`
- **Vote API**: `vote_api.py` en puerto 9099

### Decisiones de diseño vigentes (NO MODIFICAR sin consultar):
1. **D001** — 4 zonas: 🏠 Alojamiento, 🏢 Comercial, 🏭 Industrial, 🌱 Ecológico
2. **D002** — Edificios públicos = colocación directa, privados = auto-settlement en zonas
3. **D003** — Grid 40×40 tiles
4. **D004** — Sistema de turnos con ciclo lunar (14 días luz + 14 días noche)
5. **D005** — Recursos: 💰 Créditos · ⚡ Energía · 🫁 Oxígeno · 💧 Agua · 💨 Presión · 😊 Felicidad
6. **D006** — 7 biomas de terreno lunar procedural
7. **D007** — Alojamiento renovado: 5 albergues balanceados (ROI 22-29 turnos), Hotel movido a Comercial

### Assets:
- 1536 PNGs generados (768 originales + 768 pixel-art)
- 5 checkpoints de ComfyUI, 3 LoRAs
- 7 runs de generación completados

---

## 🎯 Siguientes Pasos Prioritarios

Por favor, trabaja en estos pendientes en orden:

### 🔴 Prioridad Alta
1. **Probar launch_all.ps1 completo** — Verificar que lanza todos los servicios (WSL2, Ollama, ComfyUI, PostgreSQL, Vote API, Viewer, Voice Bridge) correctamente
2. **Revisar y corregir auto-settlement** — La lógica de colocación automática de edificios privados en zonas pintadas necesita verificación

### 🟡 Prioridad Media
3. **Arreglar binario invokeai** — El comando es `invokeai-web`, no `invokeai`
4. **Pipeline LangGraph end-to-end** — Probar `simmoon_pipeline.py` con `--skip-generation --skip-db`
5. **Balance de otras categorías** — Comparar ROI de edificios de negocio e industria vs alojamiento

### 🟢 Prioridad Baja
6. **Evaluar Leonardo.ai y Scenario.gg** — APIs cloud de generación (documentadas en `LEONARDO_INVOKEAI_SCENARIO.md`)

---

## 📂 Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `juego_simmoon.py` | 🎮 Juego principal (~2200 líneas) |
| `simmoon_terrain.py` | 🏔️ Generación procedural de terreno |
| `simmoon_mecanicas.py` | ⚙️ Mecánicas de juego (turnos, economía) |
| `simmoon_pipeline.py` | 🔄 Pipeline LangGraph completo |
| `vote_api.py` | 🗳️ API REST de votos (PostgreSQL) |
| `config.json` | ⚙️ Configuración del sistema |
| `schema.sql` | 🗄️ Esquema de base de datos |
| `../proyecto_0/DECISIONES.md` | 📐 Registro de decisiones de diseño |
| `../proyecto_0/balance_albergues.md` | ⚖️ Tabla de ROI de alojamiento |

---

## ⚠️ Reglas Importantes

1. **LEER `../proyecto_0/DECISIONES.md` antes de modificar el juego**
2. NO cambiar decisiones de diseño sin registrarlas en DECISIONES.md
3. Los edificios privados van en auto-settlement, los públicos en colocación directa
4. Todos los nuevos cambios deben mantener compatibilidad con PostgreSQL
5. El juego debe seguir ejecutándose sin errores después de cada cambio
6. Actualizar `../proyecto_0/siguiente.md` al completar cada tarea
