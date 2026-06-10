#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║                    HERA — Agent System                      ║
║  Orquestador unificado de agentes para el ecosistema       ║
║  SIMMOON. Proporciona Message Bus, Task Queue y            ║
║  descubrimiento dinámico de agentes.                       ║
╚══════════════════════════════════════════════════════════════╝

Módulos:
    core        → HeraCore, Message, TaskQueue, MessageBus
    agents/     → Adaptadores para cada agente (próximamente)
    memory/     → Memoria unificada (próximamente)
    vault/      → Gestión de secretos (próximamente)
"""

from .core import HeraCore, Message, Task, TaskQueue, MessageBus
from .vault import Vault, HeraVault, vault as _vault_instance

__all__ = [
    "HeraCore", "Message", "Task", "TaskQueue", "MessageBus",
    "Vault", "HeraVault",
]
__version__ = "0.1.0"
