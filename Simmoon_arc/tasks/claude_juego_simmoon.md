# Tarea: Investigar cierre prematuro de juego_simmoon.py

## Problema
El juego `juego_simmoon.py` se abre y se cierra inmediatamente sin esperar interacción del usuario ("se fue sin tocar nada").

## Contexto
- El archivo `juego_simmoon.py` tenía errores de sintaxis que fueron corregidos:
  - 3 `elif` anidados ilegalmente convertidos a `if` independientes (L3699, L3703, L3753)
  - 5 `continue` fuera de bucles reemplazados por `pass` (L3721, L3757, L3870, L3889, L3976)
  - Indentaciones corregidas en L3755, L3763, L3765
- En pruebas CLI, el juego arranca correctamente: carga pygame-ce 2.5.7, carga 112 assets vía API, y se mantiene ejecutándose hasta timeout.
- En escritorio Windows, la ventana aparece y se cierra sin dar tiempo a interactuar.

## Posibles causas
1. Error de runtime no capturado (sin try/except en el main loop)
2. `pygame.quit()` llamado prematuramente al inicio del loop
3. Asset faltante que causa excepción no manejada
4. Configuración de display incorrecta para Windows
5. Los `continue` reemplazados por `pass` alteraron el flujo del game loop

## Assets cargados correctamente
- Votos desde API: 112 assets OK
- Pygame-ce 2.5.7: OK
- Sintaxis del archivo: OK (ast.parse + compile pasan)

## Reproducir
```bash
cd Simmoon_arc
PYTHONIOENCODING=utf-8 python juego_simmoon.py
```

## Acceso directo creado
- `C:\Users\docus\Desktop\SIMMOON_Colonia_Lunar.bat`
- Incluye `set PYTHONIOENCODING=utf-8` para evitar errores Unicode en Windows
- Al finalizar, hace `pause >nul` para que la ventana no se cierre inmediatamente (útil para ver errores)

## Fix de encoding
El juego necesita `PYTHONIOENCODING=utf-8` para mostrar caracteres Unicode (┌─┐, ☾, etc.) en la consola de Windows (CP1252). Sin esto, los prints con box-drawing chars causan `UnicodeEncodeError`.

```bash
cd Simmoon_arc
set PYTHONIOENCODING=utf-8
python juego_simmoon.py
```

## Archivos relevantes
- `Simmoon_arc/juego_simmoon.py` — el juego principal (152k chars, ~4800 líneas)
- `Simmoon_arc/game_config.py` — configuración del juego
- `Simmoon_arc/config.json` — config general
- `C:\Users\docus\Desktop\SIMMOON_Colonia_Lunar.bat` — launcher en escritorio

## Historial de cambios
- Sintaxis corregida (indentación, continues) — commit `8ee689d`
- `_fix_*.py` scripts temporales eliminados

## Prioridad
Alta — el juego no es jugable.
