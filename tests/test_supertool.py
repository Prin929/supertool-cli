
import json
import pytest
from supertool.super_path import super_path
from supertool.cli_config_engine import ConfigEngine
from supertool.async_task_runner import TaskRunner
from supertool.data_transformer import DataTransformer

def test_super_path_operations(tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello World!")
    
    sp = super_path(test_file)
    assert sp.exists()
    assert sp.is_file()
    assert sp.size() > 0
    assert sp.ext == ".txt"

def test_config_engine(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"server": {"port": 8080}}))
    
    config = ConfigEngine()
    config.load_file(str(cfg_file))
    
    assert config.get("server.port") == 8080
    config.set("server.port", 9000)
    assert config.get("server.port") == 9000

def test_task_runner():
    runner = TaskRunner(max_concurrency=2)
    runner.add_task("test_task", lambda x: x * 2, 5, retries=1)
    
    results = runner.run_sync()
    assert len(results) == 1
    assert results[0].success
    assert results[0].value == 10

def test_data_transformer(tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps([{"name": "Alice", "role": "dev"}, {"name": "Bob", "role": "ops"}]))
    
    sp = super_path(json_file)
    transformer = DataTransformer.from_json(sp).select("name")
    
    csv_out = transformer.to_csv()
    assert "name" in csv_out
    assert "role" not in csv_out
