from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

random.seed(26102)

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
PATTERNS = ['NORMAL'] * 124 + ['DELAY'] * 16 + ['COST_ANOMALY'] * 12 + ['OVERRUN'] * 10 + ['HIGH_UTILIZATION'] * 8 + ['DUPLICATE'] * 6 + ['DATA_QUALITY'] * 4 + ['MULTI_SIGNAL'] * 8

rows: list[dict[str, object]] = []
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
        delay_days = random.randint(100, 360)
        expenditure_ratio = random.uniform(0.35, 0.82)
    elif pattern == 'COST_ANOMALY':
        sanction = round(base_amount * random.uniform(3.0, 5.5), -3)
        expenditure_ratio = random.uniform(0.45, 0.85)
    elif pattern == 'OVERRUN':
        expenditure_ratio = random.uniform(1.08, 1.42)
    elif pattern == 'HIGH_UTILIZATION':
        expenditure_ratio = random.uniform(0.98, 1.08)
    elif pattern == 'MULTI_SIGNAL':
        sanction = round(base_amount * random.uniform(2.5, 4.0), -3)
        delay_days = random.randint(140, 320)
        expenditure_ratio = random.uniform(1.12, 1.55)
    elif pattern == 'DUPLICATE':
        name = 'Community Hall Renovation'
        category = 'Community Infrastructure'
        state = 'Maharashtra'
        district = 'Pune'
        expenditure_ratio = random.uniform(0.6, 0.95)

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

output = Path(__file__).resolve().parents[1] / 'sample_data' / 'mplads_demo_180.csv'
pd.DataFrame(rows).to_csv(output, index=False)
print(f'wrote {len(rows)} rows to {output}')
