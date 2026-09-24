from app.ml.integration import integrate_files


def _csv(path, rows):
    path.write_text('project_id,project_name,state,district,constituency,mp_name,sanction_amount,expenditure\n' + '\n'.join(','.join(map(str, row)) for row in rows), encoding='utf-8')


def test_project_id_match_beats_context_difference(tmp_path):
    sanctioned, expenditure = tmp_path / 'sanctioned.csv', tmp_path / 'expenditure.csv'
    _csv(sanctioned, [('W1', 'Drain repair', 'Bihar', 'Patna', 'Patna', 'MP A', 100, 0)])
    _csv(expenditure, [('W1', 'Drain work renamed', 'Bihar', 'Patna', 'Patna', 'MP A', 0, 75)])
    data, summary = integrate_files([sanctioned, expenditure], roles={sanctioned.name: 'SANCTIONED_WORKS', expenditure.name: 'EXPENDITURE'})
    assert summary['matched_expenditure'] == 1 and data.iloc[0]['expenditure'] == 75


def test_context_fallback_and_ambiguous_context_are_distinguished(tmp_path):
    sanctioned, completed = tmp_path / 'sanctioned.csv', tmp_path / 'completed.csv'
    _csv(sanctioned, [('W1', 'Road', 'Bihar', 'Patna', 'Patna', 'MP A', 100, 0), ('W2', 'Road', 'Bihar', 'Patna', 'Patna', 'MP A', 200, 0)])
    _csv(completed, [('', 'Road', 'Bihar', 'Patna', 'Patna', 'MP A', 0, 0)])
    _, summary = integrate_files([sanctioned, completed], roles={sanctioned.name: 'SANCTIONED_WORKS', completed.name: 'COMPLETED_WORKS'})
    assert summary['matched_completed'] == 0
    assert summary['ambiguous_matches'][0]['reason'] == 'NON_UNIQUE_CONTEXT_KEY'

def test_real_workbooks_have_expected_roles_and_join_coverage():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'demo_data'
    paths = [root / name for name in [
        'Works Sanctioned.xlsx', 'Works Completed.xlsx',
        'Expenditure on Completed and On-going Works as on Date.xlsx',
        'Allocated Limit for Honble MPs.xlsx',
    ]]
    unified, summary = integrate_files(paths)

    assert len(unified) > 0
    assert summary['matched_completed'] >= 0
    assert summary['matched_expenditure'] >= 0
    assert summary['allocation_matched'] >= 0
    assert {item['detected_role'] for item in summary['datasets']} == {'SANCTIONED_WORKS', 'COMPLETED_WORKS', 'EXPENDITURE', 'MP_ALLOCATION'}
    assert 'source_datasets' in unified.columns
