from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class RequestTier(str, Enum):
    PREMIUM = "premium"
    STANDARD = "standard"
    BATCH = "batch"


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LATENCY_AWARE = "latency_aware"
    LEAST_CONNECTIONS = "least_connections"
    PRIORITY = "priority"


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    tier: RequestTier = RequestTier.STANDARD
    routing_strategy: Optional[RoutingStrategy] = None


class CompletionRequest(BaseModel):
    model: Optional[str] = None
    prompt: str
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    tier: RequestTier = RequestTier.STANDARD


class BackendStatus(BaseModel):
    id: str
    url: str
    model: str
    healthy: bool
    circuit_state: str
    active_connections: int
    latency_ewma_ms: float
    requests_total: int = 0
    errors_total: int = 0


class GatewayStatusResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    routing_strategy: str
    backends: List[BackendStatus]
    queue_depth: Dict[str, int]
    uptime_seconds: float
    redis_connected: bool


class RouteOverrideRequest(BaseModel):
    strategy: RoutingStrategy


class CircuitOverrideRequest(BaseModel):
    action: Literal["open", "close"]


class HealthResponse(BaseModel):
    status: str
    healthy_backends: int
    total_backends: int
    redis: str
    uptime_seconds: float


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    backend_id: Optional[str] = None
