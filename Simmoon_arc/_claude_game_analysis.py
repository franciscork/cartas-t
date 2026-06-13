"""Ask Ollama/gemma3 to analyze the SIMMOON game."""
import urllib.request, json, sys

# Direct Ollama chat
url = 'http://localhost:11434/api/generate'
prompt = """Eres un analista de videojuegos. Analiza SIMMOON, un constructor de colonia lunar estilo SimCity 2000 con Pygame. Caracteristicas: grid isometrico 2:1, 40x40, 131 edificios en 22 categorias. Recursos: creditos, energia, oxigeno, agua, presion, felicidad. Sistema de turnos con auto-settlement en 4 zonas.

Responde en espanol, MAXIMO 8 lineas:
1) Un bug probable en el codigo
2) Un problema de balance economico
3) Una mejora concreta que implementarias"""

payload = json.dumps({
    "model": "gemma3:latest",
    "prompt": prompt,
    "stream": False,
}).encode('utf-8')

req = urllib.request.Request(url, data=payload,
    headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        reply = data.get("response", data.get("message", {}).get("content", "Sin respuesta"))
        print("=" * 50)
        print("CLAUDE/Gemma3 ANALISIS DEL JUEGO:")
        print("=" * 50)
        print(reply)
        print("=" * 50)
except Exception as e:
    print(f"Error: {e}")
