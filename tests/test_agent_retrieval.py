from types import SimpleNamespace

import pytest

from cepio.agent_retrieval import resolve, search


def obj(identity, name, kind='Equipment', **properties):
    return SimpleNamespace(id=identity, name=name, type=kind, properties=properties)


@pytest.fixture
def objects():
    # Deliberately independent of all frozen challenge identifiers and answers.
    return [
        obj('plant-43-feed-pump-09', 'Feed Pump 09', plant_id='plant-43'),
        obj('plant-44-feed-pump-09', 'Feed Pump 09', plant_id='plant-44'),
        obj('plant-43-feed-pump-10', 'Feed Pump 10', plant_id='plant-43'),
        obj('JOB-801', 'Replace seal', 'WorkOrder', equipment_id='plant-43-feed-pump-09',
            scenario_id='CASE-617', status='open'),
        obj('JOB-802', 'Replace seal', 'WorkOrder', equipment_id='plant-44-feed-pump-09',
            scenario_id='CASE-618', status='completed'),
        obj('DOC-902', 'Inspection', 'Document', scenario_id='CASE-618', note='CASE-6170'),
    ]


def test_identity_normalizes_format_and_zero_padding_without_guessing(objects):
    assert resolve(objects, 'Plant 43 Feed Pump 9').id == 'plant-43-feed-pump-09'
    assert resolve(objects, 'plant-44-feed-pump-09').id == 'plant-44-feed-pump-09'
    assert resolve(objects, 'Plant 43 Feed Pump 99') is None


def test_duplicate_names_and_aliases_fail_closed(objects):
    with pytest.raises(ValueError, match='Ambiguous identity'):
        resolve(objects, 'Feed Pump 09')
    objects[0].properties['aliases'] = {'historian': 'P-909'}
    objects[1].properties['aliases'] = {'historian': 'P-909'}
    with pytest.raises(ValueError, match='Ambiguous identity'):
        resolve(objects, 'P-909')


def test_exact_alias_precedes_display_name(objects):
    objects[0].properties['source_tag'] = 'Feed Pump 09'
    assert resolve(objects, 'Feed Pump 09').id == objects[0].id


def test_canonical_identifier_anchors_exclude_other_plants(objects):
    result = search(objects, 'plant-43 feed pump 9', None, 50)
    assert result[0].id == 'plant-43-feed-pump-09'
    assert {o.id for o in result} == {'plant-43-feed-pump-09', 'JOB-801'}


def test_scenario_anchor_does_not_match_shared_numeric_tokens_or_prefixes(objects):
    assert [o.id for o in search(objects, 'CASE-617', None, 50)] == ['JOB-801']


def test_type_validation_and_typed_search(objects):
    assert [o.id for o in search(objects, 'plant-43 open', 'WorkOrder', 20)] == ['JOB-801']
    with pytest.raises(ValueError, match='available types: Document, Equipment, WorkOrder'):
        search(objects, 'open', 'scenario', 20)


def test_limits_and_order_are_deterministic(objects):
    assert [o.id for o in search(objects, '', None, 2)] == ['DOC-902', 'JOB-801']
    assert [o.id for o in search(reversed(objects), '', None, 2)] == ['DOC-902', 'JOB-801']
