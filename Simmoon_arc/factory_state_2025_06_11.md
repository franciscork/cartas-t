# FACTORY STATE - Actualizado 2025-06-11

## Cambios de Hoy

### RAM Fix (monitor_sistema.py check_ram)
- Bug: Dashboard mostraba 15.5GB en vez de 32GB
- Causa: check_ram() solo consultaba RAM real desde WSL, no desde Windows nativo
- Fix: Rama con psutil.virtual_memory() para Windows nativo
- Verificado: 31.7GB correctos via API /api/health

### Factory State
- minimax-m3:cloud funciona con ollama launch claude (limit reached, resets ~5h)
- 3 categorias implementadas en game_config.py: characters, lunar_flora, infrastructure
- Pendientes: TAREA 6 (overlay resumen), TAREA 7 (selector visual)
