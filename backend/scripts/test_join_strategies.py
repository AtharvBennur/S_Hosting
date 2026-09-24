"""Compare join strategies for MPLADS datasets."""
from pathlib import Path
import re
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.workbook_reader import read_workbook
from app.ml.integration import _header_frame, parse_district

DEMO = Path(__file__).resolve().parents[1] / "demo_data"
WORK_REF = re.compile(r"WS\s*/\s*MP\s*(\d+)\s*/\s*(\d{4})\s*-\s*(\d{4})\s*/\s*(\d+)", re.I)


def extract_ref(value: object) -> str:
    match = WORK_REF.search(str(value or ""))
    if match:
        mp, ys, ye, serial = match.groups()
        return f"WSMP{mp}{ys}{ye}{serial}"
    return ""


def load(name: str) -> pd.DataFrame:
    path = DEMO / name
    raw = read_workbook(path)[list(read_workbook(path).keys())[0]]
    return _header_frame(raw)


def norm_text(v: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def main():
    san = load("Works Sanctioned.xlsx")
    exp = load("Expenditure on Completed and On-going Works as on Date.xlsx")

    san["ref"] = san["Work"].map(extract_ref)
    exp["ref"] = exp["Work ID"].map(extract_ref)
    san["sr"] = pd.to_numeric(san["Sr. No."], errors="coerce")
    exp["sr"] = pd.to_numeric(exp["Sr. No."], errors="coerce")

    san["desc"] = san["Work description"].map(norm_text)
    exp["desc"] = exp["Work"].map(norm_text)
    san["loc"] = san["State"].map(norm_text) + "|" + san["Constituency"].map(norm_text)
    exp["loc"] = exp["State"].map(norm_text) + "|" + exp["Constituency"].map(norm_text)

    merged_sr = san.merge(exp, on="sr", suffixes=("_san", "_exp"))
    print("merge on Sr No rows:", len(merged_sr))
    print("same state on sr merge:", (merged_sr["State_san"] == merged_sr["State_exp"]).mean())
    print("same constituency on sr merge:", (merged_sr["Constituency_san"] == merged_sr["Constituency_exp"]).mean())

    desc_match = san.merge(exp.drop_duplicates("desc"), on="desc", how="inner")
    print("desc exact match rows:", len(desc_match))

    loc_desc = san.merge(exp.drop_duplicates(["loc", "desc"]), on=["loc", "desc"], how="inner")
    print("loc+desc match rows:", len(loc_desc))

    # serial number only from work ref tail
    san["serial"] = san["ref"].str[-6:]
    exp["serial"] = exp["ref"].str[-6:]
    serial_loc = san.merge(exp.drop_duplicates(["loc", "serial"]), on=["loc", "serial"], how="inner")
    print("loc+serial match rows:", len(serial_loc))

    print("\nSample sanctioned ref:", san["ref"].head(3).tolist())
    print("Sample expenditure ref:", exp["ref"].head(3).tolist())
    print("Sample sanctioned work:", san["Work"].head(1).iloc[0][:100])
    print("Sample exp work id:", exp["Work ID"].head(1).iloc[0])


if __name__ == "__main__":
    main()
