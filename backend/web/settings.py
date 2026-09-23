"""Standalone web configuration, independent of modeling imports."""
from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    port: int = 8768
    frontend_port: int = 5173
    frontend_dist: Path = ROOT / 'frontend/dist'

    @classmethod
    def from_env(cls):
        return cls(port=int(os.getenv('OPSCOPE_PORT', '8768')),
                   frontend_port=int(os.getenv('OPSCOPE_FRONTEND_PORT', '5173')))

    @property
    def origins(self):
        return {f'http://{host}:{port}' for host in ('127.0.0.1', 'localhost')
                for port in (self.port, self.frontend_port)}
