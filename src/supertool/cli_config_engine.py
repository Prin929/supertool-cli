import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Callable, Optional

class ConfigEngine:
    def __init__(self):
        self._data: Dict[str, Any] = {}

    def load_file(self, filepath: str) -> None:
        p = Path(filepath)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                content = json.load(f)
                self._data.update(content)

    def load_env(self, prefix: str = "APP_") -> None:
        for k, v in os.environ.items():
            if k.startswith(prefix):
                config_key = k[len(prefix):].lower().replace("__", ".")
                self.set(config_key, self._parse_env_value(v))

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value

    def save(self, filepath: str) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4)

    def _parse_env_value(self, val: str) -> Any:
        if val.lower() == "true": return True
        if val.lower() == "false": return False
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val

class CLIEngine:
    def __init__(self, name: str, description: str):
        self.parser = argparse.ArgumentParser(prog=name, description=description)
        self.subparsers = self.parser.add_subparsers(dest="subcommand", help="Available subcommands")
        self.subcommand_parsers: Dict[str, argparse.ArgumentParser] = {}
        self.handlers: Dict[str, Callable] = {}

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    def command(self, name: str, help_text: str):
        sub_parser = self.subparsers.add_parser(name, help=help_text)
        self.subcommand_parsers[name] = sub_parser
        def decorator(func: Callable):
            self.handlers[name] = func
            return func
        return decorator

    def add_subcommand_arg(self, cmd_name: str, *args, **kwargs):
        if cmd_name in self.subcommand_parsers:
            self.subcommand_parsers[cmd_name].add_argument(*args, **kwargs)

    def run(self, config: Optional[ConfigEngine] = None):
        args = self.parser.parse_args()
        if args.subcommand in self.handlers:
            kwargs = vars(args)
            handler = self.handlers[args.subcommand]
            handler(config=config, **kwargs)
        else:
            self.parser.print_help()
