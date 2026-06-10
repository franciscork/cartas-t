# 📐 DECISIONES DE DISEÑO — SIMMOON Fábrica de Juegos

> ⚠️ **LEER ESTE ARCHIVO ANTES DE MODIFICAR CUALQUIER CÓDIGO DEL JUEGO**
> Este es el registro ÚNICO y AUTORITATIVO de las decisiones de diseño.
> Cada sesión empieza leyendo esto.

---

## Cómo usar este archivo

1. **Antes de modificar el juego**: leer este archivo completo
2. **Después de tomar una decisión**: agregarla aquí inmediatamente
3. **Nunca borrar una decisión** — si cambia, marcarla como `↻ MODIFICADA: [fecha]` con el nuevo acuerdo
4. **Cada decisión tiene**: fecha, contexto, acuerdo, y estado

---

## 🏗️ Decisiones de Arquitectura del Juego

### D001 — Sistema de Zonificación (4 zonas)
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Contexto** | Se discutió reducir el exceso de categorías del sistema de zonificación |
| **Acuerdo** | El juego tendrá SOLO 4 zonas de zonificación: |
| | 1. 🏠 **Alojamiento** — Albergues (hou_01, hou_02, hou_04, misc_01, site_08) |
| | 2. 🏢 **Comercial** — Negocios, servicios, entretenimiento, gobierno, universidades, hotel (hou_03) |
| | 3. 🏭 **Industrial** — Fábricas, minería, industria pesada, vehículos, transporte |
| | 4. 🌱 **Ecológico** — Invernaderos, parques, decoración, recursos vitales |
| **Implementado** | ✅ CORREGIDO — CATALOGO_ZONAS reducido a 4 zonas |
| **Detalles** | misc_05 (Ascensor Espacial) agregado a zona comercial. SIN edificios privados huérfanos. |
| **Prioridad** | 🔴 ALTA — corregir antes de la próxima jugabilidad |
| | |
| ↻ **MODIFICADA: 2026-06-09** — Zona "Residencial" → "Alojamiento". hou_03 (Hotel) movido a zona Comercial. Todos los albergues renombrados y rebalanceados (ver D007). |

### D002 — Sistema de Construcción (Público vs Privado)
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Contexto** | Se definió cómo se colocan los edificios en el mapa |
| **Acuerdo** | - **Edificios públicos**: carreteras, energía, agua, O2, bomberos, policía, decoración → colocación directa por el jugador |
| | - **Edificios privados**: negocios, viviendas, industrias, invernaderos → se colocan automáticamente (auto-settlement) en zonas pintadas |
| **Implementado** | ✅ Parcial — lógica de auto-settlement existe pero con 13 zonas incorrectas |

### D003 — Grid del Mapa
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Contexto** | Tamaño del mapa para la colonia lunar |
| **Acuerdo** | Grid de **40×40 tiles** isométricos (proyección dimétrica 2:1) |
| **Implementado** | ✅ Correcto |

### D004 — Sistema de Turnos
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Contexto** | Mecánica principal del juego |
| **Acuerdo** | - Botón "⏩ SIGUIENTE TURNO" en panel + atajo ESPACIO |
| | - Cada turno: mantenimiento → ingresos → población → auto-settlement |
| | - Ciclo lunar: 14 días luz + 14 días noche |
| **Implementado** | ✅ Funcional |

### D005 — Recursos del Juego
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Contexto** | Qué recursos gestiona el jugador |
| **Acuerdo** | 💰 Créditos · ⚡ Energía · 🫁 Oxígeno · 💧 Agua · 💨 Presión · 😊 Felicidad |
| **Implementado** | ✅ |

### D006 — Terreno Lunar (Multi-bioma)
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-08 |
| **Contexto** | Se implementó generación procedural de terreno con biomas |
| **Acuerdo** | 7 biomas: regolith, highlands, crater_floor, maria, crater_rim, ridge, basin |
| | Generación vía FBM noise + cráteres procedurales |
| | Altura normalizada (0.0-1.0) con sombreado por elevación |
| **Implementado** | ✅ Recién implementado en `simmoon_terrain.py` + parche en `juego_simmoon.py` |

### D007 — Renovación del Sistema de Alojamiento (Albergues)
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-09 |
| **Contexto** | El sistema de viviendas tenia nombres genericos, costos desbalanceados y categorias inconsistentes. La zona "Residencial" sonaba a suburbio terrestre, no a colonia lunar. El Hotel (hou_03) estaba mezclado con los albergues. |
| **Acuerdo** | Renovar TODO el sistema de alojamiento: |
| | **Zona:** "Residencial" renombrada a "Alojamiento" con icono 🏠 |
| | **Albergues** (categoria "housing"): |
| | - hou_01: "Modulo Habitacional Basico" → **Albergue Basico** (costo 400→300, energia -3→-2, alquiler 20→15) |
| | - hou_02: "Complejo Residencial" → **Albergue Comunitario** (costo 700→500, alquiler 35→22) |
| | - hou_04: "Barrio Subterraneo" → **Albergue Subterraneo** (costo 1000→700, energia -8→-6) |
| | **Hotel** movido a negocios: |
| | - hou_03: "Cupula de Lujo" → **Hotel Cupula de Lujo** (categoria "businesses", zona Comercial, costo 2000) |
| | **Albergues adicionales** en zona Alojamiento: |
| | - misc_01: "Viviendas" → **Albergue Central** (costo 600→450, alquiler 40→25) |
| | - site_08: "Sector Residencial" → **Complejo de Albergues** (costo 700→800, oxigeno -5→-3) |
| | **Rango de alquiler** de zona Alojamiento: 10-80 → **8-50** creditos |
| | **Panel:** "Vivienda" → **"Alojamiento"** en el selector de categorias |
| | **Correccion:** biz_02 restaurado de corrupcion (costo 300→400, energia -2→-3) |
| **Implementado** | ✅ Todos los cambios aplicados y verificados en runtime. Archivo compila sin errores. |
| **Detalles** | Todos los albergues siguen en EDIFICIOS_PRIVADOS. jerarquia de costos: Basico(300) < Comunitario(500) < Central(450/2x2) < Subterraneo(700/3x2) < Complejo(800/4x4). |
| **Prioridad** | 🔴 ALTA — completado |

---

## 🎨 Decisiones de Assets

### A001 — Estilo Visual
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Acuerdo** | Estilo 2.5D isométrico (dimetric projection 2:1, 26.565°) con sharp black outline, flat cel-shaded 3-tone depth, estilo SimCity 2000 + Factorio + Oxygen Not Included |
| **Implementado** | ✅ En los prompts de generación |

### A002 — Resolución Pixel-Art
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Acuerdo** | 64×64 px para edificios, 48×48 para vehículos, 32×32 para UI, 128×128 para sitios grandes. Paleta de 16 colores (32 para sitios). |
| **Implementado** | ✅ En simmoon_pixelator.py |

---

## 🧠 Decisiones de Arquitectura Técnica

### T001 — Backend de Generación
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-03 |
| **Acuerdo** | **ComfyUI** como backend oficial de generación de imágenes. ~~A1111~~ eliminado. InvokeAI en estudio. |
| **Implementado** | ✅ |

### T002 — Pipeline de Assets
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Acuerdo** | Prompt → ComfyUI (imagen) → Pixelator (pixel-art) → BD (PostgreSQL) → Viewer (HTML) |
| **Implementado** | ✅ Pipeline completo funcional |

### T003 — Persistencia de Votos
| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-04 |
| **Acuerdo** | Votos guardados en PostgreSQL vía API REST (:9099). Fallback a localStorage. |
| **Implementado** | ✅ vote_api.py funcional |

---

## 📋 Checklist de Inicio de Sesión

Cada vez que inicies una sesión:

- [ ] Leer `proyecto_0/DECISIONES.md` ← **ESTE ARCHIVO**
- [ ] Leer `proyecto_0/LEEME_PRIMERO.md`
- [ ] Leer `proyecto_0/estado_sistema.md`
- [ ] Leer `proyecto_0/siguiente.md`
- [ ] NO MODIFICAR CÓDIGO sin verificar DECISIONES.md primero

---

*Última actualización: 2026-06-09*
*Próxima acción: D007 — Playtest del nuevo sistema de alojamiento*
