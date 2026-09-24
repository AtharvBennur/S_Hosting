from app.ml.compliance import evaluate_project, evaluate_run
import pandas as pd
import pytest


def test_compliance_returns_explainable_financial_findings():
    findings = evaluate_project({'project_id': 'P-1', 'project_code': 'P-1', 'sanction_amount': 100, 'expenditure': 125, 'utilization_ratio': 1.25})
    codes = {item['rule_code'] for item in findings}
    assert {'EXPENDITURE_EXCEEDS_SANCTION', 'UTILIZATION_ABOVE_THRESHOLD'} <= codes
    assert all({'rule_code', 'severity', 'title', 'explanation', 'evidence_fields', 'project_id', 'recommended_action'} <= set(item) for item in findings)


def test_compliance_reports_missing_source_coverage():
    findings = evaluate_run([], {'missing_source_coverage': ['EXPENDITURE']})
    assert findings[0]['rule_code'] == 'INCOMPLETE_SOURCE_COVERAGE'


@pytest.mark.parametrize('missing', [None, '', '   ', float('nan'), pd.NA])
def test_missing_values_are_null_safe(missing):
    findings = evaluate_project({'project_id': missing, 'sanction_amount': missing, 'expenditure': missing})
    assert {'MISSING_PROJECT_ID', 'MISSING_SANCTION_AMOUNT', 'MISSING_EXPENDITURE'} <= {item['rule_code'] for item in findings}


def test_invalid_numeric_value_is_treated_as_missing_not_a_crash():
    findings = evaluate_project({'project_code': 'P-1', 'sanction_amount': 'not-a-number', 'expenditure': 'bad'})
    assert {'MISSING_SANCTION_AMOUNT', 'MISSING_EXPENDITURE'} <= {item['rule_code'] for item in findings}
