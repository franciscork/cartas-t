@echo off
REM Test Claude Code with Ollama via Anthropic Messages API
set ANTHROPIC_BASE_URL=http://localhost:11434
set ANTHROPIC_AUTH_TOKEN=ollama
set ANTHROPIC_API_KEY=
echo [TEST] Environment set. Running Claude Code with Ollama...
echo [TEST] Model: qwen2.5-coder:14b
echo.
"C:\Users\docus\AppData\Roaming\npm\claude.cmd" -p "Responde solo: CLAUDE_CODE_CON_OLLAMA_EXITOSO" --dangerously-skip-permissions --no-session-persistence --model qwen2.5-coder:14b
echo.
echo [TEST] Exit code: %ERRORLEVEL%
