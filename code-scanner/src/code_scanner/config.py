from __future__ import annotations

import json
from pathlib import Path

from code_scanner.models import AppConfig, ProviderSettings, ScanSettings, SignalRule


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    providers_raw = raw.get("providers")
    if not isinstance(providers_raw, list) or not providers_raw:
        raise ConfigError("Config must include non-empty 'providers' list")

    providers: list[ProviderSettings] = []
    for item in providers_raw:
        if not isinstance(item, dict):
            raise ConfigError("Each provider entry must be an object")
        provider_type = str(item.get("type", "")).strip()
        name = str(item.get("name", "")).strip()
        if not provider_type:
            raise ConfigError("Provider entry is missing 'type'")
        if not name:
            raise ConfigError("Provider entry is missing 'name'")

        providers.append(
            ProviderSettings(
                type=provider_type,
                name=name,
                base_url=_optional_str(item.get("base_url")),
                token_env=_optional_str(item.get("token_env")),
                org=_optional_str(item.get("org")),
                workspace=_optional_str(item.get("workspace")),
                project_key=_optional_str(item.get("project_key")),
                root_dir=_optional_str(item.get("root_dir")),
                recursive=bool(item.get("recursive", False)),
                use_token_for_clone=bool(item.get("use_token_for_clone", False)),
            )
        )

    scan_raw = raw.get("scan", {})
    if not isinstance(scan_raw, dict):
        raise ConfigError("'scan' must be an object")

    scan = ScanSettings(
        include_repo_patterns=tuple(_ensure_string_list(scan_raw.get("include_repo_patterns", []))),
        exclude_repo_patterns=tuple(_ensure_string_list(scan_raw.get("exclude_repo_patterns", []))),
        max_file_size_bytes=int(scan_raw.get("max_file_size_bytes", 500_000)),
        max_files_per_repo=int(scan_raw.get("max_files_per_repo", 40_000)),
    )

    return AppConfig(
        db_path=str(raw.get("db_path", "data/code_scanner.db")),
        repo_cache_dir=str(raw.get("repo_cache_dir", "repo_cache")),
        rules_path=str(raw.get("rules_path", "configs/default_rules.json")),
        providers=tuple(providers),
        scan=scan,
    )


def load_rules(path: str | Path) -> list[SignalRule]:
    rules_path = Path(path)
    if not rules_path.exists():
        raise ConfigError(f"Rules file not found: {rules_path}")

    with rules_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, list) or not raw:
        raise ConfigError("Rules file must contain a non-empty list")

    rules: list[SignalRule] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ConfigError("Each rule entry must be an object")

        missing = [
            key
            for key in ("signal_code", "category", "severity", "description", "pattern")
            if key not in item
        ]
        if missing:
            raise ConfigError(f"Rule is missing keys: {', '.join(missing)}")

        rules.append(
            SignalRule(
                signal_code=str(item["signal_code"]),
                category=str(item["category"]),
                severity=str(item["severity"]),
                description=str(item["description"]),
                pattern=str(item["pattern"]),
                ignore_case=bool(item.get("ignore_case", False)),
            )
        )

    return rules


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ensure_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError("Expected a list of strings")
    return [str(item) for item in value]
