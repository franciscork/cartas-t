# Siguientes Pasos — Próxima Sesión

> Fecha: 2026-06-09 (madrugada) → Próxima sesión

---

## ✅ Completado en esta Sesión (2026-06-09)

| # | Tarea | Estado |
|---|-------|--------|
| — | **Alojamiento y Balance** | |
| 1 | Renovar sistema de alojamiento completo | ✅ Ver D007 en DECISIONES.md |
| 2 | Zona "Residencial" → "Alojamiento" | ✅ Nombre, icono, categorías |
| 3 | Albergues renombrados y rebalanceados | ✅ 5 albergues + Hotel a negocios |
| 4 | Hotel (hou_03) movido a zona Comercial | ✅ Categoría "businesses" |
| 5 | biz_02 restaurado de corrupción | ✅ Costo 300→400, energía -2→-3 |
| 6 | Rango de alquiler zona alojamiento 10-80→8-50 | ✅ Más accesible |
| 7 | Panel "Vivienda" → "Alojamiento" | ✅ UI actualizada |
| 8 | DECISIONES.md actualizado | ✅ D001 modificado + D007 nueva |
| 9 | Juego lanzado y verificado visualmente | ✅ Sin errores |
| 10 | Análisis ROI completo de albergues | ✅ balance_albergues.md creado |
| 11 | Balance económico: hou_04 alquiler 30→38 | ✅ ROI 30t→23t |
| 12 | Balance económico: site_08 alquiler 35→45 | ✅ ROI 30t→22t |
| 13 | Balance económico: hou_03 (Hotel) alquiler 120→100 | ✅ ROI 20t→24t |
| 14 | Balance económico: hou_02 alquiler 22→26 | ✅ ROI 29t→24t |
| — | **Voice Bridge** | |
| 15 | Bugfix global VOZ (SyntaxError) | ✅ En seleccionar_voz() y main() |
| 16 | Bugfix encoding UTF-8 en Windows | ✅ PYTHONIOENCODING=utf-8 |
| 17 | Voz por defecto: es-CL→es-ES-AlvaroNeural | ✅ España masculina |
| 18 | Config .voice_bridge_config.json eliminado | ✅ Para usar nuevo default |
| 19 | Voice Bridge funcional (--say, --hotkey) | ✅ Probado y verificado |
| — | **Launch Scripts** | |
| 20 | launch_all.ps1: integración Voice Bridge | ✅ Step 7, hotkey mode |
| 21 | launch_all.ps1: parámetro -NoVoice | ✅ Para omitir Voice Bridge |
| 22 | launch_all.ps1: bugfix here-string | ✅ "@ en su propia línea |
| 23 | launch_all.ps1: Clear-Host try/catch | ✅ Para entornos headless |
| 24 | launch_all.ps1: -NoViewer consistente | ✅ Mensaje [SKIP] agregado |

## 🔴 Pendientes

| # | Tarea | Prioridad | Notas |
|---|-------|-----------|-------|
| 1 | Probar launch_all.ps1 completo en PC real | 🔴 | Con WSL2 + servicios reales |
| 2 | Probar dictado por voz (F4) en Codebuff | 🟡 | Voice Bridge + Codebuff juntos |
| 3 | Arreglar binario `invokeai` → es `invokeai-web` | 🟡 | El comando correcto es `invokeai-web` |
| 4 | Probar pipeline LangGraph end-to-end | 🟡 | `simmoon_pipeline.py` ya sincronizado |
| 5 | Evaluar Leonardo.ai y Scenario.gg | 🟢 | APIs documentadas |

---

## 📋 Checklist para la Próxima Sesión

- [ ] Leer `proyecto_0/DECISIONES.md` (especialmente D007)
- [ ] Leer `proyecto_0/balance_albergues.md`
- [ ] Leer `proyecto_0/LEEME_PRIMERO.md`
- [ ] Revisar `proyecto_0/estado_sistema.md`
- [ ] Probar `launch_all.ps1` en PC real
- [ ] Probar Voice Bridge con F4 (dictado)
- [ ] Arreglar binario `invokeai` en `~/invokeai-env`
- [ ] Probar pipeline LangGraph con `--skip-generation --skip-db`

---

## 📊 Estado del Proyecto

```
✅ 7 runs generados            (768 PNGs originales)
✅ Pixel-art completado         (768 PNGs pixel = 1536 total)
✅ 5 checkpoints usados
✅ 3 LoRAs
✅ ComfyUI:8188 activo
✅ Vote API :9099 validada
✅ PostgreSQL 5 tablas
✅ Pipeline sincronizado
✅ openclaw desinstalado
✅ Alojamiento renovado (D007)
✅ Balance económico (ROI 22-25t)
✅ Voice Bridge funcional (es-ES-AlvaroNeural)
✅ launch_all.ps1 con Voice Bridge integrado
⚠️ InvokeAI instalado pero sin binario
```

*Recordatorio: este directorio `proyecto_0/` es la memoria persistente entre sesiones. Leer antes de actuar.*
