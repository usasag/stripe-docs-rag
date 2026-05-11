from app.tools.search_tool import SearchToolInput
from app.tools.source_ranker import SourceRankerInput
from app.tools.citation_sourcer import CitationSourcerInput

def test_search_tool_schema_generates_valid_json_schema() -> None:
    schema = SearchToolInput.model_json_schema()
    assert schema['type'] == 'object'
    assert 'query' in schema['properties']
    assert schema['properties']['query']['type'] == 'string'
    assert 'description' in schema['properties']['query']
    assert 'top_k' in schema['properties']

def test_source_ranker_schema_generates_valid_json_schema() -> None:
    schema = SourceRankerInput.model_json_schema()
    assert schema['type'] == 'object'
    assert 'query' in schema['properties']
    assert 'candidate_chunk_ids' in schema['properties']
    assert schema['properties']['candidate_chunk_ids']['type'] == 'array'
    assert schema['properties']['candidate_chunk_ids']['items']['type'] == 'string'

def test_citation_sourcer_schema_generates_valid_json_schema() -> None:
    schema = CitationSourcerInput.model_json_schema()
    assert schema['type'] == 'object'
    assert 'ranked_chunk_ids' in schema['properties']
    assert schema['properties']['ranked_chunk_ids']['type'] == 'array'
    assert 'max_citations' in schema['properties']
