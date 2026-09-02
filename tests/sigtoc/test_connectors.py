import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from shared.models import Source, IntelDiscipline, AdmiraltyReliability, AdmiraltyCredibility, CollectionTasking, TaskingStatus
from sigtoc.connectors.state_dept import StateDeptConnector
from sigtoc.connectors.gdelt import GDELTConnector
from sigtoc.connectors.gdacs_connector import GDACSConnector
from sigtoc.connectors.health_notices import HealthNoticesConnector
from sigtoc.collection.manager import CollectionManager

@pytest.fixture
def mock_source():
    return Source(
        source_id="test_source",
        name="Test Source",
        discipline=IntelDiscipline.OSINT,
        reliability=AdmiraltyReliability.A,
        connector_class="TestConnector"
    )

@pytest.mark.asyncio
async def test_state_dept_connector_parses_advisory(mock_source):
    connector = StateDeptConnector(mock_source)
    mock_response = Response(200, json={
        "Data": [
            {
                "TravelAdvisory": {
                    "iso_code": "SA",
                    "advisory_date": "2023-10-01",
                    "advisory_text": "Level 2: Exercise Increased Caution in Saudi Arabia.",
                    "url": "https://travel.state.gov/test"
                }
            }
        ]
    })
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        signals = await connector.collect()
        
        assert len(signals) == 1
        assert signals[0].credibility == AdmiraltyCredibility.PROBABLY_TRUE
        assert signals[0].origin_key == "state_dept_SA_2023-10-01"
        assert signals[0].raw_text == "Level 2: Exercise Increased Caution in Saudi Arabia."

@pytest.mark.asyncio
async def test_gdelt_connector_parses_articles(mock_source):
    connector = GDELTConnector(mock_source)
    mock_response = Response(200, json={
        "articles": [
            {"url": "http://example.com/1", "title": "Test 1"},
            {"url": "http://example.com/2", "title": "Test 2"},
            {"url": "http://example.com/3", "title": "Test 3"}
        ]
    })
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        signals = await connector.collect(query="Saudi Arabia")
        
        assert len(signals) == 3
        assert signals[0].credibility == AdmiraltyCredibility.POSSIBLY_TRUE
        assert signals[0].origin_key == "http://example.com/1"
        assert signals[1].origin_key == "http://example.com/2"

@pytest.mark.asyncio
async def test_gdacs_connector_parses_events(mock_source):
    connector = GDACSConnector(mock_source)
    xml_content = """<?xml version="1.0"?>
    <rss xmlns:gdacs="http://www.gdacs.org" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">
        <channel>
            <item>
                <title>Earthquake in Chile</title>
                <link>http://gdacs.org/eq123</link>
                <description>Magnitude 7.0 earthquake</description>
                <gdacs:eventtype>EQ</gdacs:eventtype>
                <gdacs:eventid>12345</gdacs:eventid>
                <gdacs:alertlevel>Red</gdacs:alertlevel>
                <gdacs:severity>7.0</gdacs:severity>
                <geo:lat>-30.0</geo:lat>
                <geo:long>-70.0</geo:long>
            </item>
        </channel>
    </rss>
    """
    mock_response = Response(200, text=xml_content)
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        signals = await connector.collect()
        
        assert len(signals) == 1
        assert signals[0].origin_key == "gdacs_EQ_12345"
        assert signals[0].geo.lat == -30.0
        assert signals[0].geo.lon == -70.0

@pytest.mark.asyncio
async def test_health_connector_parses_notices(mock_source):
    connector = HealthNoticesConnector(mock_source)
    html_content = """
    <html>
        <body>
            <div class="notice">
                <h3>Level 2: Polio in Country X</h3>
            </div>
        </body>
    </html>
    """
    mock_response = Response(200, text=html_content)
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        signals = await connector.collect()
        
        assert len(signals) == 1
        assert "cdc_Level 2: Polio in Country X_" in signals[0].origin_key
        assert signals[0].raw_text == "Level 2: Polio in Country X"

@pytest.mark.asyncio
async def test_collection_manager_runs_all_connectors(mock_source):
    connector1 = StateDeptConnector(mock_source)
    connector1.collect = AsyncMock(return_value=[MagicMock(), MagicMock()])
    
    connector2 = GDELTConnector(mock_source)
    connector2.collect = AsyncMock(return_value=[MagicMock()])
    
    manager = CollectionManager({"source1": connector1, "source2": connector2})
    
    taskings = [
        CollectionTasking(tasking_id="t1", indicator_id="i1", source_id="source1"),
        CollectionTasking(tasking_id="t2", indicator_id="i2", source_id="source2")
    ]
    
    signals = await manager.run_collection(taskings)
    
    assert len(signals) == 3
    connector1.collect.assert_called_once()
    connector2.collect.assert_called_once()
    
    assert taskings[0].status == TaskingStatus.CURRENT
    assert taskings[1].status == TaskingStatus.CURRENT

@pytest.mark.asyncio
async def test_connector_failure_returns_empty(mock_source):
    connector = StateDeptConnector(mock_source)
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("API Error")
        signals = await connector.collect()
        
        assert signals == []
