from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Literal
from functools import lru_cache
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class BackendConfig(BaseModel):
    id: str
    url: str
    model: str
    weight: int = 1
    max_connections: int = 10
    tags: List[str] = []


class RateLimitTiers(BaseModel):
    premium: int = 300
    standard: int = 60
    batch: int = 20


class RateLimitConfig(BaseModel):
    enabled: bool = True
    default_rpm: int = 60
    burst_multiplier: float = 1.5
    tiers: RateLimitTiers = Field(default_factory=RateLimitTiers)


class CircuitBreakerConfig(BaseModel):
    error_threshold: float = 0.5
    window_seconds: int = 10
    open_timeout: int = 30
    success_threshold: int = 2


class QueueTiers(BaseModel):
    premium: int = 10
    standard: int = 5
    batch: int = 1


class QueueConfig(BaseModel):
    enabled: bool = True
    max_depth: int = 1000
    tiers: QueueTiers = Field(default_factory=QueueTiers)


class RoutingConfig(BaseModel):
    default_strategy: Literal[
        "round_robin", "latency_aware", "least_connections", "priority"
    ] = "latency_aware"
    ewma_alpha: float = 0.1
    health_check_interval: int = 10


class GatewayConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "info"


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379"
    db: int = 0
    max_connections: int = 20


class TimeoutConfig(BaseModel):
    connect: float = 5.0
    read: float = 120.0
    write: float = 10.0


class HermesConfig(BaseModel):
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    backends: List[BackendConfig] = []
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)


_config: Optional[HermesConfig] = None


def load_config(path: str = "config/config.yaml") -> HermesConfig:
    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return HermesConfig(**data)
    return HermesConfig()


def get_config() -> HermesConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Used in tests to reset singleton."""
    global _config
    _config = None
