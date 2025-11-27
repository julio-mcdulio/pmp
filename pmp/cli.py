 """PMP command line interface."""

 from __future__ import annotations

 import argparse
 import sys
 from typing import Any, Dict, List, Optional, Sequence

 from .backends import load_backend
 from .config import ConfigManager
 from .errors import ConfigError, PMPError
 from .output import as_json, as_yaml, render_table
 from .services import PromptService
 from .utils import parse_tags, read_content


 def build_parser() -> argparse.ArgumentParser:
     parser = argparse.ArgumentParser(prog="pmp", description="Prompt Management CLI")
     parser.add_argument("--profile", help="Override the active profile")
     parser.add_argument("--backend", help="Override backend name")
     subparsers = parser.add_subparsers(dest="command", required=True)

     add_parser = subparsers.add_parser("add", help="Add a new prompt")
     add_parser.add_argument("name")
     _add_content_flags(add_parser)
     _add_metadata_flags(add_parser)

     get_parser = subparsers.add_parser("get", help="Retrieve a prompt")
     get_parser.add_argument("name")
     get_parser.add_argument("--version", type=int)
     get_parser.add_argument("--format", choices=["raw", "json", "yaml"], default="raw")

     update_parser = subparsers.add_parser("update", help="Update an existing prompt")
     update_parser.add_argument("name")
     _add_content_flags(update_parser)
     _add_metadata_flags(update_parser)

     delete_parser = subparsers.add_parser("delete", help="Delete a prompt or version")
     delete_parser.add_argument("name")
     delete_parser.add_argument("--version", type=int)
     delete_parser.add_argument("--force", action="store_true", help="Delete all versions")

     list_parser = subparsers.add_parser("list", help="List prompts")
     list_parser.add_argument("--long", action="store_true", help="Display human-readable table")
     list_parser.add_argument("--format", choices=["raw", "json", "yaml"], default="raw")
     list_parser.add_argument("--tag", help="Filter by tag")
     list_parser.add_argument("--model", help="Filter by model")

     config_parser = subparsers.add_parser("config", help="Manage configuration")
     config_sub = config_parser.add_subparsers(dest="config_command", required=True)

     config_set = config_sub.add_parser("set", help="Set a config key")
     config_set.add_argument("key")
     config_set.add_argument("value")

     config_get = config_sub.add_parser("get", help="Get a config value")
     config_get.add_argument("key")

     config_sub.add_parser("list", help="Print entire config file")

     profile_parser = config_sub.add_parser("profile", help="Manage profiles")
     profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)

     profile_add = profile_sub.add_parser("add", help="Add or update a profile")
     profile_add.add_argument("name")
     profile_add.add_argument("--backend", required=True)

     profile_use = profile_sub.add_parser("use", help="Activate a profile")
     profile_use.add_argument("name")

     return parser


 def main(argv: Optional[Sequence[str]] = None) -> int:
     parser = build_parser()
     args, unknown = parser.parse_known_args(argv)
     try:
         if unknown and not _allows_unknown(args):
             parser.error(f"unrecognized arguments: {' '.join(unknown)}")
         if args.command == "config":
             handle_config(args, unknown)
             return 0
         return run_command(args)
     except PMPError as exc:
         print(f"error: {exc}", file=sys.stderr)
         sys.exit(getattr(exc, "exit_code", 1))


 def run_command(args: argparse.Namespace) -> int:
     manager = ConfigManager()
     backend_settings = manager.resolve_backend(backend_override=args.backend, profile_override=args.profile)
     backend = load_backend(backend_settings.name, backend_settings.options)
     service = PromptService(backend)

     if args.command == "add":
         content = read_content(args.file, args.content)
         metadata_tags = parse_tags(args.tag)
         record = service.add_prompt(args.name, content, metadata_tags, args.model)
         print(f'prompt "{args.name}" version {record["version"]} created')
         return 0

     if args.command == "get":
         record = service.get_prompt(args.name, args.version)
         _print_get(record, args.format)
         return 0

     if args.command == "update":
         content = read_content(args.file, args.content)
         tags = parse_tags(args.tag) if args.tag is not None else None
         record = service.update_prompt(args.name, content, tags, args.model)
         print(f'prompt "{args.name}" version {record["version"]} created')
         return 0

     if args.command == "delete":
         record = service.delete_prompt(args.name, args.version, args.force)
         if "deleted_versions" in record:
             versions = ", ".join(str(v) for v in sorted(record["deleted_versions"]))
             print(f'prompt "{args.name}" deleted versions [{versions}]')
         else:
             print(f'prompt "{args.name}" version {record["version"]} deleted')
         return 0

     if args.command == "list":
         prompts = service.list_prompts(args.tag, args.model)
         _print_list(prompts, args)
         return 0

     raise PMPError(f'unknown command "{args.command}"')  # pragma: no cover


 # --------------------------------------------------------------------------- IO
 def _print_get(record: Dict[str, Any], format_: str) -> None:
     if format_ == "raw":
         print(record["content"], end="" if record["content"].endswith("\n") else "\n")
     elif format_ == "json":
         print(as_json(record))
     else:
         print(as_yaml(record))


 def _print_list(prompts: List[Dict[str, Any]], args: argparse.Namespace) -> None:
     if args.format == "json":
         print(as_json(prompts))
         return
     if args.format == "yaml":
         print(as_yaml(prompts))
         return
     if args.long:
         rows = []
         for item in prompts:
             metadata = item.get("metadata", {})
             tags = ",".join(metadata.get("tags", []))
             rows.append(
                 [
                     item["name"],
                     str(item["latest_version"]),
                     tags,
                     metadata.get("model", "") or "",
                     item.get("updated_at", ""),
                 ]
             )
         if rows:
             print(
                 render_table(
                     rows,
                     headers=["NAME", "VERSION", "TAGS", "MODEL", "UPDATED"],
                 )
             )
         return
     for item in prompts:
         print(item["name"])


 # ---------------------------------------------------------------------- config
 def handle_config(args: argparse.Namespace, unknown: List[str]) -> None:
     manager = ConfigManager()
     if args.config_command == "set":
         value = _parse_value(args.value)
         manager.set_value(args.key, value)
         manager.save()
         print(f'{args.key} = {args.value}')
         return
     if args.config_command == "get":
         value = manager.get_value(args.key)
         if value is None:
             raise ConfigError(f'key "{args.key}" is not set')
         print(value)
         return
     if args.config_command == "list":
         print(manager.save() or "", end="")
         # manager.save wrote file, but we want to print content? Need to output dumps? mistake
