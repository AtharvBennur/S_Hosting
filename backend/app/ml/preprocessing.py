import re
from pathlib import Path
from typing import Iterable

import pandas as pd
from rapidfuzz import fuzz, process

REQUIRED_FIELDS = [
    'project_name',
    'state',
    'district',
    'sanction_amount',
    'expenditure',
]

CANONICAL_ALIASES = {
    'project_name': ['project name', 'name of work', 'work', 'work description', 'project', 'title', 'scheme name', 'work name'],
    'state': ['state', 'state name', 'state/ut', 'province'],
    'district': ['district', 'district name', 'district/region', 'ida'],
    'constituency': ['constituency', 'parliamentary constituency', 'lok sabha constituency', 'ls constituency'],
    'agency': ['agency', 'implementing agency', 'department', 'executing agency', 'nodal agency'],
    'project_category': ['category', 'work category', 'project category', 'scheme category', 'type of work'],
    'vendor_name': ['vendor', 'vendor name', 'contractor', 'supplier'],
    'utilization_ratio': ['utilization ratio', 'utilisation ratio', 'disbursement to sanction ratio'],
    'delay_days': ['delay days', 'days delayed', 'delay'],
    'sanction_amount': ['sanction amount', 'sanctioned amount', 'approved amount', 'approved project cost', 'sanctioned cost', 'project cost', 'sanction amount (₹)'],
    'expenditure': ['expenditure', 'expenditure amount', 'actual expenditure', 'funds utilised', 'funds utilized', 'utilised amount', 'utilized amount', 'expenditure incurred', 'amount disbursed', 'fund disbursed amount'],
    'expected_completion_date': ['expected completion date', 'target date', 'target completion date', 'completion target'],
    'actual_completion_date': ['actual completion date', 'completion date', 'date of completion actual'],
    'sanction_date': ['sanction date', 'approval date', 'recommended date', 'start date'],
    'status': ['status', 'work status', 'project status', 'completion status', 'payment status'],
    'project_code': ['sr. no.', 'serial no.', 'serial number', 'project code', 'project id', 'id', 'work id', 'work'],
    'mp_name': ['mp', 'mp name', 'member of parliament', "hon'ble member of parliament", "hon'ble members of parliament", 'parliament member'],
}


def normalize_header(value: object) -> str:
    text = str(value).strip().lower()
    text = text.replace('-', '_').replace(' ', '_').replace('/', '_')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text


def header_candidates() -> list[str]:
    candidates = []
    for canonical, aliases in CANONICAL_ALIASES.items():
        candidates.append(canonical)
        candidates.extend(aliases)
    return list(dict.fromkeys(candidates))


def detect_canonical_name(raw_name: str) -> tuple[str | None, float]:
    normalized = normalize_header(raw_name)
    for canonical, aliases in CANONICAL_ALIASES.items():
        if normalized == canonical:
            return canonical, 100.0
        if normalized in {normalize_header(alias) for alias in aliases}:
            return canonical, 100.0
    candidates = [(canonical, alias) for canonical, aliases in CANONICAL_ALIASES.items() for alias in [canonical, *aliases]]
    best = process.extractOne(normalized, [alias for _, alias in candidates], scorer=fuzz.ratio)
    if best and best[1] >= 75:
        return next(canonical for canonical, alias in candidates if alias == best[0]), float(best[1])
    return None, 0.0


def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = df.copy()
    original_columns = list(normalized_df.columns)
    renamed = {}
    for col in original_columns:
        canonical, score = detect_canonical_name(str(col))
        if canonical:
            renamed[col] = canonical
        else:
            renamed[col] = normalize_header(col)
    normalized_df = normalized_df.rename(columns=renamed)
    if normalized_df.columns.duplicated().any():
        deduplicated = pd.DataFrame(index=normalized_df.index)
        for column in dict.fromkeys(normalized_df.columns):
            values = normalized_df.loc[:, normalized_df.columns == column]
            deduplicated[column] = values.bfill(axis=1).iloc[:, 0]
        normalized_df = deduplicated
    if 'category' in normalized_df.columns and 'project_category' in normalized_df.columns:
        normalized_df = normalized_df.drop(columns=['category'])
    normalized_df.columns = [str(c) for c in normalized_df.columns]
    return normalized_df


def read_file_to_dataframe(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path)
    if path.suffix.lower() in {'.xls', '.xlsx'}:
        excel_file = pd.ExcelFile(path)
        sheet_data = []
        for sheet in excel_file.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            sheet_data.append(df.assign(_sheet_name=sheet))
        if not sheet_data:
            return pd.DataFrame()
        return pd.concat(sheet_data, ignore_index=True)
    raise ValueError('Unsupported file type. Use CSV or XLSX.')


def coerce_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(',', '', regex=False)
    cleaned = cleaned.str.replace(r'[^0-9.\-]', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce')


def validate_dataset(df: pd.DataFrame) -> tuple[bool, list[str], dict[str, str]]:
    normalized = normalize_dataframe_columns(df)
    missing = [field for field in REQUIRED_FIELDS if field not in normalized.columns]
    if 'project_name' in missing and 'project_code' in normalized.columns:
        # A project ID is a sufficient, stable name for registers that do not
        # provide a separate description column.
        missing.remove('project_name')
    suggested: dict[str, str] = {}
    if missing:
        for field in missing:
            candidates = CANONICAL_ALIASES.get(field, [])
            best = process.extractOne(
                field,
                list(normalized.columns),
                scorer=lambda value, candidate: max(
                    fuzz.ratio(normalize_header(candidate), normalize_header(alias))
                    for alias in [field, *candidates]
                ),
            )
            if best and best[1] >= 75:
                suggested[field] = best[0]
    return len(missing) == 0, missing, suggested


def build_mapping(df: pd.DataFrame) -> tuple[dict[str, str], list[str]]:
    normalized = normalize_dataframe_columns(df)
    output: dict[str, str] = {}
    for col in list(df.columns):
        canonical, score = detect_canonical_name(str(col))
        if canonical:
            output[col] = canonical
    return output, list(normalized.columns)
