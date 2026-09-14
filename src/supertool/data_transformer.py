import csv
import json
from io import StringIO
from typing import List, Dict, Any, Optional, Generator
from supertool.super_path import SuperPath

class DataTransformer:
    def __init__(self, data_stream: Generator[Dict[str, Any], None, None]):
        self._data_stream = data_stream
        self._selected_fields: Optional[List[str]] = None

    @classmethod
    def from_json(cls, source_path: SuperPath) -> "DataTransformer":
        def json_generator():
            with open(source_path.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    yield from data
                elif isinstance(data, dict):
                    yield data
        return cls(json_generator())

    @classmethod
    def from_csv(cls, source_path: SuperPath) -> "DataTransformer":
        def csv_generator():
            with open(source_path.path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                yield from reader
        return cls(csv_generator())

    def select(self, *fields: str) -> "DataTransformer":
        self._selected_fields = list(fields)
        return self

    def _apply_projection(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not self._selected_fields:
            return item
        return {k: item.get(k) for k in self._selected_fields if k in item}

    def to_csv(self, destination: Optional[SuperPath] = None) -> str:
        out_stream = open(destination.path, "w", newline="", encoding="utf-8") if destination else StringIO()
        writer = None

        try:
            for item in self._data_stream:
                filtered = self._apply_projection(item)
                if writer is None:
                    writer = csv.DictWriter(out_stream, fieldnames=filtered.keys())
                    writer.writeheader()
                writer.writerow(filtered)
            
            if isinstance(out_stream, StringIO):
                return out_stream.getvalue()
            return str(destination)
        finally:
            if destination:
                out_stream.close()

    def to_json(self, destination: Optional[SuperPath] = None) -> str:
        data = [self._apply_projection(item) for item in self._data_stream]
        if destination:
            with open(destination.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return str(destination)
        return json.dumps(data, indent=2)
