"""Explicit web and engine configuration, independent of modeling imports."""
from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    engine_root: str = ''
    engine_python: str = ''
    tilesim_python: str = ''
    port: int = 8768
    frontend_port: int = 5173
    frontend_dist: Path = ROOT / 'frontend/dist'

    @classmethod
    def from_env(cls):
        return cls(engine_root=os.getenv('OPSCOPE_ENGINE_ROOT', ''),
                   engine_python=os.getenv('OPSCOPE_ENGINE_PYTHON', ''),
                   tilesim_python=os.getenv('OPSCOPE_TILESIM_PYTHON', ''),
                   port=int(os.getenv('OPSCOPE_PORT', '8768')),
                   frontend_port=int(os.getenv('OPSCOPE_FRONTEND_PORT', '5173')))

    @property
    def origins(self):
        return {f'http://{host}:{port}' for host in ('127.0.0.1', 'localhost')
                for port in (self.port, self.frontend_port)}
