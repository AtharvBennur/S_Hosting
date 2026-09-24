from __future__ import annotations

from typing import Iterable

import pandas as pd
from rapidfuzz import fuzz, process

from app.ml.preprocessing import CANONICAL_ALIASES, normalize_header


class SchemaMapper:
    def __init__(self):
        self.alias_map = {
            normalize_header(k): normalize_header(v)
            for k, values in CANONICAL_ALIASES.items()
            for v in values
        }

    def map_columns(self, columns: Iterable[str]) -> dict[str, str]:
        return {raw: canonical for raw, canonical, _ in self.map_columns_with_confidence(columns)}

    def map_columns_with_confidence(self, columns: Iterable[str]) -> list[tuple[str, str, float]]:
        mappings: list[tuple[str, str, float]] = []
        mapped: dict[str, str] = {}
        canonical_names = {normalize_header(name): name for name in CANONICAL_ALIASES}
        for raw in columns:
            key = normalize_header(raw)
            if key in canonical_names:
                mapped[str(raw)] = canonical_names[key]
                mappings.append((str(raw), canonical_names[key], 100.0))
                continue
            score_target = None
            best_name = None
            for canonical in canonical_names:
                alias_values = CANONICAL_ALIASES[canonical]
                for alias in alias_values:
                    score = fuzz.ratio(key, normalize_header(alias))
                    if score > (score_target or 0):
                        score_target = score
                        best_name = canonical
            if score_target is not None and score_target >= 78:
                mapped[str(raw)] = best_name
                mappings.append((str(raw), best_name, float(score_target)))
            else:
                mapped[str(raw)] = key
                mappings.append((str(raw), key, 0.0))
        return mappings

    def suggest_missing_fields(self, missing_fields: list[str], columns: list[str]) -> dict[str, str]:
        suggestions: dict[str, str] = {}
        for field in missing_fields:
            for col in columns:
                best_score = 0.0
                for alias in CANONICAL_ALIASES.get(field, []):
                    score = fuzz.ratio(normalize_header(col), normalize_header(alias))
                    if score > best_score:
                        best_score = score
                if best_score >= 75:
                    suggestions[field] = col
                    break
        return suggestions


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    mapped = df.copy()
    rename_map = {}
    for original_name, canonical_name in mapping.items():
        if original_name in mapped.columns:
            rename_map[original_name] = canonical_name
    return mapped.rename(columns=rename_map)
