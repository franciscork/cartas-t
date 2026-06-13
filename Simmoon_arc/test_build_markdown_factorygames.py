#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_build_markdown_factorygames.py — Tests unitarios para `build_markdown()`
de Simmoon_arc/_cargar_factorygames_texto.py.

Cubre:
  1. Frontmatter YAML válido (parseable, con todos los campos requeridos)
  2. Conteo correcto de caracteres, líneas y palabras
  3. Fence de 4-backticks (no 3) para evitar inyección
  4. Contenido NO se trunca en archivos grandes (>100KB)
  5. Comportamiento ante BOM (debe strippearse)
  6. Idempotencia estructural (mismo input → misma forma de output)

Ejecutar:
    cd Simmoon_arc
    PYTHONIOENCODING=utf-8 python -m unittest test_build_markdown_factorygames -v
"""
import os
import re
import sys
import unittest
from pathlib import Path

# Parsing de YAML: PyYAML es opcional. Si no está, usamos parsing ligero
# a nivel de strings (los tests de frontmatter estructural no requieren YAML
# estricto, sólo presencia/forma de los campos).
try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from _cargar_factorygames_texto import build_markdown  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────────
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _extract_frontmatter(md: str) -> str:
    """Extrae el bloque YAML del frontmatter (entre los dos `---`)."""
    m = _FRONTMATTER_RE.search(md)
    if not m:
        raise AssertionError(
            f"No se encontró frontmatter YAML (formato '---...---'). "
            f"Primeros 50 chars: {md[:50]!r}"
        )
    return m.group(1)


def _extract_fenced_content(md: str) -> str:
    """Extrae el contenido dentro de la fence 4-backticks (si existe)."""
    # Buscar la primera línea de 4+ backticks consecutivos y la siguiente
    # línea con la MISMA cantidad de backticks.
    pattern = re.compile(r"^(`{4,})\s*$\n(.*?)\n^\1\s*$",
                         re.DOTALL | re.MULTILINE)
    m = pattern.search(md)
    if not m:
        raise AssertionError(
            f"No se encontró fence 4-backticks. md[:300]={md[:300]!r}"
        )
    return m.group(2), len(m.group(1))


# ── Tests ──────────────────────────────────────────────────────────────────
class TestFrontmatter(unittest.TestCase):
    """Verifica que el frontmatter es válido y contiene los campos requeridos."""

    # Campos que DEBEN estar presentes en el frontmatter
    REQUIRED_FIELDS = {
        "title", "date", "tags", "importance", "empresa", "version",
        "tipo", "archivo_adjunto", "caracteres", "lineas", "palabras",
        "idioma", "cargado_por",
    }

    def setUp(self):
        self.md, _, _, _ = build_markdown("Hola mundo.\nEsto es un test.")

    def test_frontmatter_block_exists(self):
        """El markdown debe empezar con `---` y tener un cierre `---`."""
        self.assertTrue(self.md.startswith("---\n"),
                        f"md no empieza con '---\\n': {self.md[:20]!r}")
        fm = _extract_frontmatter(self.md)
        self.assertGreater(len(fm), 0, "Frontmatter vacío")

    def test_frontmatter_yaml_is_parseable(self):
        """Si PyYAML está disponible, el frontmatter debe ser YAML válido."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible; skip YAML strict parse")
        fm = _extract_frontmatter(self.md)
        parsed = yaml.safe_load(fm)
        self.assertIsInstance(parsed, dict,
                              f"YAML parseó a {type(parsed)}, esperado dict")

    def test_frontmatter_has_all_required_fields(self):
        """Todos los campos requeridos deben estar presentes."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible; skip field check por YAML")
        fm = _extract_frontmatter(self.md)
        parsed = yaml.safe_load(fm)
        for field in self.REQUIRED_FIELDS:
            self.assertIn(field, parsed,
                          f"Campo requerido '{field}' falta en frontmatter")

    def test_frontmatter_required_fields_present_via_grep(self):
        """Versión sin PyYAML: verificar que cada campo aparece en el FM."""
        fm = _extract_frontmatter(self.md)
        for field in self.REQUIRED_FIELDS:
            # Buscar `field:` como clave YAML (no como substring dentro de un valor).
            # MULTILINE para que ^ matchee inicio de cada línea, no sólo de la primera.
            pattern = re.compile(rf"^{re.escape(field)}\s*:", re.MULTILINE)
            self.assertIsNotNone(
                pattern.search(fm),
                f"Campo '{field}:' no aparece como clave en frontmatter",
            )

    def test_title_is_correct(self):
        """El title debe ser 'FactoryGames — Estudio (Texto Fundador)'."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(self.md))
        self.assertIn("FactoryGames", parsed["title"])
        self.assertIn("Texto Fundador", parsed["title"])

    def test_tags_is_list_with_expected_count(self):
        """tags debe ser una lista con al menos 5 elementos."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(self.md))
        self.assertIsInstance(parsed["tags"], list)
        self.assertGreaterEqual(len(parsed["tags"]), 5)
        self.assertIn("factorygames", parsed["tags"])
        self.assertIn("fundacional", parsed["tags"])

    def test_importance_is_int_and_high(self):
        """importance debe ser 5 (documento fundacional)."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(self.md))
        self.assertEqual(parsed["importance"], 5)

    def test_empresa_field(self):
        """empresa debe ser 'FactoryGames'."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(self.md))
        self.assertEqual(parsed["empresa"], "FactoryGames")

    def test_date_is_today(self):
        """date debe ser la fecha de hoy (YYYY-MM-DD)."""
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(self.md))
        from datetime import datetime, timedelta
        # parsed["date"] es datetime.date; comparar como string.
        # Tolerar midnight roll: aceptar hoy, ayer o mañana.
        today = datetime.now().date()
        allowed = {
            (today).isoformat(),
            (today + timedelta(days=1)).isoformat(),
            (today - timedelta(days=1)).isoformat(),
        }
        # Coerce datetime.date a ISO string si aplica
        date_str = (parsed["date"].isoformat()
                    if hasattr(parsed["date"], "isoformat")
                    else str(parsed["date"]))
        self.assertIn(date_str, allowed,
                      f"date {date_str!r} no está cerca de hoy {today.isoformat()}")


class TestCounters(unittest.TestCase):
    """Verifica que el conteo de chars/lines/words es correcto."""

    def test_counts_simple_text(self):
        """Texto simple: contar correctamente."""
        content = "Hola mundo.\nEsto es un test.\nTres líneas."
        md, n_chars, n_lines, n_words = build_markdown(content)
        self.assertEqual(n_chars, len(content))
        self.assertEqual(n_lines, 3)
        # "Hola mundo. Esto es un test. Tres líneas." → 8 words
        self.assertEqual(n_words, 8)

    def test_counts_no_trailing_newline(self):
        """Archivo SIN newline final: splitlines() NO debe contar línea extra."""
        content = "linea1\nlinea2\nlinea3"  # sin \n al final
        md, n_chars, n_lines, n_words = build_markdown(content)
        self.assertEqual(n_chars, len(content))
        # splitlines() cuenta las 3 líneas reales (no añade una
        # "línea vacía" extra por la ausencia de \n final).
        self.assertEqual(n_lines, 3,
                         "splitlines() no debe contar línea vacía post-EOF")

    def test_counts_with_trailing_newline(self):
        """Archivo CON newline final: splitlines() debe contar correctamente."""
        content = "linea1\nlinea2\nlinea3\n"
        md, n_chars, n_lines, n_words = build_markdown(content)
        self.assertEqual(n_chars, len(content))
        self.assertEqual(n_lines, 3)  # splitlines() cuenta 3 (no 4)

    def test_counts_empty_string(self):
        """String vacío: chars=0, lines=0, words=0."""
        md, n_chars, n_lines, n_words = build_markdown("")
        self.assertEqual(n_chars, 0)
        self.assertEqual(n_lines, 0)
        self.assertEqual(n_words, 0)

    def test_counts_match_frontmatter(self):
        """Los counts en frontmatter deben coincidir con los retornados."""
        content = "Uno dos tres.\nCuatro cinco seis siete."
        md, n_chars, n_lines, n_words = build_markdown(content)
        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(md))
        self.assertEqual(parsed["caracteres"], n_chars)
        self.assertEqual(parsed["lineas"], n_lines)
        self.assertEqual(parsed["palabras"], n_words)

    def test_word_count_uses_split(self):
        """El word count usa str.split() (cualquier whitespace, no solo espacio)."""
        content = "palabra1   palabra2\tpalabra3\npalabra4"
        md, n_chars, n_lines, n_words = build_markdown(content)
        # 4 palabras separadas por espacios/tab/newline
        self.assertEqual(n_words, 4)

    def test_bom_is_stripped(self):
        """El BOM (\ufeff) al inicio debe ser eliminado antes de contar."""
        content_with_bom = "\ufeffHola mundo."
        content_without_bom = "Hola mundo."
        md1, c1, _, _ = build_markdown(content_with_bom)
        md2, c2, _, _ = build_markdown(content_without_bom)
        # El BOM no debe contar como carácter
        self.assertEqual(c1, c2)
        self.assertEqual(c1, len("Hola mundo."))

    def test_multibyte_chars_counted_correctly(self):
        """Caracteres multibyte (UTF-8 español) cuentan como 1 carácter Python."""
        content = "Mañana será otro día. Año 2026. ñoño."
        md, n_chars, _, n_words = build_markdown(content)
        self.assertEqual(n_chars, len(content))  # len() cuenta code points
        # Verificar que el contenido completo está en el markdown
        self.assertIn(content, md)


class TestFence(unittest.TestCase):
    """Verifica que la fence es de 4-backticks (anti-inyección)."""

    def test_fence_is_4_backticks(self):
        """La fence DEBE ser de 4 backticks, no 3."""
        content = "Texto con ``` triple backticks dentro"
        md, _, _, _ = build_markdown(content)
        content_in_fence, fence_len = _extract_fenced_content(md)
        self.assertEqual(fence_len, 4,
                         f"Fence debe ser 4 backticks, got {fence_len}")
        self.assertEqual(content_in_fence, content)

    def test_content_with_triple_backticks_does_not_break_fence(self):
        """Si el TXT contiene ``` (3 backticks), la fence de 4 NO se rompe."""
        content = (
            "Aquí hay un bloque de código:\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
            "Y aquí sigue el texto normal."
        )
        md, _, _, _ = build_markdown(content)
        # El markdown debe seguir siendo parseable
        # (la fence de 4 envuelve correctamente)
        content_in_fence, fence_len = _extract_fenced_content(md)
        self.assertEqual(fence_len, 4)
        # El contenido extraído debe incluir los ``` internos intactos
        self.assertIn("```python", content_in_fence)
        self.assertIn("print('hello')", content_in_fence)

    def test_fence_opens_and_closes_match(self):
        """El conteo de líneas de fence (apertura + cierre) debe ser par."""
        content = "cualquier contenido"
        md, _, _, _ = build_markdown(content)
        # Contar líneas que son SOLO 4+ backticks
        fence_lines = [
            line for line in md.split("\n")
            if re.match(r"^`{4,}\s*$", line)
        ]
        self.assertGreaterEqual(len(fence_lines), 2,
                                f"Debe haber al menos apertura + cierre: "
                                f"got {len(fence_lines)} fence lines")
        self.assertEqual(len(fence_lines) % 2, 0,
                         f"Fence lines debe ser par: got {len(fence_lines)}")


class TestLargeContent(unittest.TestCase):
    """Verifica que el contenido NO se trunca en archivos grandes."""

    # El test de 1MB es opt-in (decorador más abajo). Por defecto se
    # skippea para mantener el suite rápido. Activar con `RUN_SLOW_TESTS=1`.

    @unittest.skipUnless(
        bool(os.environ.get("RUN_SLOW_TESTS")),
        "1MB stress test (opt-in via RUN_SLOW_TESTS=1)",
    )
    def test_extreme_content_1mb(self):
        """1MB: verificar que se maneja sin truncación ni crash."""
        chunk = "0123456789" * 100  # 1KB
        content = (chunk + "\n") * 1024  # ~1MB
        self.assertGreater(len(content), 1_000_000)

        md, n_chars, n_lines, n_words = build_markdown(content)

        # Verificar que NO se truncó
        self.assertEqual(n_chars, len(content))
        # El markdown final debe ser > 1MB
        self.assertGreater(len(md), 1_000_000)

    def test_content_100kb_not_truncated(self):
        """100KB de contenido: el markdown debe incluir TODO el input."""
        # Generar ~100KB de texto (100 líneas de ~1KB cada una)
        line = "x" * 1000 + "\n"
        content = line * 100  # 100,100 bytes aprox
        self.assertGreater(len(content), 100_000)

        md, n_chars, n_lines, n_words = build_markdown(content)

        # El retorno de n_chars debe ser exactamente len(content)
        self.assertEqual(n_chars, len(content))
        # El contenido debe estar ÍNTEGRO en el markdown
        self.assertIn(content, md,
                      "Contenido de 100KB debe estar completo en el markdown")
        # El markdown final debe ser > 100KB (frontmatter + body + estructura)
        self.assertGreater(len(md), 100_000)

    def test_content_150kb_not_truncated(self):
        """150KB: verificar que el markdown contiene TODO el input."""
        # Generar 150KB de texto variado
        chunk = "abcdefghij" * 100 + "\n"  # ~1KB
        content = chunk * 150  # ~150KB
        self.assertGreater(len(content), 150_000)

        md, n_chars, n_lines, n_words = build_markdown(content)

        self.assertEqual(n_chars, len(content))
        self.assertIn(content, md,
                      "Contenido de 150KB debe estar completo en el markdown")

    def test_large_content_counts_in_frontmatter(self):
        """Para 100KB, el campo 'caracteres' del frontmatter debe ser exacto."""
        line = "línea de prueba " * 50 + "\n"  # ~700 bytes
        content = line * 150  # ~105KB
        self.assertGreater(len(content), 100_000)

        md, n_chars, _, _ = build_markdown(content)

        if not _HAS_YAML:
            self.skipTest("PyYAML no disponible")
        parsed = yaml.safe_load(_extract_frontmatter(md))
        self.assertEqual(parsed["caracteres"], n_chars)
        self.assertEqual(parsed["caracteres"], len(content))

class TestStructuralIdempotence(unittest.TestCase):
    """Verifica la forma del output (estructura, no contenido)."""

    def test_md_starts_with_frontmatter(self):
        """El markdown debe empezar con el bloque frontmatter."""
        md, _, _, _ = build_markdown("test")
        self.assertTrue(md.startswith("---\n"))

    def test_md_contains_title_h1(self):
        """El markdown debe tener un H1 con el emoji 🏭."""
        md, _, _, _ = build_markdown("test")
        self.assertIn("# 🏭", md)

    def test_md_has_archivo_adjunto_link(self):
        """Debe referenciar al TXT adjunto con un wikilink."""
        md, _, _, _ = build_markdown("test")
        self.assertIn("[[FactoryGames-Estudio-Texto-Fundador.txt]]", md)

    def test_md_has_pdf_link(self):
        """Debe referenciar al PDF resumen ejecutivo."""
        md, _, _, _ = build_markdown("test")
        self.assertIn("[[FactoryGames-Estudio-Concepto-v1.0.pdf]]", md)

    def test_return_type_is_tuple(self):
        """El retorno debe ser tuple[str, int, int, int]."""
        result = build_markdown("test")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        self.assertIsInstance(result[0], str)
        self.assertIsInstance(result[1], int)
        self.assertIsInstance(result[2], int)
        self.assertIsInstance(result[3], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
