#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
game_sound.py — Sonidos Procedurales para SIMMOON 🎵

Genera efectos de sonido procedurales usando síntesis de ondas.
Sin dependencias externas — solo math + struct + pygame.mixer.

Extraído de juego_simmoon.py como parte de la refactorización.
"""

import math
import random
import struct

import pygame


class SonidoProcedural:
    """Genera efectos de sonido procedurales usando síntesis de ondas.

    Sin dependencias externas — solo math + struct + pygame.mixer."""

    _inicializado = False

    @classmethod
    def _init_mixer(cls):
        if not cls._inicializado:
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            except pygame.error:
                pass  # Sin audio disponible
            cls._inicializado = True

    @staticmethod
    def _generar_onda(frecuencia: float, duracion: float, volumen: float = 0.3,
                      tipo: str = "sin", sample_rate: int = 22050) -> bytes:
        """Genera datos PCM de una onda simple."""
        num_samples = int(sample_rate * duracion)
        datos = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            if tipo == "sin":
                val = math.sin(2 * math.pi * frecuencia * t)
            elif tipo == "square":
                val = 1.0 if math.sin(2 * math.pi * frecuencia * t) >= 0 else -1.0
            elif tipo == "sawtooth":
                val = 2.0 * (t * frecuencia - math.floor(t * frecuencia + 0.5))
            elif tipo == "noise":
                val = random.uniform(-1, 1)
            else:
                val = math.sin(2 * math.pi * frecuencia * t)
            # Envelope suave (attack/release)
            env = 1.0
            ataque = min(1.0, i / (sample_rate * 0.02))
            release_start = num_samples - int(sample_rate * 0.05)
            if i > release_start:
                release = (num_samples - i) / (sample_rate * 0.05)
                env = min(ataque, release)
            else:
                env = ataque
            sample = int(val * volumen * env * 32767)
            sample = max(-32768, min(32767, sample))
            # Estéreo: mismo valor en ambos canales
            datos.extend(struct.pack('<hh', sample, sample))
        return bytes(datos)

    @classmethod
    def _reproducir(cls, datos: bytes):
        """Reproduce un sonido desde datos PCM."""
        cls._init_mixer()
        try:
            sonido = pygame.mixer.Sound(buffer=datos)
            sonido.play()
        except (pygame.error, Exception):
            pass

    @classmethod
    def sonido_construir(cls):
        """Sonido de construcción: tono ascendente."""
        sample_rate = 22050
        duracion = 0.18
        num_samples = int(sample_rate * duracion)
        datos = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            freq = 220 + 280 * (t / duracion)
            val = math.sin(2 * math.pi * freq * t)
            env = min(1.0, i / (sample_rate * 0.01)) * max(0.0, (num_samples - i) / (sample_rate * 0.06))
            sample = int(val * 0.25 * env * 32767)
            sample = max(-32768, min(32767, sample))
            datos.extend(struct.pack('<hh', sample, sample))
        cls._reproducir(bytes(datos))

    @classmethod
    def sonido_vender(cls):
        """Sonido de venta: dos pings rápidos (cash register)."""
        sample_rate = 22050
        duracion = 0.25
        num_samples = int(sample_rate * duracion)
        datos = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            if t < 0.1:
                freq = 880
                vol = 0.2
            elif t < 0.2:
                freq = 1100
                vol = 0.15
            else:
                freq = 660
                vol = 0.1
            val = math.sin(2 * math.pi * freq * t)
            env = max(0.0, 1.0 - t / duracion)
            sample = int(val * vol * env * 32767)
            sample = max(-32768, min(32767, sample))
            datos.extend(struct.pack('<hh', sample, sample))
        cls._reproducir(bytes(datos))

    @classmethod
    def sonido_turno(cls):
        """Sonido de avance de turno: whoosh sci-fi."""
        sample_rate = 22050
        duracion = 0.35
        num_samples = int(sample_rate * duracion)
        datos = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            freq = 150 + 400 * (t / duracion)
            noise_val = random.uniform(-0.4, 0.4)
            wave_val = math.sin(2 * math.pi * freq * t) * 0.6
            val = noise_val + wave_val
            env = min(1.0, i / (sample_rate * 0.02)) * max(0.0, (num_samples - i) / (sample_rate * 0.1))
            sample = int(val * 0.22 * env * 32767)
            sample = max(-32768, min(32767, sample))
            datos.extend(struct.pack('<hh', sample, sample))
        cls._reproducir(bytes(datos))

    @classmethod
    def sonido_alerta(cls):
        """Sonido de alerta / error."""
        sample_rate = 22050
        duracion = 0.15
        num_samples = int(sample_rate * duracion)
        datos = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            val = math.sin(2 * math.pi * 200 * t) * 0.5 + math.sin(2 * math.pi * 250 * t) * 0.5
            env = max(0.0, 1.0 - t / duracion)
            sample = int(val * 0.2 * env * 32767)
            sample = max(-32768, min(32767, sample))
            datos.extend(struct.pack('<hh', sample, sample))
        cls._reproducir(bytes(datos))
