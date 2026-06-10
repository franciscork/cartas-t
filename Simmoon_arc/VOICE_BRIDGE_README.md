# 🎤 Puente de Voz — SIMMOON

## Instalación (ya está)

```bash
pip install SpeechRecognition sounddevice numpy keyboard pyperclip edge-tts
```
✅ Todo instalado.

## Cómo usarlo

### Opción 1 — Menú interactivo (recomendado)

Abre una **terminal APARTE** (junto a Codebuff) y ejecuta:

```bash
cd Simmoon_arc
python voice_bridge.py
```

Menú:
- **Opción 1** → Hablas, se transcribe, se escribe solo en Codebuff 🎤  
- **Opción 2** → Escribís texto y lo lee en voz alta 🔊  
- **Opción 3** → Lee lo que tengas en el portapapeles 📋  

### Opción 2 — Modo Hotkey (F4/F5/F6)

```bash
cd Simmoon_arc
python voice_bridge.py --hotkey
```

- **F4** → Hablas → se transcribe → se escribe en la ventana activa 🎤  
- **F5** → Lee el texto seleccionado (primero enfoca otra ventana) 🔊  
- **F6** → Lee el portapapeles 📋  
- **ESC** → Salir  

### Opción 3 — Comandos directos

```bash
python voice_bridge.py --listen           # Escuchar una vez
python voice_bridge.py --say "texto"      # Leer texto
python voice_bridge.py --clipboard        # Leer portapapeles
python voice_bridge.py --voz "es-ES-AlvaroNeural"  # Cambiar voz
```
