from __future__ import annotations

from dataclasses import dataclass

from ism.config import AppConfig


@dataclass(frozen=True)
class RunProvenance:
    git_commit: str
    model_revision: str
    tokenizer_revision: str
    seed: int

    def validate(self) -> None:
        if not self.git_commit or not self.model_revision or not self.tokenizer_revision:
            raise ValueError("provenance fields must not be empty")


@dataclass(frozen=True)
class FrozenRunManifest:
    run_id: str
    config_hash: str
    provenance: RunProvenance

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        config: AppConfig,
        provenance: RunProvenance,
    ) -> FrozenRunManifest:
        provenance.validate()
        return cls(
            run_id=run_id,
            config_hash=config.config_hash(),
            provenance=provenance,
        )

    def verify_config(self, config: AppConfig) -> None:
        if config.config_hash() != self.config_hash:
            raise ValueError("resolved config changed after run manifest was frozen")
