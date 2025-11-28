"""PMP command line interface."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from pmp.backends import load_backend
from pmp.output import OutputFormatType
from pmp.config import (
    ConfigManager,
    dumps as dump_config,
    parse_value,
    parse_profile_options,
)
from pmp.errors import ConfigError, PMPError
from pmp.output import print_get, print_list
from pmp.services import PromptService
from pmp.utils import parse_tags, read_content


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
    get_parser.add_argument("--format", choices=OutputFormatType, default="raw")

    update_parser = subparsers.add_parser("update", help="Update an existing prompt")
    update_parser.add_argument("name")
    _add_content_flags(update_parser)
    _add_metadata_flags(update_parser)

    delete_parser = subparsers.add_parser("delete", help="Delete a prompt or version")
    delete_parser.add_argument("name")
    delete_parser.add_argument("--version", type=int)
    delete_parser.add_argument(
        "--force", action="store_true", help="Delete all versions"
    )

    list_parser = subparsers.add_parser("list", help="List prompts")
    list_parser.add_argument(
        "--long", action="store_true", help="Display human-readable table"
    )
    list_parser.add_argument("--format", choices=OutputFormatType, default="raw")
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
    backend_settings = manager.resolve_backend(
        backend_override=args.backend, profile_override=args.profile
    )
    backend = load_backend(backend_settings.name, backend_settings.options)
    service = PromptService(backend)

    if args.command == "add":
        content = read_content(args.file, args.content)
        metadata_tags = parse_tags(args.tag)
        record = service.add_prompt(args.name, content, metadata_tags, args.model)
        print(f'prompt "{args.name}" version {record["version"]} created')
        return 0

    elif args.command == "get":
        record = service.get_prompt(args.name, args.version)
        print_get(record, args.format)
        return 0

    elif args.command == "update":
        content = read_content(args.file, args.content)
        tags = parse_tags(args.tag) if args.tag is not None else None
        record = service.update_prompt(args.name, content, tags, args.model)
        print(f'prompt "{args.name}" version {record["version"]} created')
        return 0

    elif args.command == "delete":
        record = service.delete_prompt(args.name, args.version, args.force)
        if "deleted_versions" in record:
            versions = ", ".join(str(v) for v in sorted(record["deleted_versions"]))
            print(f'prompt "{args.name}" deleted versions [{versions}]')
        else:
            print(f'prompt "{args.name}" version {record["version"]} deleted')
        return 0

    elif args.command == "list":
        prompts = service.list_prompts(args.tag, args.model)
        print_list(prompts, args.format, args.long)
        return 0

    else:
        raise PMPError(f'unknown command "{args.command}"')


def handle_config(args: argparse.Namespace, unknown: List[str]) -> None:
    manager = ConfigManager()
    if args.config_command == "set":
        value = parse_value(args.value)
        manager.set_value(args.key, value)
        manager.save()
        print(f"{args.key} = {args.value}")
        return
    elif args.config_command == "get":
        value = manager.get_value(args.key)
        if value is None:
            raise ConfigError(f'key "{args.key}" is not set')
        print(value)
        return
    elif args.config_command == "list":
        print(dump_config(manager.data), end="")
        return
    elif args.config_command == "profile":
        handle_profile(manager, args, unknown)
        return
    else:
        raise PMPError(f'unknown config command "{args.config_command}"')


def handle_profile(
    manager: ConfigManager, args: argparse.Namespace, unknown: List[str]
) -> None:
    if args.profile_command == "add":
        options = parse_profile_options(unknown)
        profile = manager.ensure_profile(args.name)
        profile.clear()
        profile["backend"] = args.backend
        profile.update(options)
        manager.save()
        print(f'profile "{args.name}" updated')
        return
    elif args.profile_command == "use":
        manager.set_active_profile(args.name)
        manager.save()
        print(f'profile "{args.name}" activated')
        return
    else:
        raise PMPError(f'unknown profile command "{args.profile_command}"')


def _add_content_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--file", help="Read prompt content from file")
    parser.add_argument("--content", help="Inline prompt content")


def _add_metadata_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tag", action="append", help="Comma-separated tags (repeatable)"
    )
    parser.add_argument("--model", help="Associate prompt with a model")


def _allows_unknown(args: argparse.Namespace) -> bool:
    return (
        getattr(args, "command", None) == "config"
        and getattr(args, "config_command", None) == "profile"
        and getattr(args, "profile_command", None) == "add"
    )
