"""
沙漠环境兼容入口。

说明：
- 原先所有沙漠环境代码集中在本文件。
- 现已按项目架构拆分到 `Ditu/biomes/` 子模块。
- 为了不影响现有 import（如 `from .desert_env import DesertEnvironment`），
  该文件保留并转发同名公开接口。
"""

from .biomes import (
    DesertEnvironment,
    DustParticle,
    ExplosionParticle,
    Particle,
    SandstoneBlock,
    TempleArrow,
    TrapDispenser,
    TrapTNT,
)

__all__ = [
    "Particle",
    "ExplosionParticle",
    "DustParticle",
    "TempleArrow",
    "SandstoneBlock",
    "TrapDispenser",
    "TrapTNT",
    "DesertEnvironment",
]
