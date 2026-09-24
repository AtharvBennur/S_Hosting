"""Authorized, explicit baseline-training entry point; never called by uploads."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.integration import integrate_files
from app.ml.pipeline import train_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description='Train an approved MPLADS baseline model from reviewed input workbooks.')
    parser.add_argument('files', nargs='+', type=Path, help='Reviewed sanctioned/expenditure source files')
    args = parser.parse_args()
    missing = [str(path) for path in args.files if not path.is_file()]
    if missing:
        parser.error(f'Input file(s) not found: {", ".join(missing)}')
    frame, summary = integrate_files(args.files)
    if frame.empty:
        parser.error('No canonical projects were available for baseline training.')
    if 'expenditure_amount' in frame.columns:
        frame['expenditure'] = frame['expenditure_amount']
    result = train_pipeline(frame, source_files=[path.name for path in args.files], enforce_minimum=True)
    print(f"Trained {result['model_version']} from {result['training_rows']} projects.")


if __name__ == '__main__':
    main()
