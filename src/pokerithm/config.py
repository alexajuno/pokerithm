"""Application configuration for pokerithm."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulations."""

    default_simulations: int = 10000
    interactive_simulations: int = 5000


@dataclass
class Config:
    """Application configuration."""

    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    @classmethod
    def load(cls) -> Self:
        """Load config from file, falling back to defaults."""
        config_paths = [
            Path.cwd() / "pokerithm.toml",
            Path.cwd() / ".pokerithm.toml",
            Path.home() / ".config" / "pokerithm" / "config.toml",
            Path.home() / ".pokerithm.toml",
        ]

        for path in config_paths:
            if path.exists():
                return cls._from_file(path)

        return cls()

    @classmethod
    def _from_file(cls, path: Path) -> Self:
        """Load config from a TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        sim_data = data.get("simulation", {})
        simulation = SimulationConfig(
            default_simulations=sim_data.get("default_simulations", 10000),
            interactive_simulations=sim_data.get("interactive_simulations", 5000),
        )

        return cls(simulation=simulation)


# Global config instance (loaded lazily)
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
