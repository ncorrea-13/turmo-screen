"""Small data models used by the renderer and senders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class Metrics:
    cpu: float
    ram: float
    disk: float
    cpu_temp: Optional[float]
    gpu: Optional[float]
    gpu_temp: Optional[float]
    net_up_kb: float
    net_down_kb: float
