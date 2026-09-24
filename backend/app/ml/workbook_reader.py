from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def read_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    """Read CSV files or Excel workbooks into a uniform sheet mapping."""
    path = Path(path)
    if path.suffix.lower() == '.csv':
        return {'CSV': pd.read_csv(path)}
    try:
        # Try calamine first (more robust for styled Excel files)
        xl_file = pd.ExcelFile(path, engine='calamine')
    except ImportError:
        # Fallback to openpyxl if calamine not available
        xl_file = pd.ExcelFile(path, engine='openpyxl')
    
    sheets = {}
    for sheet_name in xl_file.sheet_names:
        sheets[sheet_name] = pd.read_excel(xl_file, sheet_name=sheet_name)
    
    xl_file.close()
    return sheets


def read_relevant_sheet(path: str | Path) -> tuple[str, pd.DataFrame, list[dict[str, Any]]]:
    """Read workbook and return the most relevant sheet with metadata."""
    sheets = read_workbook(path)
    summaries = [
        {
            'sheet': name,
            'rows': len(frame),
            'columns': frame.shape[1],
            'non_null_count': frame.notna().sum().sum()
        }
        for name, frame in sheets.items()
    ]
    if not sheets:
        return '', pd.DataFrame(), summaries
    # Select sheet with most non-null data
    selected_name, selected_frame = max(sheets.items(), key=lambda item: item[1].notna().sum().sum())
    return selected_name, selected_frame, summaries
