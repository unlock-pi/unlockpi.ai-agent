from __future__ import annotations

from config import LLMConfig, STTConfig, TTSConfig


def _dedupe(descriptors: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []

    for descriptor in descriptors:
        if descriptor in seen:
            continue
        seen.add(descriptor)
        ordered.append(descriptor)

    return tuple(ordered)


def _append_suffix_if_missing(descriptor: str, suffix: str) -> str:
    if not suffix or ":" in descriptor:
        return descriptor
    return f"{descriptor}:{suffix}"


def stt_fallback_descriptors(config: STTConfig) -> tuple[str, ...]:
    primary = _append_suffix_if_missing(config.model, config.language)
    normalized = _dedupe(
        tuple(_append_suffix_if_missing(model, config.language) for model in config.fallback_models)
    )
    return tuple(model for model in normalized if model != primary)


def llm_model_chain(config: LLMConfig) -> tuple[str, ...]:
    return _dedupe((config.model, *config.fallback_models))


def tts_model_chain(config: TTSConfig) -> tuple[str, ...]:
    return _dedupe((f"{config.model}:{config.voice}", *config.fallback_models))


def describe_fallback_chains(
    stt_config: STTConfig,
    llm_config: LLMConfig,
    tts_config: TTSConfig,
) -> dict[str, list[str]]:
    return {
        "stt": [f"{stt_config.model}:{stt_config.language}", *stt_fallback_descriptors(stt_config)],
        "llm": list(llm_model_chain(llm_config)),
        "tts": list(tts_model_chain(tts_config)),
    }
