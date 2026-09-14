import sys
from supertool.cli_config_engine import CLIEngine, ConfigEngine
from supertool.super_path import super_path, SuperPath
from supertool.async_task_runner import TaskRunner
from supertool.data_transformer import DataTransformer

def main():
    config = ConfigEngine()
    
    default_config = super_path("config.json")
    if default_config.exists():
        config.load_file(str(default_config))
    config.load_env(prefix="APP_")

    cli = CLIEngine(
        name="supertool",
        description="Unified CLI interface integrating SuperPath, ConfigEngine, TaskRunner, and DataTransformer."
    )
    
    cli.add_argument("-c", "--config", help="Path to custom JSON configuration file")
    cli.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    # --- Subcommand: info ---
    @cli.command("info", help_text="Inspect current workspace or target path details")
    def handle_info(path=".", verbose=False, config=None, **kwargs):
        target = super_path(path)
        print(f"Path: {target}")
        print(f"Exists: {target.exists()}")
        if target.exists():
            print(f"Type: {'Directory' if target.is_dir() else 'File'}")
            print(f"Size: {target.size()} bytes")
            if verbose and target.is_file():
                print(f"Extension: {target.ext}")
                print(f"Parent: {target.parent}")
                print(f"SHA-256: {target.hash()}")

    cli.add_subcommand_arg("info", "path", nargs="?", default=".", help="Target path to inspect")

    # --- Subcommand: archive ---
    @cli.command("archive", help_text="Compress a target file or folder into an archive")
    def handle_archive(src, dest=None, format="zip", config=None, **kwargs):
        source_path = super_path(src)
        if not source_path.exists():
            print(f"Error: Source path '{src}' does not exist.", file=sys.stderr)
            sys.exit(1)

        if format == "zip":
            output = source_path.zip(dest)
        elif format in ("tar", "tar.gz", "tar.bz2"):
            mode_map = {"tar": "w", "tar.gz": "w:gz", "tar.bz2": "w:bz2"}
            output = source_path.tar(dest, mode=mode_map[format])
        else:
            print(f"Error: Unsupported format '{format}'.", file=sys.stderr)
            sys.exit(1)

        print(f"Successfully archived '{source_path.name}' -> '{output}' ({output.size()} bytes)")

    cli.add_subcommand_arg("archive", "src", help="Source file or directory to archive")
    cli.add_subcommand_arg("archive", "-d", "--dest", help="Destination archive path")
    cli.add_subcommand_arg("archive", "-f", "--format", choices=["zip", "tar", "tar.gz", "tar.bz2"], default="zip", help="Archive compression format")

    # --- Subcommand: extract ---
    @cli.command("extract", help_text="Extract a ZIP or TAR archive to a target directory")
    def handle_extract(archive, dest=None, config=None, **kwargs):
        arc_path = super_path(archive)
        if not arc_path.exists():
            print(f"Error: Archive '{archive}' does not exist.", file=sys.stderr)
            sys.exit(1)

        if arc_path.ext == ".zip":
            out_dir = arc_path.unzip(dest)
        elif arc_path.name.endswith((".tar", ".tar.gz", ".tar.bz2", ".tgz")):
            out_dir = arc_path.untar(dest)
        else:
            print(f"Error: Unrecognized archive extension for '{arc_path.name}'.", file=sys.stderr)
            sys.exit(1)

        print(f"Successfully extracted '{arc_path.name}' -> '{out_dir}'")

    cli.add_subcommand_arg("extract", "archive", help="Path to archive file")
    cli.add_subcommand_arg("extract", "-d", "--dest", help="Target output directory")

    # --- Subcommand: config ---
    @cli.command("config", help_text="View or set active configuration settings")
    def handle_config_cmd(action="show", key=None, value=None, config=None, **kwargs):
        if action == "show":
            if key:
                val = config.get(key)
                print(f"{key} = {val}")
            else:
                print(f"Configuration Settings:\n{config._data}")
        elif action == "set":
            if not key or value is None:
                print("Error: Setting a config key requires both a key and a value.", file=sys.stderr)
                sys.exit(1)
            config.set(key, config._parse_env_value(value))
            save_dest = super_path(kwargs.get("config") or "config.json")
            config.save(str(save_dest))
            print(f"Updated '{key}' = {value} (saved to {save_dest})")

    cli.add_subcommand_arg("config", "action", choices=["show", "set"], nargs="?", default="show", help="Config action")
    cli.add_subcommand_arg("config", "--key", help="Key path (e.g. server.port)")
    cli.add_subcommand_arg("config", "--value", help="Value to assign")

    # --- Subcommand: run-tasks ---
    @cli.command("run-tasks", help_text="Execute parallel file processing via Async Task Runner")
    def handle_run_tasks(path=".", concurrency=5, retries=1, config=None, **kwargs):
        target_dir = super_path(path)
        if not target_dir.exists() or not target_dir.is_dir():
            print(f"Error: Target directory '{path}' does not exist.", file=sys.stderr)
            sys.exit(1)

        max_c = int(config.get("runner.concurrency", concurrency))
        runner = TaskRunner(max_concurrency=max_c)

        files = target_dir.list_files()
        if not files:
            print(f"No files found in '{target_dir}'.")
            return

        def process_file(sp: SuperPath):
            return {"file": sp.name, "size": sp.size(), "hash": sp.hash("sha256")[:8]}

        for sp in files:
            runner.add_task(name=f"Process-{sp.name}", func=process_file, sp=sp, retries=int(retries))

        print(f"Enqueueing {len(files)} file processing tasks (Concurrency: {max_c})...")
        results = runner.run_sync()

        print("\n--- Task Execution Summary ---")
        for res in results:
            if res.success:
                print(f"[SUCCESS] {res.name} -> {res.value['hash']} ({res.duration:.4f}s)")
            else:
                print(f"[FAILED]  {res.name} -> {res.error}")

    cli.add_subcommand_arg("run-tasks", "path", nargs="?", default=".", help="Target directory for file tasks")
    cli.add_subcommand_arg("run-tasks", "--concurrency", default=5, type=int, help="Max concurrent workers")
    cli.add_subcommand_arg("run-tasks", "--retries", default=1, type=int, help="Task retry limit")

    # --- Subcommand: transform ---
    @cli.command("transform", help_text="Convert or filter dataset formats (JSON <-> CSV)")
    def handle_transform(src, output=None, fields=None, config=None, **kwargs):
        src_path = super_path(src)
        if not src_path.exists():
            print(f"Error: Source file '{src}' does not exist.", file=sys.stderr)
            sys.exit(1)

        if src_path.ext == ".json":
            transformer = DataTransformer.from_json(src_path)
        elif src_path.ext == ".csv":
            transformer = DataTransformer.from_csv(src_path)
        else:
            print(f"Error: Unsupported input format '{src_path.ext}'. Must be .json or .csv.", file=sys.stderr)
            sys.exit(1)

        if fields:
            selected_keys = [f.strip() for f in fields.split(",")]
            transformer.select(*selected_keys)

        out_path = super_path(output) if output else None

        if out_path and out_path.ext == ".csv":
            result = transformer.to_csv(destination=out_path)
        elif out_path and out_path.ext == ".json":
            result = transformer.to_json(destination=out_path)
        else:
            result = transformer.to_csv() if src_path.ext == ".json" else transformer.to_json()

        if out_path:
            print(f"Successfully transformed data: '{src_path.name}' -> '{out_path.name}'")
        else:
            print("\n--- Transformed Output ---")
            print(result)

    cli.add_subcommand_arg("transform", "src", help="Source JSON or CSV file")
    cli.add_subcommand_arg("transform", "-o", "--output", help="Output file path (.json or .csv)")
    cli.add_subcommand_arg("transform", "--fields", help="Comma-separated keys to select")

    # Ingest custom config via flag dynamically before dispatch
    parsed_args, _ = cli.parser.parse_known_args()
    if parsed_args.config:
        config.load_file(parsed_args.config)

    cli.run(config=config)

if __name__ == "__main__":
    main()
