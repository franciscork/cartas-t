#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_save_main_factorygames.py — Tests para las funciones de I/O
(save_via_obsidian_memory y main) de ``_cargar_factorygames_texto.py``.

Cubre:
  * Ruta correcta en modo REST (POST/PUT a /vault/FactoryGames/...)
  * Ruta correcta en modo FS (escritura a ``vault/FactoryGames/...md``)
  * Manejo de errores (filesystem exception, rest_client returns False)
  * Idempotencia: re-ejecución sobre el mismo path no rompe
  * Argumentos CLI (--src, --vault, --skip-txt-copy)
  * Caso patológico: TXT fuente no existe → exit 1

Mocking strategy:
  * ``obsidian_memory.ObsidianMemory`` se reemplaza por un ``MagicMock`` con
    atributos configurables (``rest_available``, ``rest_client``, ``vault_path``)
  * El filesystem real se usa dentro de ``tmp_path`` (pytest fixture)
  * Variables de entorno se controlan con ``monkeypatch.delenv`` /
    ``monkeypatch.setenv`` para aislar el modo REST vs FS

Run: ``pytest test_save_main_factorygames.py -v``
     ``RUN_SLOW_TESTS=1 pytest test_save_main_factorygames.py -v``
"""
from __future__ import annotations

import sys
import os
import importlib
from pathlib import Path
from unittest import mock

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures y helpers
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
SCRIPT_PATH = SCRIPT_DIR / "_cargar_factorygames_texto.py"


@pytest.fixture
def cargar_module():
    """Importa (o reimporta) el script bajo test de forma aislada."""
    spec = importlib.util.spec_from_file_location(
        "_cargar_factorygames_texto", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fake_obsidian_class(monkeypatch):
    """Crea un Mock que reemplaza ``obsidian_memory.ObsidianMemory``.

    Devuelve (FakeClass, instances) donde ``instances`` es una lista con
    las instancias creadas, para que cada test pueda inspeccionar los
    kwargs con que se construyó cada una.
    """
    instances = []

    class FakeObsidianMemory:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs
            instances.append(self)
            # Default: FS mode (no REST)
            self.rest_available = False
            self.rest_client = None
            # vault_path por defecto: tmp_path/vault
            vault_path = kwargs.get("vault_path")
            if vault_path is None:
                # Si el script pasa None, ObsidianMemory real usa
                # ~/simmoon-memoria; para tests usamos un marker string
                self.vault_path = Path("~/simmoon-memoria")
            else:
                self.vault_path = Path(vault_path)

    fake_module = mock.MagicMock()
    fake_module.ObsidianMemory = FakeObsidianMemory
    monkeypatch.setitem(sys.modules, "obsidian_memory", fake_module)
    return FakeObsidianMemory, instances


@pytest.fixture
def sample_txt(tmp_path):
    """Crea un TXT de muestra con BOM + 2 líneas (sin newline final)."""
    p = tmp_path / "FactoryGames-Estudio.txt"
    p.write_bytes("\ufeffLínea 1\nLínea 2 sin newline".encode("utf-8"))
    return p


# ─────────────────────────────────────────────────────────────────────────────
# TestSaveViaObsidianMemory — modo REST vs FS
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveViaObsidianMemory:
    """Tests de ``save_via_obsidian_memory(md_text, vault_path=None)``."""

    def test_fs_mode_writes_to_factorygames_folder(
        self, cargar_module, fake_obsidian_class, tmp_path, monkeypatch
    ):
        """En modo FS escribe a ``vault/FactoryGames/...md`` (NO a Buffy/)."""
        FakeCls, instances = fake_obsidian_class
        # No OBSIDIAN_REST_API_KEY → rest_available=False
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)

        vault = tmp_path / "vault"
        ok = cargar_module.save_via_obsidian_memory(
            "# md", vault_path=str(vault)
        )

        assert ok is True
        assert len(instances) == 1
        target = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.md"
        assert target.exists(), f"Expected {target} to exist"
        assert target.read_text(encoding="utf-8") == "# md"

    def test_rest_mode_calls_rest_client_with_custom_path(
        self, cargar_module, fake_obsidian_class, monkeypatch
    ):
        """En modo REST usa ``rest_client.write_note(rel_path, md_text)``."""
        FakeCls, instances = fake_obsidian_class
        monkeypatch.setenv("OBSIDIAN_REST_API_KEY", "test-key-xyz")
        monkeypatch.setenv("OBSIDIAN_REST_PORT", "27124")
        monkeypatch.setenv("OBSIDIAN_REST_HTTPS", "false")

        # Configurar la instancia post-creación para que sea REST
        instances_holder = []

        real_init = FakeCls.__init__

        def init_with_rest(self, *args, **kwargs):
            real_init(self, *args, **kwargs)
            self.rest_available = True
            self.rest_client = mock.MagicMock()
            self.rest_client.write_note.return_value = True
            instances_holder.append(self)

        FakeCls.__init__ = init_with_rest

        ok = cargar_module.save_via_obsidian_memory("# rest md")

        assert ok is True
        assert len(instances_holder) == 1
        inst = instances_holder[0]
        # Verifica que la ruta NO usa Buffy/ sino FactoryGames/
        inst.rest_client.write_note.assert_called_once()
        called_path, called_content = inst.rest_client.write_note.call_args[0]
        assert called_path == "FactoryGames/FactoryGames-Estudio-Texto-Fundador.md", (
            f"Expected custom FactoryGames/ path, got {called_path!r}"
        )
        assert called_content == "# rest md"
        # Verifica que los kwargs de REST se pasaron correctamente
        assert inst.kwargs.get("rest_api_key") == "test-key-xyz"
        assert inst.kwargs.get("rest_port") == 27124
        assert inst.kwargs.get("rest_https") is False

    def test_fs_mode_handles_write_exception(
        self, cargar_module, fake_obsidian_class, tmp_path, monkeypatch, capsys
    ):
        """Si write_text lanza, retorna False y muestra error."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)

        # Forzar exception en el write_text
        FakeCls, instances = fake_obsidian_class
        real_init = FakeCls.__init__

        def init_with_bad_vault(self, *args, **kwargs):
            real_init(self, *args, **kwargs)
            # vault_path apunta a un directorio inválido (un archivo)
            bad = tmp_path / "IAmAFile"
            bad.write_text("x", encoding="utf-8")
            self.vault_path = bad

        FakeCls.__init__ = init_with_bad_vault

        ok = cargar_module.save_via_obsidian_memory("# md")
        assert ok is False
        captured = capsys.readouterr()
        assert "❌" in captured.out

    def test_rest_mode_handles_write_note_returning_false(
        self, cargar_module, fake_obsidian_class, monkeypatch
    ):
        """Si rest_client.write_note retorna False, retorna False."""
        monkeypatch.setenv("OBSIDIAN_REST_API_KEY", "k")

        FakeCls, instances = fake_obsidian_class
        real_init = FakeCls.__init__

        def init(self, *a, **kw):
            real_init(self, *a, **kw)
            self.rest_available = True
            self.rest_client = mock.MagicMock()
            self.rest_client.write_note.return_value = False

        FakeCls.__init__ = init

        ok = cargar_module.save_via_obsidian_memory("# md")
        assert ok is False

    def test_prints_mode_correctly(self, cargar_module, fake_obsidian_class,
                                   tmp_path, monkeypatch, capsys):
        """Muestra '🪨 Guardando via ObsidianMemory [FS|REST]: ...' en stdout."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        cargar_module.save_via_obsidian_memory(
            "# md", vault_path=str(tmp_path / "v")
        )
        out = capsys.readouterr().out
        assert "[FS]:" in out
        assert "FactoryGames/FactoryGames-Estudio-Texto-Fundador.md" in out

    def test_idempotent_rerun_overwrites(
        self, cargar_module, fake_obsidian_class, tmp_path, monkeypatch
    ):
        """Re-ejecución sobre el mismo path sobrescribe (no falla)."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"
        # 1ª ejecución
        assert cargar_module.save_via_obsidian_memory(
            "v1", vault_path=str(vault)
        ) is True
        # 2ª ejecución (mismo path, contenido distinto)
        assert cargar_module.save_via_obsidian_memory(
            "v2", vault_path=str(vault)
        ) is True
        target = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.md"
        assert target.read_text(encoding="utf-8") == "v2"

    def test_does_not_write_to_buffy_folder(
        self, cargar_module, fake_obsidian_class, tmp_path, monkeypatch
    ):
        """Asegura que NO usa el routing por defecto Buffy/{type}/..."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"
        cargar_module.save_via_obsidian_memory(
            "# md", vault_path=str(vault)
        )
        # No debe haber carpeta Buffy/ en el vault
        assert not (vault / "Buffy").exists(), (
            "save_via_obsidian_memory NO debe escribir a Buffy/"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TestMain — entrypoint CLI
# ─────────────────────────────────────────────────────────────────────────────

class TestMain:
    """Tests de ``main()`` con sys.argv controlado y ObsidianMemory mockeado."""

    def _run_main(self, cargar_module, argv, monkeypatch):
        """Ejecuta main() con sys.argv simulado y retorna exit code."""
        monkeypatch.setattr(sys, "argv", ["_cargar_factorygames_texto.py"] + argv)
        return cargar_module.main()

    def test_src_not_found_returns_1(
        self, cargar_module, fake_obsidian_class, monkeypatch, tmp_path
    ):
        """Si --src apunta a un archivo inexistente, retorna 1."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        missing = tmp_path / "no_existe.txt"
        rc = self._run_main(
            cargar_module,
            ["--src", str(missing), "--skip-txt-copy"],
            monkeypatch,
        )
        assert rc == 1

    def test_fs_mode_writes_both_md_and_txt(
        self, cargar_module, fake_obsidian_class, sample_txt, monkeypatch, tmp_path
    ):
        """Modo FS: escribe MD + copia TXT a vault/FactoryGames/."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"

        rc = self._run_main(
            cargar_module,
            ["--src", str(sample_txt), "--vault", str(vault)],
            monkeypatch,
        )
        assert rc == 0
        md_path = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.md"
        txt_path = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.txt"
        assert md_path.exists()
        assert txt_path.exists()
        # El MD debe tener el wikilink al TXT
        assert "[[FactoryGames-Estudio-Texto-Fundador.txt]]" in md_path.read_text(
            encoding="utf-8"
        )

    def test_rest_mode_writes_both_via_rest_client(
        self, cargar_module, fake_obsidian_class, sample_txt, monkeypatch
    ):
        """Modo REST: usa rest_client.write_note para MD y TXT."""
        monkeypatch.setenv("OBSIDIAN_REST_API_KEY", "k")

        instances_holder = []
        FakeCls, _ = fake_obsidian_class
        real_init = FakeCls.__init__

        def init(self, *a, **kw):
            real_init(self, *a, **kw)
            self.rest_available = True
            self.rest_client = mock.MagicMock()
            self.rest_client.write_note.return_value = True
            instances_holder.append(self)

        FakeCls.__init__ = init

        rc = self._run_main(
            cargar_module, ["--src", str(sample_txt)], monkeypatch
        )
        assert rc == 0
        # 2 calls: 1 para el TXT, 1 para el MD
        assert len(instances_holder) == 1
        rest_client = instances_holder[0].rest_client
        assert rest_client.write_note.call_count == 2
        called_paths = [c.args[0] for c in rest_client.write_note.call_args_list]
        assert "FactoryGames/FactoryGames-Estudio-Texto-Fundador.md" in called_paths
        assert "FactoryGames/FactoryGames-Estudio-Texto-Fundador.txt" in called_paths

    def test_skip_txt_copy_does_not_copy_txt(
        self, cargar_module, fake_obsidian_class, sample_txt, monkeypatch, tmp_path
    ):
        """Con --skip-txt-copy, no copia el TXT (sólo el MD)."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"

        rc = self._run_main(
            cargar_module,
            ["--src", str(sample_txt), "--vault", str(vault), "--skip-txt-copy"],
            monkeypatch,
        )
        assert rc == 0
        md_path = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.md"
        txt_path = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.txt"
        assert md_path.exists()
        assert not txt_path.exists(), "TXT no debe existir con --skip-txt-copy"

    def test_fs_mode_txt_copy_failure_does_not_abort(
        self, cargar_module, fake_obsidian_class, sample_txt, monkeypatch, tmp_path, capsys
    ):
        """Si la copia del TXT falla (exception), main continúa y retorna 0 si el MD OK."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"
        # Pre-crear un DIRECTORIO en la ruta del TXT destino para forzar
        # que write_text falle SOLO para el TXT, no para el MD.
        # (Si bloquearamos ``vault/FactoryGames/`` bloquearíamos ambos.)
        txt_blocker = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.txt"
        txt_blocker.parent.mkdir(parents=True, exist_ok=True)
        txt_blocker.mkdir(parents=False, exist_ok=False)

        rc = self._run_main(
            cargar_module,
            ["--src", str(sample_txt), "--vault", str(vault)],
            monkeypatch,
        )
        # main() debe retornar 0 (MD OK) aunque TXT falle con warning
        assert rc == 0
        # El MD sí debe haberse escrito
        md_path = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.md"
        assert md_path.exists()
        out = capsys.readouterr().out
        assert "⚠️" in out

    def test_idempotent_rerun_overwrites_md(
        self, cargar_module, fake_obsidian_class, sample_txt, monkeypatch, tmp_path
    ):
        """Re-ejecución: MD se sobrescribe con timestamp nuevo, no falla."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"

        rc1 = self._run_main(
            cargar_module, ["--src", str(sample_txt), "--vault", str(vault)], monkeypatch
        )
        rc2 = self._run_main(
            cargar_module, ["--src", str(sample_txt), "--vault", str(vault)], monkeypatch
        )
        assert rc1 == 0
        assert rc2 == 0
        md_path = vault / "FactoryGames" / "FactoryGames-Estudio-Texto-Fundador.md"
        assert md_path.exists()

    def test_md_write_failure_returns_1(
        self, cargar_module, fake_obsidian_class, sample_txt, monkeypatch, tmp_path
    ):
        """Si la escritura del MD falla (FS), retorna 1."""
        monkeypatch.delenv("OBSIDIAN_REST_API_KEY", raising=False)
        vault = tmp_path / "vault"
        # Pre-crear un archivo en la ruta del MD para que el mkdir/write falle
        md_blocker = vault / "FactoryGames"
        md_blocker.parent.mkdir(parents=True, exist_ok=True)
        md_blocker.write_text("I am a file", encoding="utf-8")

        rc = self._run_main(
            cargar_module,
            ["--src", str(sample_txt), "--vault", str(vault), "--skip-txt-copy"],
            monkeypatch,
        )
        assert rc == 1
