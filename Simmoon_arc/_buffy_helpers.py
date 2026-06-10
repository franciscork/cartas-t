
# ── Helpers for Agent Activity Logging ────────────────────────────────────

def log_buffy(message: str):
    ""Registra actividad de Buffy para los reportes de Agatha.""
    log("Buffy", "🦙", message)


def log_claude(message: str):
    ""Registra actividad de Claude Code para los reportes de Agatha.""
    log("Claude Code", "🤖", message)


def get_agent_activity(source: str = None, limit: int = 5) -> list:
    ""Obtiene actividad reciente de un agente.""
    entries = get_recent(100)
    if source:
        entries = [e for e in entries if e.get('source') -eq source]
    return entries[:limit]

