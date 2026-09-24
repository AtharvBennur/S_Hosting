"""Inspect join keys across MPLADS workbooks."""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.workbook_reader import read_workbook
from app.ml.integration import _header_frame, normalize_key

DEMO = Path(__file__).resolve().parents[1] / "demo_data"

WORK_REF_PATTERN = re.compile(
    r"WS\s*/\s*MP\s*(\d+)\s*/\s*(\d{4})\s*-\s*(\d{4})\s*/\s*(\d+)",
    re.IGNORECASE,
)


def extract_work_reference(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = WORK_REF_PATTERN.search(text)
    if not match:
        return normalize_key(text)
    mp_code, year_start, year_end, serial = match.groups()
    return f"WSMP{mp_code}{year_start}{year_end}{serial}"


def main():
    paths = {
        "sanctioned": DEMO / "Works Sanctioned.xlsx",
        "expenditure": DEMO / "Expenditure on Completed and On-going Works as on Date.xlsx",
        "completed": DEMO / "Works Completed.xlsx",
    }
    ids = {}
    for name, path in paths.items():
        sheets = read_workbook(path)
        raw = sheets[list(sheets.keys())[0]]
        frame = _header_frame(raw)
        print(f"\n=== {name} ===")
        if name == "expenditure" and "Work ID" in frame.columns:
            extracted = frame["Work ID"].map(extract_work_reference)
        elif "Work" in frame.columns:
            extracted = frame["Work"].map(extract_work_reference)
        else:
            extracted = frame.iloc[:, 0].map(extract_work_reference)
        nonempty = extracted[extracted.astype(str).str.strip() != ""]
        print("extracted count:", len(nonempty), "unique:", nonempty.nunique())
        print("samples:", nonempty.head(3).tolist())
        ids[name] = set(nonempty.tolist())

    print("\nOverlap sanctioned vs expenditure:", len(ids["sanctioned"] & ids["expenditure"]))
    print("Overlap sanctioned vs completed:", len(ids["sanctioned"] & ids["completed"]))
    print("Overlap expenditure vs completed:", len(ids["expenditure"] & ids["completed"]))

if __name__ == "__main__":
    main()
