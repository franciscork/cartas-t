#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
launch_validator.py
===================

Validador de scripts de lanzamiento del proyecto.

Escanea todos los scripts de inicio (*.sh, *.ps1, *.bat) ubicados en el
directorio padre (../) y verifica buenas practicas de robustez:

  * Presencia de shebang o cabecera valida (PowerShell, Batch, etc.).
  * Inclusion de `set -euo pipefail` en scripts bash (modo estricto).
  * Referencias a archivos que podrian no existir (ejecutables o scripts).
  * Uso de variables potencialmente sin definir (riesgo de unbound variable).
  * Tamano del script en lineas.

Genera un reporte en consola con colores ANSI y, ademas, persiste los
resultados en `launch_report.json` para su analisis posterior.

Uso:
    python launch_validator.py
    python3 launch_validator.py

No recibe argumentos: trabaja con rutas relativas al directorio actual.
"""

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable


# --- Configuracion ------------------------------------------------------------

# Directorio donde se buscan los scripts de lanzamiento.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent

# Patrones de archivos a validar.
EXTENSIONES = (".sh", ".ps1", ".bat", ".cmd")

# Archivo de salida con el reporte estructurado.
OUTPUT_JSON = Path(__file__).resolve().parent / "launch_report.json"

# Falsos positivos conocidos: referencias que parecen rotas pero son validas.
# - # (comentario), palabras sueltas del lenguaje, flags de PowerShell
# - venv/bin/python: siempre valido tras "cd $COMFYUI_DIR"
# - ~/ prefijos: se filtran aparte (referencias absolutas al home)
_FILTRO_FALSOS_POSITIVOS = {
    "#", "no", "como", "for", "from", "is", "with",
    "instance", "session", "assemblies", "agents",
    "processes", "Core", "ETW",
    "venv/bin/python",
    "generate.sh",  # verificado con [ -f ] en launch_all.sh
}

# Colores ANSI (se desactivan automaticamente si la salida no es un TTY).
COLOR_VERDE = "\033[92m"
COLOR_AMARILLO = "\033[93m"
COLOR_ROJO = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_GRIS = "\033[90m"
COLOR_NEGRITA = "\033[1m"
COLOR_RESET = "\033[0m"

USAR_COLOR = sys.stdout.isatty()


# --- Modelos de datos ---------------------------------------------------------

@dataclass
class ResultadoScript:
    """Representa el resultado del analisis de un script de lanzamiento."""

    nombre: str
    ruta: str
    tipo: str
    lineas: int
    tiene_shebang: bool
    shebang: str
    cabecera_valida: bool
    cabecera_detectada: str
    modo_estricto: bool
    issues: list[str] = field(default_factory=list)
    referencias_rotas: list[str] = field(default_factory=list)
    variables_sin_definir: list[str] = field(default_factory=list)

    @property
    def limpio(self) -> bool:
        """Devuelve True si el script no tiene issues criticos."""
        return len(self.issues) == 0


# --- Funciones de utilidad para color -----------------------------------------

def color(texto: str, codigo: str) -> str:
    """Aplica un codigo de color ANSI al texto si la salida es un TTY."""
    if not USAR_COLOR:
        return texto
    return f"{codigo}{texto}{COLOR_RESET}"


def verde(texto: str) -> str:
    return color(texto, COLOR_VERDE)


def amarillo(texto: str) -> str:
    return color(texto, COLOR_AMARILLO)


def rojo(texto: str) -> str:
    return color(texto, COLOR_ROJO)


def cyan(texto: str) -> str:
    return color(texto, COLOR_CYAN)


def gris(texto: str) -> str:
    return color(texto, COLOR_GRIS)


def negrita(texto: str) -> str:
    return color(texto, COLOR_NEGRITA)


# --- Deteccion de cabeceras y shebangs ---------------------------------------

SHEBANG_RE = re.compile(r"^#!\s*(.+?)\s*$")

# Cabeceras validas alternativas para scripts que no usan shebang.
POWERShell_CABECERA_RE = re.compile(r"^\s*#\s*Requires\s+-Version", re.IGNORECASE)
BATCH_CABECERA_RE = re.compile(r"^@echo\s+off", re.IGNORECASE)

# Modo estricto de bash.
STRICT_MODE_COMPLETO_RE = re.compile(r"set\s+-[a-zA-Z]*e[a-zA-Z]*u[a-zA-Z]*o", re.IGNORECASE)


# --- Deteccion de referencias a archivos -------------------------------------

# Captura llamadas tipo: python X.py, python3 X.py, bash X.sh, ./X.sh, .\\X.ps1, etc.
# Se limita a coincidencias razonables para reducir falsos positivos.
PATRONES_EJECUCION = [
    re.compile(r"(?:^|\s)(?:python3?|py)\s+([^\s|&;]+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:bash|sh|zsh)\s+([^\s|&;]+)", re.IGNORECASE),
    re.compile(r"(?:^|\s)\./([^\s|&;]+)"),
    re.compile(r"(?:^|\s)\.\\([^\s|&;]+)"),
    re.compile(r"(?:^|\s)(?:pwsh|powershell)(?:\.exe)?\s+(?:-File\s+)?([^\s|&;]+)", re.IGNORECASE),
]


def extraer_referencias(contenido: str) -> list[str]:
    """Devuelve la lista de archivos referenciados en comandos de ejecucion."""
    referencias: set[str] = set()
    for patron in PATRONES_EJECUCION:
        for match in patron.finditer(contenido):
            candidato = match.group(1).strip().strip('"').strip("'")
            # Ignorar redirecciones y patrones que no son archivos.
            if not candidato or candidato.startswith("-"):
                continue
            # Quitar posibles argumentos finales estilo script.py arg1
            candidato = candidato.split()[0] if " " in candidato else candidato
            referencias.add(candidato)
    return sorted(referencias)


def verificar_referencias(referencias: Iterable[str], base_dir: Path) -> list[str]:
    """Devuelve la lista de referencias que no existen en disco."""
    rotas: list[str] = []
    for ref in referencias:
        # Saltar URLs, variables de expansion, o pipes logicos.
        if any(token in ref for token in ("$", "%", ">", "<", "|", "*", "?")):
            continue
        # Quitar prefijos comunes.
        limpio = ref.lstrip("./").lstrip(".\\")
        if not limpio:
            continue
        # Comprobar en el directorio base, padre, Simmoon_arc, factory,
        # y directorios de instalacion comunes (ComfyUI, InvokeAI, etc.)
        # donde los scripts hacen "cd" antes de usar rutas relativas.
        homes = [Path.home()]
        candidatas = [
            base_dir / limpio,
            base_dir.parent / limpio,
            base_dir / "Simmoon_arc" / limpio,
            base_dir / "factory" / limpio,
        ]
        for h in homes:
            candidatas.extend([
                h / "ComfyUI" / limpio,
                h / "invokeai" / limpio,
                h / "OpenHuman" / limpio,
                h / "OpenJarvis" / limpio,
            ])
        if not any(c.exists() for c in candidatas):
            # Filtrar falsos positivos (definido una vez, no por referencia)
            if ref not in _FILTRO_FALSOS_POSITIVOS and not ref.startswith("~/"):
                rotas.append(ref)
    return rotas


# --- Deteccion de variables sin definir --------------------------------------

# Estilo bash: $VAR, ${VAR}
VARIABLE_BASH_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
# Estilo PowerShell: $env:VAR, $var
VARIABLE_PS_RE = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
# Estilo batch: %VAR%
VARIABLE_BATCH_RE = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")


def _leer_asignaciones_bash(contenido: str) -> set[str]:
    """Devuelve el conjunto de variables bash asignadas en el script."""
    asignadas: set[str] = set()
    # VAR=valor  o  export VAR=valor  (tambien detras de ; en la misma linea)
    patron = re.compile(r"(?:^|;)\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)
    for match in patron.finditer(contenido):
        asignadas.add(match.group(1))
    # Detectar declaraciones `local/declare/typeset/readonly var` y `var=valor`
    # (multiples vars por linea, con flags como -a -i -r -x -g -n -A)
    for linea in contenido.splitlines():
        if re.match(r'^\s*(?:local|declare|typeset|readonly)\s', linea):
            linea = linea.split('#')[0]  # quitar comentarios inline
            tokens = re.split(r'\s+', linea.strip())[1:]  # quitar 'local'
            for token in tokens:
                if token.startswith('-'):
                    continue
                var = token.split('=')[0].rstrip(';')
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', var):
                    asignadas.add(var)
    # Detectar variables de bucle `for var in ...`
    patron_for = re.compile(r"^\s*for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+", re.MULTILINE)
    for match in patron_for.finditer(contenido):
        asignadas.add(match.group(1))
    # Argumentos posicionales y variables magicas que damos por validas.
    asignadas.update({"BASH_SOURCE", "BASH_LINENO", "LINENO", "FUNCNAME", "RANDOM", "PPID", "PIDS"})
    return asignadas


def _leer_asignaciones_ps(contenido: str) -> set[str]:
    """Devuelve el conjunto de variables PowerShell asignadas en el script."""
    asignadas: set[str] = set()
    # $var = valor  o  param([string]$var)  o  [string]$var (en param())
    patron = re.compile(r"(?:^|;)\s*\$([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)
    for match in patron.finditer(contenido):
        asignadas.add(match.group(1))
    # Detectar parametros de funcion: param($var) o [string]$var en bloque param
    patron_param = re.compile(r"(?:param\s*\(|\[\w+\])\s*\$([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
    for match in patron_param.finditer(contenido):
        asignadas.add(match.group(1))
    # Variables automaticas de PowerShell que damos por validas.
    asignadas.update({"PSScriptRoot", "PSCommandPath", "MyInvocation", "args", "input", "_"})
    return asignadas


def detectar_variables_sin_definir(contenido: str, tipo: str) -> list[str]:
    """Detecta referencias a variables que parecen no estar asignadas."""
    if tipo == "sh":
        patron = VARIABLE_BASH_RE
        asignadas = _leer_asignaciones_bash(contenido)
    elif tipo == "ps1":
        patron = VARIABLE_PS_RE
        asignadas = _leer_asignaciones_ps(contenido)
    elif tipo in ("bat", "cmd"):
        patron = VARIABLE_BATCH_RE
        # En batch las variables se asignan con `set VAR=...`; sin embargo
        # %1..%9 son argumentos posicionales validos.
        asignadas = {f"{i}" for i in range(10)}
    else:
        return []

    # Variables de entorno y de un solo caracter que solemos ignorar.
    ignoradas = {
        "PATH", "HOME", "USER", "SHELL", "PWD", "LANG", "TERM", "HOSTNAME",
        "RANDOM", "LINENO", "SECONDS", "IFS", "PS4", "PS1", "PS2", "PS3",
        "BASH", "BASH_VERSION", "BASH_SOURCE", "BASH_LINENO", "FUNCNAME",
        "PPID", "UID", "EUID", "GROUPS", "OSTYPE", "MACHTYPE", "HOSTTYPE",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "@", "*", "#",
        "?", "-", "$", "!",
    }

    encontradas: set[str] = set()
    for match in patron.finditer(contenido):
        var = match.group(1)
        if var in ignoradas or var in asignadas:
            continue
        # Evitar capturar palabras que en realidad son flags de comandos.
        if var.lower() in {"true", "false", "null", "args", "input", "this"}:
            continue
        encontradas.add(var)

    return sorted(encontradas)


# --- Analisis principal de un script -----------------------------------------

def analizar_script(ruta: Path) -> ResultadoScript:
    """Analiza un script y devuelve un objeto ResultadoScript con los hallazgos."""
    tipo = ruta.suffix.lstrip(".").lower()
    nombre = ruta.name

    # Lectura tolerante: algunos archivos pueden tener una codificacion rara.
    try:
        contenido = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return ResultadoScript(
            nombre=nombre,
            ruta=str(ruta),
            tipo=tipo,
            lineas=0,
            tiene_shebang=False,
            shebang="",
            cabecera_valida=False,
            cabecera_detectada="",
            modo_estricto=False,
            issues=[f"No se pudo leer el archivo: {exc}"],
        )

    lineas = contenido.count("\n") + (0 if contenido.endswith("\n") else 1)
    lineas_texto = contenido.splitlines()
    primera_linea = lineas_texto[0] if lineas_texto else ""

    # Deteccion de shebang o cabecera valida.
    shebang_match = SHEBANG_RE.match(primera_linea)
    tiene_shebang = bool(shebang_match)
    shebang = shebang_match.group(1).strip() if shebang_match else ""

    cabecera_valida = False
    cabecera_detectada = ""

    if tiene_shebang:
        cabecera_valida = True
        cabecera_detectada = shebang
    elif tipo == "ps1" and any(POWERShell_CABECERA_RE.match(l) for l in lineas_texto[:5]):
        cabecera_valida = True
        cabecera_detectada = "PowerShell #Requires"
    elif tipo in ("bat", "cmd") and any(BATCH_CABECERA_RE.match(l) for l in lineas_texto[:3]):
        cabecera_valida = True
        cabecera_detectada = "@echo off"

    # Modo estricto solo tiene sentido en scripts bash.
    modo_estricto = False
    if tipo == "sh":
        modo_estricto = bool(STRICT_MODE_COMPLETO_RE.search(contenido))

    # Busqueda de issues.
    issues: list[str] = []

    if not cabecera_valida:
        issues.append("Sin shebang ni cabecera valida")

    if tipo == "sh" and not modo_estricto:
        issues.append("Falta `set -euo pipefail` (modo estricto)")

    # Verificar referencias a archivos.
    referencias = extraer_referencias(contenido)
    referencias_rotas = verificar_referencias(referencias, ruta.parent)
    for ref in referencias_rotas:
        issues.append(f"Referencia rota: {ref}")

    # Verificar variables sin definir.
    variables_sin_definir = detectar_variables_sin_definir(contenido, tipo)
    # Limitamos el reporte a las primeras cinco para no saturar la tabla.
    for var in variables_sin_definir[:5]:
        issues.append(f"Variable sin definir: ${var}")
    if len(variables_sin_definir) > 5:
        issues.append(f"... y {len(variables_sin_definir) - 5} variables mas")

    return ResultadoScript(
        nombre=nombre,
        ruta=str(ruta),
        tipo=tipo,
        lineas=lineas,
        tiene_shebang=tiene_shebang,
        shebang=shebang,
        cabecera_valida=cabecera_valida,
        cabecera_detectada=cabecera_detectada,
        modo_estricto=modo_estricto,
        issues=issues,
        referencias_rotas=referencias_rotas,
        variables_sin_definir=variables_sin_definir,
    )


# --- Recoleccion de scripts --------------------------------------------------

def listar_scripts(base_dir: Path) -> list[Path]:
    """Devuelve la lista de scripts de lanzamiento encontrados."""
    if not base_dir.exists():
        return []
    scripts: list[Path] = []
    for patron in ("*.sh", "*.ps1", "*.bat", "*.cmd"):
        for archivo in sorted(base_dir.glob(patron)):
            if archivo.is_file():
                scripts.append(archivo)
    return scripts


# --- Renderizado del reporte en consola --------------------------------------

def formatear_estado(resultado: ResultadoScript) -> str:
    """Devuelve un codigo de color segun la severidad de los issues."""
    tiene_referencias_rotas = any(i.startswith("Referencia rota") for i in resultado.issues)
    if tiene_referencias_rotas:
        return rojo("ERROR")
    if resultado.issues:
        return amarillo("WARN ")
    return verde("OK   ")


def renderizar_tabla(resultados: list[ResultadoScript]) -> str:
    """Genera la tabla con los resultados para imprimir en consola."""
    cabecera = (
        f"{'NOMBRE':<32} {'TIPO':<5} {'LINEAS':>7} "
        f"{'SHEBANG':<10} {'STRICT':<7} {'ISSUES':<6} ESTADO"
    )
    separador = "-" * len(cabecera)

    filas = [negrita(cabecera), gris(separador)]
    for r in resultados:
        nombre_corto = r.nombre if len(r.nombre) <= 32 else r.nombre[:29] + "..."
        shebang_txt = "si" if r.tiene_shebang else "no"
        strict_txt = "si" if r.modo_estricto else "-"
        issues_txt = str(len(r.issues))
        fila = (
            f"{nombre_corto:<32} {r.tipo:<5} {r.lineas:>7} "
            f"{shebang_txt:<10} {strict_txt:<7} {issues_txt:<6} "
        )
        filas.append(fila + formatear_estado(r))
    return "\n".join(filas)


def renderizar_resumen(resultados: list[ResultadoScript]) -> str:
    """Genera un resumen final con conteos de estado."""
    total = len(resultados)
    limpios = sum(1 for r in resultados if r.limpio)
    con_issues = total - limpios
    errores = sum(
        1 for r in resultados if any(i.startswith("Referencia rota") for i in r.issues)
    )
    warnings = con_issues - errores

    lineas = [
        "",
        negrita("RESUMEN"),
        gris("-" * 40),
        f"  Total de scripts : {cyan(str(total))}",
        f"  Limpios          : {verde(str(limpios))}",
        f"  Con advertencias : {amarillo(str(warnings))}",
        f"  Con errores      : {rojo(str(errores))}",
    ]
    return "\n".join(lineas)


# --- Persistencia en JSON ----------------------------------------------------

def guardar_reporte(resultados: list[ResultadoScript], destino: Path) -> None:
    """Guarda el reporte completo en formato JSON."""
    payload = {
        "directorio": str(SCRIPTS_DIR),
        "total_scripts": len(resultados),
        "scripts_limpios": sum(1 for r in resultados if r.limpio),
        "scripts_con_issues": sum(1 for r in resultados if not r.limpio),
        "scripts": [asdict(r) for r in resultados],
    }
    destino.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# --- Punto de entrada --------------------------------------------------------

def main() -> int:
    """Ejecuta el flujo completo de validacion y muestra el reporte."""
    print(negrita(cyan("VALIDADOR DE SCRIPTS DE LANZAMIENTO")))
    print(gris(f"Directorio analizado: {SCRIPTS_DIR}"))
    print(gris(f"Patrones: {', '.join(EXTENSIONES)}"))
    print()

    scripts = listar_scripts(SCRIPTS_DIR)
    if not scripts:
        print(amarillo("No se encontraron scripts de lanzamiento."))
        return 0

    resultados = [analizar_script(s) for s in scripts]

    print(renderizar_tabla(resultados))
    print(renderizar_resumen(resultados))
    print()

    # Detalle ampliado para scripts con issues.
    con_issues = [r for r in resultados if r.issues]
    if con_issues:
        print(negrita("DETALLE DE ISSUES"))
        print(gris("-" * 60))
        for r in con_issues:
            color_titulo = rojo if any(i.startswith("Referencia rota") for i in r.issues) else amarillo
            print(color_titulo(f"\n[{r.nombre}] ({r.tipo}, {r.lineas} lineas)"))
            for issue in r.issues:
                print(f"  - {issue}")
        print()

    # Persistencia en JSON.
    try:
        guardar_reporte(resultados, OUTPUT_JSON)
        print(verde(f"Reporte guardado en: {OUTPUT_JSON}"))
    except OSError as exc:
        print(rojo(f"No se pudo guardar el reporte JSON: {exc}"))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
