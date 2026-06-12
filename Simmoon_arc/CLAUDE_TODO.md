# 🎯 CLAUDE — Tareas Pendientes en SIMMOON

## 📋 Resumen

El juego tiene **20 categorías de sprites pixel-art** post-procesados. **16 ya están integradas** en `CATALOGO_EDIFICIOS` (game_config.py). Faltan **3 categorías (14 sprites)**:

| Categoría | Sprites | Estado |
|---|---|---|
| ❌ **characters** | 6 sprites | No está en catálogo, ni en panel, ni en minimapa |
| ❌ **lunar_flora** | 4 sprites | No está en catálogo, ni en panel, ni en minimapa |
| ❌ **infrastructure** | 4 sprites | No está en catálogo, ni en panel, ni en minimapa |

---

## TAREA 1: Agregar entradas a `CATALOGO_EDIFICIOS` en `game_config.py`

### Formato exacto que debes seguir (mira un ejemplo existente como `dec_01`):

```python
"dec_01": TipoEdificio("dec_01", "Formación Rocosa", "decorations",
                       "dec_01_lunar_rock_formation_pixel.png",
                       costo=20, mantenimiento=0,
                       descripcion="Roca natural lunar decorativa."),
```

### 1A — `characters` (6 sprites)

Archivos en `characters_pixel/`:
- `char_01_astronaut_worker_pixel.png`
- `char_02_scientist_pixel.png`
- `char_03_security_guard_pixel.png`
- `char_04_miner_pixel.png`
- `char_05_medical_officer_pixel.png`
- `char_06_pilot_pixel.png`

Agrégalos como edificios decorativos/empleados con `produce_felicidad`:
```python
# ── Personajes (characters) ──
"char_01": TipoEdificio("char_01", "Astronauta Trabajador", "characters",
                        "char_01_astronaut_worker_pixel.png",
                        costo=100, produce_energia=-1,
                        mantenimiento=2, empleos=1,
                        produce_felicidad=3,
                        descripcion="Colono trabajador de la colonia lunar."),
"char_02": TipoEdificio("char_02", "Científico", "characters",
                        "char_02_scientist_pixel.png",
                        costo=150, produce_energia=-1,
                        mantenimiento=2, empleos=2,
                        produce_felicidad=4,
                        descripcion="Investigador del laboratorio lunar."),
"char_03": TipoEdificio("char_03", "Guardia de Seguridad", "characters",
                        "char_03_security_guard_pixel.png",
                        costo=120, produce_energia=-1,
                        mantenimiento=2, empleos=1,
                        produce_felicidad=2,
                        descripcion="Protege la colonia de amenazas."),
"char_04": TipoEdificio("char_04", "Minero", "characters",
                        "char_04_miner_pixel.png",
                        costo=130, produce_energia=-2,
                        mantenimiento=3, empleos=1,
                        produce_felicidad=2,
                        descripcion="Excava recursos del regolito lunar."),
"char_05": TipoEdificio("char_05", "Oficial Médico", "characters",
                        "char_05_medical_officer_pixel.png",
                        costo=180, produce_energia=-2,
                        mantenimiento=4, empleos=2,
                        produce_felicidad=6,
                        descripcion="Atiende la salud de los colonos."),
"char_06": TipoEdificio("char_06", "Piloto", "characters",
                        "char_06_pilot_pixel.png",
                        costo=160, produce_energia=-2,
                        mantenimiento=3, empleos=2,
                        produce_felicidad=4,
                        descripcion="Pilota naves y lanzaderas lunares."),
```

### 1B — `lunar_flora` (4 sprites)

Archivos en `lunar_flora_pixel/`:
- `flora_01_crystal_fungus_pixel.png`
- `flora_02_lunar_moss_pixel.png`
- `flora_03_tube_plant_pixel.png`
- `flora_04_glow_flower_pixel.png`

Agrégalos como decoración natural que produce oxígeno:
```python
# ── Flora Lunar (lunar_flora) ──
"flora_01": TipoEdificio("flora_01", "Hongo de Cristal", "lunar_flora",
                         "flora_01_crystal_fungus_pixel.png",
                         costo=30, mantenimiento=0,
                         produce_oxigeno=1,
                         descripcion="Hongo bioluminiscente que produce oxígeno."),
"flora_02": TipoEdificio("flora_02", "Musgo Lunar", "lunar_flora",
                         "lunar_moss_pixel.png",  # ← CORREGIR: el archivo es flora_02_lunar_moss_pixel.png
                         costo=20, mantenimiento=0,
                         produce_oxigeno=2,
                         descripcion="Alfombra de musgo adaptado al vacío."),
"flora_03": TipoEdificio("flora_03", "Planta Tubular", "lunar_flora",
                         "flora_03_tube_plant_pixel.png",
                         costo=40, mantenimiento=0,
                         produce_oxigeno=1, produce_felicidad=2,
                         descripcion="Planta alienígena de tallos huecos."),
"flora_04": TipoEdificio("flora_04", "Flor Luminiscente", "lunar_flora",
                         "flora_04_glow_flower_pixel.png",
                         costo=50, mantenimiento=0,
                         produce_oxigeno=1, produce_felicidad=3,
                         descripcion="Flor que brilla en la oscuridad lunar."),
```

⚠️ **NOTA:** El sprite `flora_02` tiene nombre de archivo `flora_02_lunar_moss_pixel.png`, NO `lunar_moss_pixel.png`. Asegúrate de usar el nombre correcto.

### 1C — `infrastructure` (4 sprites)

Archivos en `infrastructure_pixel/`:
- `infra_01_pressure_pipe_pixel.png`
- `infra_02_power_cable_pixel.png`
- `infra_03_water_pipeline_pixel.png`
- `infra_04_transport_tube_pixel.png`

Agrégalos como infraestructura pública (como las carreteras):
```python
# ── Infraestructura (infrastructure) ──
"infra_01": TipoEdificio("infra_01", "Tubería de Presión", "infrastructure",
                         "infra_01_pressure_pipe_pixel.png",
                         costo=80, mantenimiento=0,
                         produce_presion=2,
                         descripcion="Mantiene la presión atmosférica."),
"infra_02": TipoEdificio("infra_02", "Cable Eléctrico", "infrastructure",
                         "infra_02_power_cable_pixel.png",
                         costo=60, mantenimiento=0,
                         descripcion="Distribuye energía por la colonia."),
"infra_03": TipoEdificio("infra_03", "Tubería de Agua", "infrastructure",
                         "infra_03_water_pipeline_pixel.png",
                         costo=70, mantenimiento=0,
                         produce_agua=1,
                         descripcion="Conduce agua a los edificios."),
"infra_04": TipoEdificio("infra_04", "Tubo de Transporte", "infrastructure",
                         "infra_04_transport_tube_pixel.png",
                         costo=100, mantenimiento=0,
                         descripcion="Cápsula de transporte neumático."),
```

### Dónde insertar el código

En `game_config.py`, las categorías están ordenadas alfabéticamente por sección. Inserta:

1. `characters` — **antes** de `# ── Decoración (decorations)` (después de civic/buildings_misc)
2. `lunar_flora` — **después** de `# ── Invernaderos (greenhouses)` 
3. `infrastructure` — **después** de `# ── Industria / Producción (industry)` o antes de transport

---

## TAREA 2: Agregar al panel lateral en `renderizador.py`

Archivo: `Simmoon_arc/renderizador.py`, método `renderizar_panel()`, lista `categorias` (~línea 568).

Agrega 3 nuevas entradas al array (orden alfabético, justo donde corresponda):

```python
("👤 Personajes", "characters"),       # después de Decoración o antes de Edificios
("🌿 Flora Lunar", "lunar_flora"),      # después de Invernadero
("🔧 Infraestructura", "infrastructure"), # después de Industria o antes de Transporte
```

También en el mensaje de "sin edificios" (línea ~646), agrega las nuevas categorías al condicional `elif categoria_actual in (...)` si son privadas, o déjalas pasar al else si son públicas.

---

## TAREA 3: Agregar colores al minimapa en `renderizador.py`

Archivo: `Simmoon_arc/renderizador.py`, método `renderizar_minimapa()` (~línea 751).

Agrega estos colores al bloque `if cat == ... elif cat == ...`:

```python
elif cat == "characters":
    color = (200, 180, 100)  # Dorado personajes
elif cat == "lunar_flora":
    color = (100, 220, 100)  # Verde flora
elif cat == "infrastructure":
    color = (180, 180, 200)  # Gris claro infraestructura
```

---

## TAREA 4: Opcional — Agregar a zonas en `CATALOGO_ZONAS` (game_config.py)

Puedes agregar los nuevos edificios a las zonas existentes en `CATALOGO_ZONAS`:

- `characters` → zona **Comercial** (son NPCs que trabajan)
- `lunar_flora` → zona **Ecológico** (flora natural)
- `infrastructure` → zona **Industrial** (infraestructura)

O déjalos como edificios públicos (no requieren zonificación). Depende de ti — elige lo que tenga más sentido.

---

## TAREA 5: Opcional — Agregar a `EDIFICIOS_PRIVADOS` (game_config.py)

Si decides que algunos sean privados (ej. personajes), agrégalos al set `EDIFICIOS_PRIVADOS`. Si son públicos, no los agregues.

Sugerencia:
- `characters` → **privados** (necesitan permiso del comisionado)
- `lunar_flora` → **públicos** (decoración natural, como decorations)
- `infrastructure` → **públicos** (como roads)

## TAREA 6: Arreglar overlay de resumen de turno que no se muestra

### 🔍 El problema

En `Simmoon_arc/juego_simmoon.py`, método `manejar_eventos()`:

**Bug 1 — El flag se apaga antes de renderizar (línea 3709):**
```python
elif self.mostrando_resumen:
    self.mostrando_resumen = False   # ← BUG: lo apaga INMEDIATAMENTE
```
Cuando el jugador presiona ESPACIO, `procesar_siguiente_turno()` pone `self.mostrando_resumen = True`. Pero en el siguiente frame, `manejar_eventos()` entra al `elif` y **lo vuelve a False** antes de que `renderizar()` (línea 4913) pueda verlo. El overlay nunca se pinta.

**Bug 2 — Llamada duplicada a `procesar_siguiente_turno()` (líneas 3839-3842):**
```python
if not self.mostrando_resumen:
    self.procesar_siguiente_turno()   # ← llama 1 vez (solo si NO resumen)

self.procesar_siguiente_turno()       # ← llama SIEMPRE, 2da vez
```
El turno avanza dos veces por cada ESPACIO.

### ✅ El fix

**Fix 1 — Mover `self.mostrando_resumen = False` al botón CERRAR (línea 3709 → eliminarlo):**

Busca estas líneas en `manejar_eventos()`:
```
3707         elif self.mostrando_resumen:
3708
3709             self.mostrando_resumen = False
3710
3711             if self.mostrando_permiso:
```

**ELIMINA la línea 3709.** El flag `mostrando_resumen` solo debe ponerse a `False` cuando:
- El jugador hace click en el botón CERRAR (ya está en línea ~3747, esa se queda)
- El jugador presiona ESC (ya está manejado fuera del elif, en ~3685)

**Fix 2 — Eliminar la llamada duplicada (quitar línea 3842, mantener el guard):**

Busca estas líneas:
```
3839                         if not self.mostrando_resumen:
3840                             self.procesar_siguiente_turno()
3841 
3842                         self.procesar_siguiente_turno()
```

**ELIMINA la línea 3842** (la llamada incondicional). **MANTÉN las líneas 3839-3840** (el guard `if not self.mostrando_resumen`). El resultado debe ser:
```python
                        if not self.mostrando_resumen:
                            self.procesar_siguiente_turno()
```

El guard es importante: evita que ESPACIO avance el turno mientras el overlay está visible.

### Resultado esperado

1. Presionas ESPACIO → `procesar_siguiente_turno()` calcula recursos y pone `mostrando_resumen = True`
2. El frame renderiza → `renderizar()` ve `mostrando_resumen = True` → pinta `renderizar_overlay_resumen()` ✅
3. Ves el overlay con ingresos, gastos, eventos, cambio poblacional
4. ESPACIO **no funciona mientras el overlay está abierto** (el guard lo bloquea) ✅
5. Clickeas CERRAR o presionas ESC → `mostrando_resumen = False` → el overlay desaparece
6. ESPACIO vuelve a funcionar → avanza el siguiente turno, una sola vez

---

## TAREA 7: Selector visual de edificios por categoría (grid 3 columnas con sprites 64×64)

### 🎯 Qué hay ahora

El método `renderizar_panel()` en `Simmoon_arc/renderizador.py` muestra los edificios como una **lista vertical** (líneas ~642-700):
```
┌──────────────────────────────┐
│ 🖼️ Nombre edificio           │
│ 🖼️ Nombre edificio           │
│ 🖼️ Nombre edificio           │
│ ...                          │
└──────────────────────────────┘
```
Cada item ocupa 298×42px con sprite de 32×32.

### 🎯 Qué hay que hacer

Reemplazar esa lista vertical por un **grid visual de 3 columnas**, tipo SimCity 2000 / constructor:
```
┌──────────────────────────────┐
│ ┌─────┐ ┌─────┐ ┌─────┐     │
│ │🖼️  │ │🖼️  │ │🖼️  │     │  ← 64×64 sprites
│ │Nom  │ │Nom  │ │Nom  │     │  ← nombre
│ │500💰│ │300💰│ │800💰│     │  ← coste
│ └─────┘ └─────┘ └─────┘     │
│ ┌─────┐ ┌─────┐ ┌─────┐     │
│ │🖼️  │ │🖼️  │ │...  │     │
│ │  ...│ │  ...│ │     │     │
│ └─────┘ └─────┘ └─────┘     │
│   ▼ scroll si hay más       │
├──────────────────────────────┤
│     [⏩ SIGUIENTE TURNO]     │
└──────────────────────────────┘
```

### 📐 Dimensiones exactas

El panel derecho mide **320px de ancho**. Con margen de 10px:
- Ancho disponible: **300px** (`margen` a `panel_x + 300`)
- 3 columnas de **96px** cada una = 288px (sobran 12px para gaps de 4px entre columnas)
- Cada celda: **96px ancho × 96px alto**
- Sprite dentro: **64×64px centrado** en la celda
- Texto nombre: **fuente_pequenia (18px)** centrado debajo del sprite
- Texto coste: **fuente_pequenia** en amarillo, centrado debajo del nombre

### 🔧 Código a reemplazar (líneas ~654-706)

Busca esta sección en `renderizador.py` dentro del método `renderizar_panel()`:

```python
        # Scroll: altura disponible para edificios

        altura_disponible = pantalla.get_height() - y_offset - 75

        for tipo in edificios_categoria:
            ...  # ← TODO ESTE BLOQUE se reemplaza
```

**Reemplázala** por el siguiente bloque ÚNICO que incluye grid + scroll indicator:

```python
        # ── Grid visual de edificios (3 columnas) ──
        Config = _from_game('Config')  # atajo local (opcional)
        COLUMNAS = 3
        CELDA_W = 96
        CELDA_H = 96
        GAP_X = 4
        GAP_Y = 6

        total = len(edificios_categoria)
        renderizados = 0

        for i, tipo in enumerate(edificios_categoria):
            fila = i // COLUMNAS
            col = i % COLUMNAS

            celda_x = margen + col * (CELDA_W + GAP_X)
            celda_y = y_offset + fila * (CELDA_H + GAP_Y)

            # Si se sale del panel, cortar
            if celda_y + CELDA_H > pantalla.get_height() - 60:
                break

            renderizados += 1
            rect_celda = pygame.Rect(celda_x, celda_y, CELDA_W, CELDA_H)

            # Color de fondo
            seleccionado = edificio_seleccionado and edificio_seleccionado.id == tipo.id
            if seleccionado:
                color_fondo = Config.COLOR_BOTON_SELECCIONADO
            elif rect_celda.collidepoint(mouse_rel_x, mouse_rel_y):
                color_fondo = Config.COLOR_BOTON_HOVER
                if mouse_click:
                    edificio_clickeado = tipo.id
            else:
                color_fondo = Config.COLOR_BOTON

            pygame.draw.rect(pantalla, color_fondo, rect_celda, border_radius=6)

            # Sprite 64x64 centrado
            sprite = self.cargar_sprite(tipo.ruta_sprite, (64, 64))
            sprite_x = celda_x + (CELDA_W - 64) // 2
            sprite_y = celda_y + 4
            pantalla.blit(sprite, (sprite_x, sprite_y))

            # Nombre
            txt_nombre = self.fuente_pequenia.render(tipo.nombre, True, Config.COLOR_TEXTO)
            txt_x = celda_x + (CELDA_W - txt_nombre.get_width()) // 2
            pantalla.blit(txt_nombre, (txt_x, sprite_y + 64 + 2))

            # Coste (más estrellas si aplica)
            estrellas = votos.get(tipo.id, 0)
            info_cost = f"💰{tipo.costo}" if estrellas == 0 else f"💰{tipo.costo} ⭐{estrellas}"
            txt_coste = self.fuente_pequenia.render(info_cost, True, Config.COLOR_TEXTO_AMARILLO)
            coste_x = celda_x + (CELDA_W - txt_coste.get_width()) // 2
            pantalla.blit(txt_coste, (coste_x, sprite_y + 64 + 18))

            # Etiqueta privado (esquina superior derecha)
            if _from_game('es_edificio_privado')(tipo.id):
                txt_priv = self.fuente_pequenia.render("📋", True, (255, 180, 50))
                pantalla.blit(txt_priv, (celda_x + CELDA_W - 24, celda_y + 2))

        # ── Indicador de scroll si hay más ──
        if renderizados < total and renderizados > 0:
            restantes = total - renderizados
            txt_mas = self.fuente_pequenia.render(f"▼ {restantes} más...", True, Config.COLOR_TEXTO_AMARILLO)
            mas_x = margen + (300 - txt_mas.get_width()) // 2
            ult_fila = (renderizados - 1) // COLUMNAS
            mas_y = y_offset + (ult_fila + 1) * (CELDA_H + GAP_Y) + 4
            pantalla.blit(txt_mas, (mas_x, mas_y))
            y_offset = mas_y + 25
        elif renderizados > 0:
            total_filas = (total + COLUMNAS - 1) // COLUMNAS
            y_offset += total_filas * (CELDA_H + GAP_Y) + 10
```

### 🔍 Detalles de diseño

1. **Hover**: La celda completa se ilumina al pasar el mouse (mismo color que antes)
2. **Selección**: La celda del edificio seleccionado se marca con `COLOR_BOTON_SELECCIONADO`
3. **Estrellas**: Se mantiene la visualización de votos junto al coste (igual que la lista anterior)
4. **Tooltip**: Opcional — al hacer hover sobre una celda, mostrar descripción breve del edificio en la parte baja del panel
5. **Etiqueta Privado**: "📋" pequeño en la esquina superior derecha de la celda para edificios privados
6. **Sin edificios**: Mantener los mensajes de "sin edificios" que ya existen (universities → zonificar, privados → zonificar, etc.) — esos van ANTES del grid, en el `if not edificios_categoria:` existente

### ✅ Recordatorio importante

El método `renderizar_panel()` retorna `(edificio_id, categoria, click_turno)`. El grid debe seguir retornando el `edificio_clickeado` de la misma forma. No cambies la firma del método ni el tipo de retorno.

### 📐 Nota de dimensiones

El panel derecho mide 320px. Margen izquierdo = 10px. Ancho disponible = 310px (de `margen` a `panel_x + 310`).
- 3 columnas × 96px = 288px
- 2 gaps de 4px entre columnas = 8px
- Total = 296px → sobran 14px (distribuibles como margen extra a la derecha)

---

## ✅ Cómo verificar que todo funcionó

### Tareas 1-5 (categorías nuevas)
1. **Sintaxis**: `python -c "import py_compile; py_compile.compile('game_config.py', doraise=True); print('OK')"`
2. **Panel visible**: Al lanzar el juego con `python juego_simmoon.py`, las 3 categorías deben aparecer en el panel lateral
3. **Sprites cargados**: Al hacer clic en la categoría, deben aparecer los edificios con sus sprites (el sistema de `cargar_sprite()` ya busca en `postproc/` automáticamente)
4. **Minimapa**: Los edificios colocados deben mostrar el color correcto en el minimapa

### Tarea 6 (overlay resumen)
1. **Sintaxis**: `python -c "import py_compile; py_compile.compile('juego_simmoon.py', doraise=True); print('OK')"`
2. **En juego**: Presiona ESPACIO → debe aparecer el overlay de resumen con ingresos, gastos, eventos ✅
3. **Cerrar**: Click en CERRAR o ESC → el overlay debe desaparecer y el turno avanza normal
4. **Un solo turno**: Cada ESPACIO debe avanzar exactamente 1 turno (no 2)
