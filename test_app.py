from fastapi.testclient import TestClient
from main import app
import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("os.path.exists")
@patch("pandas.read_csv")
def test_get_trends(mock_read_csv, mock_exists):
    mock_exists.return_value = True
    
    # Mock DataFrame
    mock_df = MagicMock()
    # Setup some dummy data
    data = {
        "item": ["Product A", "Product B"],
        "country": ["USA", "India"],
        "category": ["Electronics", "Fashion"],
        "trend_strength": [80, 60],
        "urls": ["['http://a.com']", "['http://b.com']"]
    }
    mock_df_obj = pd.DataFrame(data)
    mock_read_csv.return_value = mock_df_obj
    
    response = client.get("/trends")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["item"] == "Product A"

    # Test filter
    response = client.get("/trends?country=India")
    # Since we are mocking the dataframe return but not the filtering logic inside (which uses the returned DF),
    # the filtering logic in the endpoint WILL run on the dataframe we returned.
    # Pandas filtering works on the real DataFrame object we created.
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["country"] == "India"

@patch("os.path.exists")
@patch("pandas.read_csv")
def test_get_trends_nan_handling(mock_read_csv, mock_exists):
    mock_exists.return_value = True
    
    # Data with NaNs
    data = {
        "item": ["Product NaN"],
        "country": ["Global"],
        "market_type": [float("nan")], # This caused the error
        "trend_strength": [50],
         "urls": ["[]"]
    }
    mock_df_obj = pd.DataFrame(data)
    mock_read_csv.return_value = mock_df_obj
    
    response = client.get("/trends")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json[0]["market_type"] is None

@patch("os.path.exists")
def test_get_trends_missing_file(mock_exists):
    mock_exists.return_value = False
    response = client.get("/trends")
    assert response.status_code == 404



@patch("festival_product_discovery.run_pipeline")
@patch("festival_product_discovery._load_existing_results")
@patch("builtins.open")
@patch("json.dump")
def test_trigger_festival_fetch(mock_json_dump, mock_open, mock_load, mock_run):
    mock_run.return_value = [{"product": "test"}]
    mock_load.return_value = []
    
    # Mock open context manager
    mock_result_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_result_file
    
    payload = {
        "countries": ["India"],
        "festival_filter": {"India": ["Diwali"]}
    }
    
    response = client.post("/festivals/fetch", json=payload)
    assert response.status_code == 200
    assert "India" in response.json()["message"]
    
    # Verify run_pipeline called with correct args
    # Note: sets are unordered, so equating sets is robust.
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args.kwargs['target_countries'] == {"India"}
    assert call_args.kwargs['festival_filter'] == {"India": {"Diwali"}}
