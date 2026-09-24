from pathlib import Path
import re
from app.ml.workbook_reader import read_workbook

BASE = Path('C:/Users/athar/Downloads')
FILES = {
    'sanctioned': 'Works Sanctioned.xlsx',
    'completed': 'Works Completed.xlsx',
    'expenditure': 'Expenditure on Completed and On-going Works as on Date.xlsx',
    'allocation': 'Allocated Limit for Honble MPs.xlsx',
}

def norm(value):
    return re.sub(r'[^A-Z0-9]', '', str(value).upper())

frames = {}
for role, filename in FILES.items():
    sheets = read_workbook(BASE / filename)
    print(f'{role}: workbook={filename}, sheets={list(sheets)}')
    raw = sheets['Sheet1']
    header = [str(value).strip() for value in raw.iloc[1].tolist()]
    frame = raw.iloc[2:].copy()
    frame.columns = header
    frames[role] = frame
    print(f'  rows={len(frame)}, columns={header}')

sanctioned = frames['sanctioned']
completed = frames['completed']
expenditure = frames['expenditure']
allocation = frames['allocation']
sanctioned_ids = set(sanctioned['Work'].map(norm))
completed_ids = set(completed['Work'].map(norm))
expenditure_ids = set(expenditure['Work ID'].map(norm))
print(f'work_id_matches: completed/sanctioned={len(completed_ids & sanctioned_ids)}, expenditure/sanctioned={len(expenditure_ids & sanctioned_ids)}, completed/expenditure={len(completed_ids & expenditure_ids)}')
sanctioned_context = set(zip(sanctioned['State'].map(norm), sanctioned["Hon'ble Members of Parliament"].map(norm), sanctioned['Constituency'].map(norm)))
allocation_context = set(zip(allocation['State'].map(norm), allocation["Hon'ble Members of Parliaments"].map(norm), allocation['Constituency'].map(norm)))
print(f'allocation_context_matches={len(sanctioned_context & allocation_context)} of sanctioned_context={len(sanctioned_context)}')
print(f'states={sanctioned["State"].nunique()}, sanctioned_categories={sanctioned["Work category"].nunique()}, MPs={sanctioned["Hon\'ble Members of Parliament"].nunique()}')
