# -*- coding: utf-8 -*-

import json
from pickle import Unpickler
import sys
import argparse
from argparse import ArgumentParser
from typing import Any, Dict, Optional
from .modules import load_modules
from .modules.machine import Machine
from .logger import configure_logging, get_logger
from .yaml import load_config
from structlog.typing import BindableLogger


def parse_args(args: list[str]) -> argparse.Namespace:
    # Putting args-parser in seperate function to make this testable
    arg_parser = ArgumentParser("Rookify")
    arg_parser.add_argument("--dry-run", action="store_true", dest="dry_run_mode")

    # Custom ReadAction to set 'all' if nothing is specified for --read-pickle
    class ReadAction(argparse.Action):
        def __call__(
            self,
            parser: ArgumentParser,
            namespace: argparse.Namespace,
            values: Optional[Any],
            option_string: Optional[str] = None,
        ) -> None:
            setattr(namespace, self.dest, values if values is not None else "all")

    # Custom ShowProgressAction to set 'all' if nothing is specified for --show-progress
    class ShowProgressAction(argparse.Action):
        def __call__(
            self,
            parser: ArgumentParser,
            namespace: argparse.Namespace,
            values: Optional[Any],
            option_string: Optional[str] = None,
        ) -> None:
            setattr(namespace, self.dest, values if values is not None else "all")

    arg_parser.add_argument(
        "--read-pickle",
        nargs="?",
        action=ReadAction,
        dest="read_pickle",
        metavar="<section>",
        help="Show the content of the pickle file. Default argument is 'all', you can also specify a section you want to look at.",
        required=False,
    )

    arg_parser.add_argument(
        "--show-progress",
        nargs="?",
        action=ShowProgressAction,
        dest="show_progress",
        metavar="<module>",
        help="Show progress of the modules. Default argument is 'all', you can also specify a module you want to get the progress status from.",
        required=False,
    )
    return arg_parser.parse_args(args)


def load_pickler(pickle_file_name: str) -> Any:
    with open(pickle_file_name, "ab+") as pickle_file:
        pickle_file.seek(0)
        states_data = Unpickler(pickle_file).load()
        return states_data


def sort_pickle_file(unsorted_states_data: Dict[str, Any]) -> Dict[str, Any]:
    # sort the pickle-file alfabetically
    iterable_dict = iter(unsorted_states_data)
    first_key = next(iterable_dict)
    data_values = unsorted_states_data[first_key]["data"]
    sorted_data_by_keys = {k: data_values[k] for k in sorted(data_values)}
    return sorted_data_by_keys


def read_pickle_file(
    args: argparse.Namespace, pickle_file_name: str, log: BindableLogger
) -> None:
    states_data = load_pickler(pickle_file_name)
    sorted_states_data = sort_pickle_file(states_data)

    # Check if a specific section should be listed
    if args.read_pickle != "all":
        if args.read_pickle not in sorted_states_data.keys():
            log.error(f"The section {args.read_pickle} does not exist")
        else:
            sorted_states_data = sorted_states_data[args.read_pickle]

    log.info(
        'Current state as retrieved from pickle-file: \n "{0}": {1}'.format(
            args.read_pickle, json.dumps(sorted_states_data, indent=4)
        )
    )


def main() -> None:
    args = parse_args(sys.argv[1:])

    # Load configuration file
    try:
        config: Dict[str, Any] = load_config("config.yaml")
    except FileNotFoundError as err:
        raise SystemExit(f"Could not load config: {err}")

    # Configure logging
    try:
        configure_logging(config["logging"])
    except Exception as e:
        raise SystemExit(f"Error configuring logging: {e}")
    # Get Logger
    log = get_logger()

    # Get Pickle File if configured in config.yaml
    pickle_file_name = config["general"].get("machine_pickle_file")
    if pickle_file_name is None:
        log.info("No pickle file was set in the configuration.")
    else:
        log.info(f"Pickle file set: {pickle_file_name}")

    # Get Pickle File if configured in config.yaml
    pickle_file_name = config["general"].get("machine_pickle_file")
    if pickle_file_name is None:
        log.info("No pickle file was set in the configuration.")
    else:
        log.info(f"Pickle file set: {pickle_file_name}")

    # If read_pickle is run and there is a picklefile, show the picklefiles contents.
    # NOTE: preflight mode (--dry-run) has no effect here, because no module actions are required.
    if args.read_pickle is not None and pickle_file_name is not None:
        read_pickle_file(args, pickle_file_name, log)
        return
    elif args.read_pickle is not None and pickle_file_name is None:
        log.info(
            "No pickle file configured to read from. Check if the pickle file exists and is configured in config.yaml"
        )
        return

    # If show_progress is run and there is a picklefile, show progress status based on picklefile contents
    # NOTE: this is always run in preflight-mode (migration shoudl not be executed)
    if args.show_progress is not None and pickle_file_name is not None:
        # Check if a specific mode should be targeted
        if args.show_progress != "all":
            print("TEST")
            print(args.show_progress)

        # TODO: implement module and method loading to let module check state itself
        return

    # TODO: should progress be checkable if no pickle file is present? Should rookify check the status by analyzing the source and traget machines state?
    elif args.show_progress is not None and pickle_file_name is None:
        log.info(
            "Currently rookify can only check the state of progress by analyzing the pickle file states."
        )
        return

    # Else run the rook migration
    else:
        log.debug("Executing Rookify")

        machine = Machine(config["general"].get("machine_pickle_file"))
        load_modules(machine, config)

        machine.execute(dry_run_mode=args.dry_run_mode)
