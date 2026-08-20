"""Repository / environment / branch / model allowlists."""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.cursor_relay.config import RelayConfig


class AllowlistError(Exception):
    def __init__(self, message: str, *, dimension: str) -> None:
        super().__init__(message)
        self.dimension = dimension
        self.code = "allowlist_denied"


@dataclass(frozen=True)
class DispatchTarget:
    repository: str
    environment: str
    head_branch: str
    model: str
    base_branch: str | None = None


def normalize_repository(repo: str) -> str:
    value = repo.strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    return value.removesuffix(".git").strip("/")


def check_repository(config: RelayConfig, repository: str) -> str:
    normalized = normalize_repository(repository)
    if normalized not in config.allowed_repositories:
        raise AllowlistError(
            f"Repository not allowlisted: {normalized}",
            dimension="repository",
        )
    return normalized


def check_environment(config: RelayConfig, environment: str) -> str:
    name = environment.strip()
    if name not in config.allowed_environments:
        raise AllowlistError(
            f"Named environment not allowlisted: {name}",
            dimension="environment",
        )
    return name


def check_head_branch(config: RelayConfig, branch: str) -> str:
    head = branch.strip()
    if head in config.forbidden_head_branches:
        raise AllowlistError(
            f"Head branch '{head}' is forbidden without explicit policy override",
            dimension="branch",
        )
    if not any(head.startswith(prefix) for prefix in config.allowed_branch_prefixes):
        raise AllowlistError(
            f"Head branch '{head}' does not match allowed prefixes "
            f"{list(config.allowed_branch_prefixes)}",
            dimension="branch",
        )
    return head


def check_model(config: RelayConfig, model: str) -> str:
    mid = model.strip()
    if mid not in config.allowed_models:
        raise AllowlistError(f"Model not allowlisted: {mid}", dimension="model")
    return mid


def validate_dispatch_target(
    config: RelayConfig,
    *,
    repository: str,
    environment: str,
    head_branch: str,
    model: str,
    base_branch: str | None = None,
) -> DispatchTarget:
    return DispatchTarget(
        repository=check_repository(config, repository),
        environment=check_environment(config, environment),
        head_branch=check_head_branch(config, head_branch),
        model=check_model(config, model),
        base_branch=base_branch.strip() if base_branch else None,
    )
