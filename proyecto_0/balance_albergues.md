# ⚖️ Balance Económico — Albergues y Alojamiento

> Fecha: 2026-06-09
> Propósito: Registrar el análisis de ROI de todos los edificios de alojamiento para referencia futura y ajustes de balance.

---

## 📊 Tabla de ROI — Albergues + Hotel

| # | Edificio | ID | Costo | Alquiler | Mant. | Neto/t | Tiles | $/tile | ROI |
|---|----------|----|------:|--------:|------:|------:|------:|-------:|----:|
| 1 | 🛏️ Albergue Básico | hou_01 | 300 | 15 | 3 | **+12** | 1×1 | 300 | **25t** |
| 2 | 🏘️ Albergue Comunitario | hou_02 | 500 | 22 | 5 | **+17** | 2×1 | 250 | **29t** |
| 3 | 🏢 Albergue Central | misc_01 | 450 | 25 | 5 | **+20** | 2×2 | 112 | **22t** 🏆 |
| 4 | 🏗️ Albergue Subterráneo | hou_04 | 700 | 38 | 7 | **+31** | 3×2 | 117 | **23t** |
| 5 | 🏛️ Complejo de Albergues | site_08 | 800 | 45 | 8 | **+37** | 4×4 | 50 | **22t** |
| 6 | 🏨 Hotel Cúpula de Lujo | hou_03 | 2.000 | 100 | 18 | **+82** | 2×2 | 500 | **24t** |

> **Nota:** Neto/t = Alquiler − Mantenimiento. ROI = Costo ÷ Neto por turno. El ROI no incluye costo de recursos secundarios (energía, oxígeno, agua).

---

## 📈 Recursos por Edificio

| Edificio | Energía | Oxígeno | Agua | Felicidad | Empleos |
|----------|:-------:|:-------:|:----:|:---------:|:-------:|
| Albergue Básico | -2 | 0 | 0 | 0 | 0 |
| Albergue Comunitario | -4 | 0 | 0 | 0 | 0 |
| Albergue Central | -4 | 0 | 0 | 0 | 2 |
| Albergue Subterráneo | -6 | 0 | 0 | 0 | 2 |
| Complejo de Albergues | -6 | -3 | -3 | 0 | 5 |
| Hotel Cúpula de Lujo | -12 | -3 | -2 | +15 | 8 |

---

## 🏗️ Costo por Tile (eficiencia de espacio)

| Edificio | Tiles | Costo/tile | Alquiler/tile |
|----------|:----:|:----------:|:-------------:|
| Complejo de Albergues | 16 | **50** ✅✅✅ | 2.8 |
| Albergue Central | 4 | **112** ✅✅ | 6.2 |
| Albergue Subterráneo | 6 | **117** ✅✅ | 6.3 |
| Albergue Comunitario | 2 | **250** ✅ | 11.0 |
| Albergue Básico | 1 | **300** | 15.0 |
| Hotel Cúpula de Lujo | 4 | **500** | 25.0 |

> **Interpretación:** A más grande el edificio, más eficiente en $/tile. El Complejo de Albergues es el más eficiente (50 créditos/tile). El Hotel es el menos eficiente en espacio pero compensa con +15 felicidad y 8 empleos.

---

## 🏠 Zona Alojamiento

| Parámetro | Valor |
|-----------|-------|
| Nombre | Alojamiento |
| Categorías compatibles | hou_01, hou_02, hou_04, misc_01, site_08 |
| Alquiler mínimo | 8 |
| Alquiler máximo | 50 |
| Prima mínima | 60% |
| Prima máxima | 250% |
| Color | (70, 130, 180) |

> **Nota:** El Hotel (hou_03) está en zona **Comercial**, no en Alojamiento.

---

## 📝 Historial de Cambios

| Fecha | Edificio | Cambio | Motivo |
|------|----------|--------|--------|
| 2026-06-09 | hou_04 | alquiler 30→**38** | ROI muy lento (30t→23t) |
| 2026-06-09 | site_08 | alquiler 35→**45** | ROI muy lento (30t→22t) |
| 2026-06-09 | hou_03 | alquiler 120→**100** | Desbalanceado vs albergues (20t→24t) |

---

## 🔮 Próximos Ajustes Sugeridos

- [ ] Albergue Comunitario (hou_02): ROI 29t — el más lento de todos, considerar alquiler 22→25
- [ ] Comparar ROI con edificios de otras categorías (negocios, industria)
- [ ] Verificar que el costo de energía/oxígeno/agua no haga no rentable a ningún albergue
