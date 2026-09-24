from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

random.seed(26102)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / 'demo_data_synthetic'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATE_DISTRICTS = {
    'Andhra Pradesh': ['Guntur', 'Krishna', 'Visakhapatnam'],
    'Assam': ['Kamrup', 'Jorhat', 'Dibrugarh'],
    'Bihar': ['Patna', 'Gaya', 'Muzaffarpur'],
    'Chhattisgarh': ['Raipur', 'Durg', 'Bilaspur'],
    'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara'],
    'Haryana': ['Gurugram', 'Hisar', 'Karnal'],
    'Jharkhand': ['Ranchi', 'Dhanbad', 'East Singhbhum'],
    'Karnataka': ['Bengaluru Urban', 'Mysuru', 'Belagavi'],
    'Madhya Pradesh': ['Bhopal', 'Indore', 'Jabalpur'],
    'Maharashtra': ['Pune', 'Nagpur', 'Nashik'],
    'Odisha': ['Cuttack', 'Puri', 'Ganjam'],
    'Rajasthan': ['Jaipur', 'Jodhpur', 'Udaipur'],
    'Tamil Nadu': ['Chennai', 'Madurai', 'Coimbatore'],
    'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad'],
    'Uttar Pradesh': ['Lucknow', 'Varanasi', 'Prayagraj'],
    'West Bengal': ['Kolkata', 'Howrah', 'Darjeeling'],
}

CATEGORIES = {
    'Roads': (900_000, 8),
    'Water Supply': (1_600_000, 10),
    'Education': (1_250_000, 12),
    'Health': (1_450_000, 9),
    'Sanitation': (700_000, 7),
    'Community Infrastructure': (1_100_000, 14),
}

AGENCIES = ['PWD', 'Rural Development', 'Urban Development', 'Water Resources', 'Health Department', 'Education Department']
PATTERNS = ['NORMAL'] * 620 + ['DELAY'] * 150 + ['COST_ANOMALY'] * 90 + ['OVERRUN'] * 70 + ['HIGH_UTILIZATION'] * 60 + ['DUPLICATE'] * 35 + ['DATA_QUALITY'] * 25 + ['MULTI_SIGNAL'] * 80

rows = []
base_date = date(2023, 1, 1)

for index, pattern in enumerate(PATTERNS, start=1):
    state = random.choice(list(STATE_DISTRICTS))
    district = random.choice(STATE_DISTRICTS[state])
    category = random.choice(list(CATEGORIES))
    base_amount, duration_months = CATEGORIES[category]
    sanction = round(base_amount * random.uniform(0.65, 1.45), -3)
    sanction_date = base_date + timedelta(days=random.randint(0, 800))
    expected = sanction_date + timedelta(days=duration_months * 30)
    delay_days = random.randint(0, 20)
    expenditure_ratio = random.uniform(0.35, 0.9)
    name = f'{category} Improvement {index:03d}'

    if pattern == 'DELAY':
        delay_days = random.randint(55, 220)
        expenditure_ratio = random.uniform(0.35, 0.82)
    elif pattern == 'COST_ANOMALY':
        sanction = round(base_amount * random.uniform(2.2, 4.5), -3)
        expenditure_ratio = random.uniform(0.45, 0.85)
    elif pattern == 'OVERRUN':
        expenditure_ratio = random.uniform(1.08, 1.42)
    elif pattern == 'HIGH_UTILIZATION':
        expenditure_ratio = random.uniform(0.98, 1.08)
    elif pattern == 'MULTI_SIGNAL':
        sanction = round(base_amount * random.uniform(2.5, 4.2), -3)
        delay_days = random.randint(90, 320)
        expenditure_ratio = random.uniform(1.12, 1.55)
    elif pattern == 'DUPLICATE':
        name = 'Community Hall Renovation'
        category = 'Community Infrastructure'
        state = 'Maharashtra'
        district = 'Pune'
        expenditure_ratio = random.uniform(0.6, 0.95)
    elif pattern == 'DATA_QUALITY':
        expenditure_ratio = random.uniform(0.1, 0.4)

    actual = expected + timedelta(days=delay_days)
    status = 'Completed' if delay_days < 30 else 'Delayed'
    row = {
        'project_code': f'MPLAD-{index:04d}',
        'project_name': name,
        'state': state,
        'district': district,
        'constituency': f'{district} Parliamentary Constituency',
        'agency': random.choice(AGENCIES),
        'project_category': category,
        'sanction_amount': sanction,
        'expenditure': round(sanction * expenditure_ratio, -3),
        'sanction_date': sanction_date.isoformat(),
        'expected_completion_date': expected.isoformat(),
        'actual_completion_date': actual.isoformat(),
        'status': status,
        'demonstration_pattern': pattern,
    }

    if pattern == 'DATA_QUALITY':
        if index % 2:
            row['expenditure'] = None
        else:
            row['expected_completion_date'] = 'not-a-date'

    rows.append(row)

raw_df = pd.DataFrame(rows)

sanctioned_df = raw_df.rename(columns={
    'project_code': 'Work ID',
    'project_name': 'Work Description',
    'state': 'State',
    'district': 'IDA',
    'constituency': 'Constituency',
    'project_category': 'Work category',
    'agency': "Hon'ble Members of Parliament",
    'sanction_amount': 'Sanction Amount ( ₹ )',
    'expenditure': 'Amount Disbursed ( ₹ )',
    'sanction_date': 'Sanction Date',
    'expected_completion_date': 'Expected Completion Date',
    'actual_completion_date': 'Completion Date',
    'status': 'Work Status',
})

completed_df = raw_df.rename(columns={
    'project_code': 'Work ID',
    'project_name': 'Work Description',
    'state': 'State',
    'district': 'IDA',
    'constituency': 'Constituency',
    'project_category': 'Work category',
    'agency': "Hon'ble Members of Parliament",
    'sanction_amount': 'Sanction Amount ( ₹ )',
    'expenditure': 'Amount Disbursed ( ₹ )',
    'sanction_date': 'Sanction Date',
    'expected_completion_date': 'Expected Completion Date',
    'actual_completion_date': 'Completion Date',
    'status': 'Work Status',
})
completed_df['Payment Status'] = completed_df['Work Status']
completed_df['Vendor Name'] = 'Demo Vendor ' + completed_df['Work ID'].astype(str)

exp_df = raw_df.rename(columns={
    'project_code': 'Work ID',
    'project_name': 'Work Description',
    'state': 'State',
    'district': 'IDA',
    'constituency': 'Constituency',
    'project_category': 'Work category',
    'agency': "Hon'ble Members of Parliament",
    'sanction_amount': 'Sanction Amount ( ₹ )',
    'expenditure': 'Amount Disbursed ( ₹ )',
    'sanction_date': 'Sanction Date',
    'expected_completion_date': 'Expected Completion Date',
    'actual_completion_date': 'Completion Date',
    'status': 'Work Status',
})
exp_df['Payment Status'] = exp_df['Work Status']
exp_df['Vendor Name'] = 'Demo Vendor ' + exp_df['Work ID'].astype(str)
exp_df['Fund Disbursed Amount ( ₹ )'] = exp_df['Amount Disbursed ( ₹ )']


# Build a deterministic allocation workbook keyed by state + MP + constituency.
mp_rows = []
seen = set()
for _, row in raw_df.iterrows():
    key = (row['state'], row['agency'], row['constituency'])
    if key in seen:
        continue
    seen.add(key)
    mp_rows.append({
        'Work ID': f'ALLOC-{len(mp_rows):04d}',
        'Work': f'MP allocation context for {row["agency"]}',
        'State': row['state'],
        'IDA': row['district'],
        'Constituency': row['constituency'],
        "Hon'ble Members of Parliament": row['agency'],
        'Allocated AMOUNT ( ₹ )': round(row['sanction_amount'] * random.uniform(0.08, 0.18), -3),
    })

allocation_df = pd.DataFrame(mp_rows)

# Build a calamity workbook with separate consent records.
calamity_rows = []
for index in range(60):
    state = random.choice(list(STATE_DISTRICTS))
    district = random.choice(STATE_DISTRICTS[state])
    calamity_type = random.choice(['Flood Relief', 'Cyclone Relief', 'Drought Relief'])
    calamity_name = f'{calamity_type} Assistance {index + 1:03d}'
    consent_date = (base_date + timedelta(days=random.randint(0, 450))).isoformat()
    consent_amount = round(random.uniform(300_000, 2_500_000), -3)
    calamity_rows.append({
        'State': state,
        'IDA': district,
        'Constituency': f'{district} Parliamentary Constituency',
        'Calamity Type': calamity_type,
        'Calamity Name': calamity_name,
        'Date of Consent': consent_date,
        'Consent Amount ( ₹ )': consent_amount,
    })
calamity_df = pd.DataFrame(calamity_rows)

# Ensure workbook headers are cleaned for the real workbook parser.
output_files = {
    'Works Sanctioned.xlsx': sanctioned_df[
        ['Work ID', 'Work Description', 'State', 'IDA', 'Constituency', 'Work category', "Hon'ble Members of Parliament",
         'Sanction Amount ( ₹ )', 'Amount Disbursed ( ₹ )', 'Sanction Date', 'Expected Completion Date', 'Completion Date', 'Work Status']
    ],
    'Works Completed.xlsx': completed_df[
        ['Work ID', 'Work Description', 'State', 'IDA', 'Constituency', 'Work category', "Hon'ble Members of Parliament",
         'Sanction Amount ( ₹ )', 'Amount Disbursed ( ₹ )', 'Sanction Date', 'Expected Completion Date', 'Completion Date', 'Work Status', 'Payment Status', 'Vendor Name']
    ],
    'Expenditure on Completed and On-going Works as on Date.xlsx': exp_df[
        ['Work ID', 'Work Description', 'State', 'IDA', 'Constituency', 'Work category', "Hon'ble Members of Parliament",
         'Sanction Amount ( ₹ )', 'Amount Disbursed ( ₹ )', 'Fund Disbursed Amount ( ₹ )', 'Sanction Date', 'Expected Completion Date', 'Completion Date', 'Work Status', 'Payment Status', 'Vendor Name']
    ],
    'Allocated Limit for Honble MPs.xlsx': allocation_df,
    'Amount consented for Calamity.xlsx': calamity_df,
}

for filename, frame in output_files.items():
    path = OUTPUT_DIR / filename
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        if filename == 'Allocated Limit for Honble MPs.xlsx':
            sheet_name = 'Allocated Limit'
        elif filename == 'Amount consented for Calamity.xlsx':
            sheet_name = 'Calamity Consent'
        elif filename == 'Works Sanctioned.xlsx':
            sheet_name = 'Works Sanctioned'
        elif filename == 'Works Completed.xlsx':
            sheet_name = 'Works Completed'
        else:
            sheet_name = 'Expenditure'
        # The production reader expects the first worksheet row to be a report
        # title and discovers the canonical header row below it.
        frame.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)

print(f'Generated synthetic demo workbooks in {OUTPUT_DIR}')
print(f'Rows: sanctioned={len(sanctioned_df)}, allocation={len(allocation_df)}, calamity={len(calamity_df)}')
print('Files written:', ', '.join(sorted(path.name for path in OUTPUT_DIR.glob('*.xlsx'))))
