#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏭 FactoryGames — Sistema de Orquestación
==========================================
Buffy (DeepSeek) supervisa, los agentes ejecutan.

Módulos:
  - orchestrator:    Orquestador principal (FactoryOrchestrator)
  - agent_registry:  Registro y descubrimiento de agentes
  - task_dispatcher: Despachador de tareas al agente correcto
  - health_monitor:  Monitor de salud de servicios
  - logging:         Sistema de logging estructurado
  - cli:             Interfaz de línea de comandos
"""

from .orchestrator import FactoryOrchestrator

__all__ = ["FactoryOrchestrator"]
__version__ = "1.0.0"
