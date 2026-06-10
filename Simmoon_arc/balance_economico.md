# ⚖️ Balance Económico — Negocios e Industria vs Alojamiento

> Fecha: 2026-06-09
> Propósito: Comparar ROI de todas las categorías que generan ingresos por alquiler para detectar desbalances.

---

## 📊 Tabla de ROI — Negocios (businesses)

| # | Edificio | ID | Costo | Alquiler | Mant. | Neto/t | Tiles | $/tile | ROI | Felicidad | Empleos |
|---|----------|----|------:|--------:|------:|------:|------:|-------:|----:|:---------:|:-------:|
| 1 | 🏪 Almacén | biz_12 | 250 | 25 | 3 | **+22** | 2×1 | 125 | **11t** 🏆 | 0 | 2 |
| 2 | 🏨 Hotel Lunar | biz_03 | 800 | 50 | 15 | **+35** | 2×1 | 400 | **23t** | 0 | 10 |
| 3 | 🏦 Banco Lunar | biz_10 | 600 | 30 | 5 | **+25** | 1×1 | 600 | **24t** | 0 | 4 |
| 4 | 🛒 Tienda Lunar | biz_11 | 300 | 15 | 3 | **+12** | 1×1 | 300 | **25t** | 0 | 3 |
| 5 | 🤝 Puesto Comercial | biz_02 | 400 | 20 | 5 | **+15** | 1×1 | 400 | **27t** | 0 | 5 |
| 6 | 🍽️ Restaurante Lunar | biz_04 | 350 | 20 | 8 | **+12** | 1×1 | 350 | **29t** | +8 😊 | 6 |
| 7 | 🚀 Terminal Espacial | biz_07 | 2000 | 80 | 30 | **+50** | 3×2 | 333 | **40t** | 0 | 20 |
| 8 | 🏭 Fábrica | biz_08 | 1500 | 35 | 25 | **+10** | 2×2 | 375 | **150t** ❌ | 0 | 15 |

## 📊 Tabla de ROI — Industria (industry)

| # | Edificio | ID | Costo | Alquiler | Mant. | Neto/t | Tiles | $/tile | ROI |
|---|----------|----|------:|--------:|------:|------:|------:|-------:|----:|
| 1 | 🚢 Puerto de Exportación | ind_04 | 2500 | 120 | 30 | **+90** | 3×2 | 417 | **28t** 🏆 |
| 2 | 🔬 Lab. de Helio-3 | ind_03 | 2000 | 90 | 25 | **+65** | 2×2 | 500 | **31t** |
| 3 | 🔥 Fundición de Regolito | ind_01 | 1400 | 40 | 20 | **+20** | 2×2 | 350 | **70t** ❌ |
| 4 | 🖨️ Fábrica Impresión 3D | ind_02 | 1200 | 35 | 18 | **+17** | 2×2 | 300 | **71t** ❌ |

## 📊 Tabla Comparativa — Alojamiento (referencia)

| # | Edificio | ROI | Neto/t | $/tile | Empleos |
|---|----------|----:|-------:|-------:|:-------:|
| 1 | 🏢 Albergue Central (misc_01) | **22t** 🏆 | +20 | 112 | 2 |
| 2 | 🏛️ Complejo Albergues (site_08) | **22t** 🏆 | +37 | 50 | 5 |
| 3 | 🏗️ Albergue Subterráneo (hou_04) | **23t** | +31 | 117 | 2 |
| 4 | 🏨 Hotel Cúpula Lujo (hou_03) | **24t** | +82 | 500 | 8 |
| 5 | 🛏️ Albergue Básico (hou_01) | **25t** | +12 | 300 | 0 |
| 6 | 🏘️ Albergue Comunitario (hou_02) | **29t** | +17 | 250 | 0 |

---

## 🔍 Hallazgos Clave

### 🟢 Bien Balanceados (ROI 22-31t)
| Edificio | ROI | Categoría |
|----------|----:|-----------|
| Almacén (biz_12) | **11t** ⚡ | Negocios (demasiado rápido) |
| Albergue Central (misc_01) | **22t** | Alojamiento |
| Complejo Albergues (site_08) | **22t** | Alojamiento |
| Hotel Lunar (biz_03) | **23t** | Negocios |
| Albergue Subterráneo (hou_04) | **23t** | Alojamiento |
| Hotel Cúpula Lujo (hou_03) | **24t** | Alojamiento (Comercial) |
| Banco Lunar (biz_10) | **24t** | Negocios |
| Albergue Básico (hou_01) | **25t** | Alojamiento |
| Tienda Lunar (biz_11) | **25t** | Negocios |
| Puesto Comercial (biz_02) | **27t** | Negocios |
| Puerto Exportación (ind_04) | **28t** | Industria |
| Restaurante Lunar (biz_04) | **29t** | Negocios |
| Albergue Comunitario (hou_02) | **29t** | Alojamiento |
| Lab. Helio-3 (ind_03) | **31t** | Industria |

### 🔴 Desbalanceados (ROI > 40t)
| Edificio | ROI | Problema |
|----------|----:|----------|
| Terminal Espacial (biz_07) | **40t** | Lento — alquiler 80 para costo 2000 |
| Fundición Regolito (ind_01) | **70t** ❌ | Pésimo — alquiler 40, costo 1400 |
| Fábrica Impresión 3D (ind_02) | **71t** ❌ | Pésimo — alquiler 35, costo 1200 |
| Fábrica (biz_08) | **150t** ❌❌ | Pésimo — alquiler 35, costo 1500, -20 energía |

### ⚡ Caso Atípico
| Edificio | ROI | Nota |
|----------|----:|------|
| Almacén (biz_12) | **11t** | ROI extremadamente rápido — costo 250, alquiler 25, 2×1 tiles |

---

## ✅ Cambios Aplicados (2026-06-09)

| # | Edificio | Cambio | ROI Anterior | ROI Nuevo | Estado |
|---|----------|--------|:------------:|:---------:|:------:|
| 1 | **biz_08** (Fábrica) | alquiler 35→**60** | 150t | ~43t | ✅ Aplicado |
| 2 | **ind_01** (Fundición) | alquiler 40→**80** | 70t | ~23t | ✅ Aplicado |
| 3 | **ind_02** (Impresión 3D) | alquiler 35→**65** | 71t | ~26t | ✅ Aplicado |

## 📈 Recomendaciones Pendientes

| # | Edificio | Cambio Sugerido | ROI Actual | Motivo |
|---|----------|-----------------|:----------:|--------|
| 4 | **biz_07** (Terminal) | alquiler 80→**120** | 40t | Puerto espacial debe generar más |
| 5 | **biz_12** (Almacén) | alquiler 25→**15** (opcional) | 11t | ROI muy rápido — quizás está bien por ser pequeño |

---

## 📊 Resumen por Zona

| Zona | ROI Promedio* | Mejor ROI | Peor ROI | Salud |
|------|:-----------:|:---------:|:--------:|:-----:|
| 🏠 **Alojamiento** | **24t** | 22t | 29t | ✅ Excelente |
| 🏢 **Comercial** | **41t** | 11t | 150t | ⚠️ Desbalanceado |
| 🏭 **Industrial** | **50t** | 28t | 71t | 🔴 Necesita ajustes |

> *Promedio excluyendo el Almacén (biz_12) por ser caso atípico.
>
> **Conclusión:** La zona Industrial necesita rebalance urgente (ind_01 e ind_02). La Fábrica (biz_08, ROI 150t) es inviable. El Alojamiento está perfectamente balanceado como referencia.

---

*Documento generado: 2026-06-09*
*Basado en datos extraídos de `juego_simmoon.py`*
