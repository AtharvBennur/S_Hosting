from app.ml.fraud_signals import DISCLAIMER, evaluate_signals, normalize_entity, vendor_analytics


def test_vendor_normalization_and_concentration_signal_are_safe():
    records = [{'id': index, 'project_code': f'P-{index}', 'project_name': f'Road {index}', 'vendor_name': 'M/s Example Pvt. Ltd.', 'sanction_amount': 100, 'expenditure': 90, 'utilization_ratio': .9} for index in range(3)]
    assert normalize_entity(' M/S Example Pvt. Ltd. ')['normalized_value'] == 'example'
    assert any(item['signal_code'] == 'VENDOR_CONCENTRATION' for item in evaluate_signals(records)[0])
    assert vendor_analytics(records)[0]['projects'] == 3


def test_duplicate_and_financial_signals_never_claim_confirmed_fraud():
    records = [{'id': 1, 'project_code': 'P 1', 'project_name': 'Drain repair', 'sanction_amount': 100, 'expenditure': 125, 'utilization_ratio': 1.25}, {'id': 2, 'project_code': 'p-1', 'project_name': 'Drain repair'}]
    signals = evaluate_signals(records)[1]
    assert {'DUPLICATE_PROJECT_IDENTIFIER', 'EXPENDITURE_ABOVE_SANCTION', 'EXCESSIVE_UTILIZATION'} <= {item['signal_code'] for item in signals}
    assert all(item['disclaimer'] == DISCLAIMER and 'proof of wrongdoing' in item['disclaimer'] for item in signals)


def test_payment_timing_and_repeated_work_signals_require_dates():
    records = [
        {
            'id': 1, 'project_code': 'P-1', 'project_name': 'Road repair',
            'vendor_name': 'Example', 'district': 'Dharwad',
            'sanction_date': '2025-01-10', 'payment_date': '2025-01-05',
            'actual_completion_date': '2025-01-20',
        },
        {
            'id': 2, 'project_code': 'P-2', 'project_name': 'Road repair',
            'vendor_name': 'Example', 'district': 'Dharwad',
            'sanction_date': '2025-01-15',
        },
    ]

    signals = evaluate_signals(records)
    codes = {item['signal_code'] for items in signals.values() for item in items}

    assert {'PAYMENT_BEFORE_SANCTION', 'POSSIBLE_PROJECT_SPLITTING', 'REPEATED_WORKS_SAME_YEAR'} <= codes


def test_invalid_numbers_do_not_create_financial_signals():
    signals = evaluate_signals([{
        'id': 1, 'project_code': 'P-1', 'sanction_amount': 'not numeric',
        'expenditure': float('inf'), 'utilization_ratio': float('nan'),
    }])

    assert not {item['signal_code'] for item in signals[1]} & {'EXPENDITURE_ABOVE_SANCTION', 'EXCESSIVE_UTILIZATION'}


def test_duplicate_payments_and_cross_year_repeated_works_are_review_signals():
    records = [
        {'id': 1, 'project_code': 'P-1', 'project_name': 'School repair', 'payment_reference': 'PAY-7', 'sanction_date': '2024-01-01'},
        {'id': 2, 'project_code': 'P-2', 'project_name': 'School repair', 'payment_reference': 'PAY-7', 'sanction_date': '2025-01-01'},
    ]

    signals = evaluate_signals(records)
    codes = {item['signal_code'] for items in signals.values() for item in items}

    assert {'DUPLICATE_PAYMENT_REFERENCE', 'REPEATED_WORKS_ACROSS_YEARS'} <= codes


