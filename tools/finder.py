#!/usr/bin/env python3
"""
Robot Framework Library Finder
"""
import argparse
import json
import logging
import re
import sys
from pathlib import Path

from robot.errors import DataError
from robot.libdocpkg import LibraryDocumentation

BLACKLIST = ("__pycache__",)
INIT_FILES = ("__init__.robot", "__init__.txt")
EXTENSIONS = (".robot", ".resource", ".txt")


class LibraryFinder:
    def __init__(self, config=None, ignore=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.ignore = ignore or []

    def find(self, root):
        paths, stack = set(), [Path(r) for r in root]

        while stack:
            path = stack.pop(0)
            self.logger.debug("Checking: %s", path)

            try:
                if self.should_ignore(path):
                    self.logger.debug("Ignoring: %s", path)
                    continue

                if path.is_dir():
                    if self.is_module_library(path):
                        paths.add(path)
                        paths |= {
                            file
                            for file in path.glob("**/*")
                            if self.is_resource_file(path)
                        }
                    else:
                        for child in path.iterdir():
                            stack.append(child)
                elif self.is_keyword_file(path):
                    paths.add(path)
            except DataError as err:
                self.logger.info("Parsing failed: %s", err)

        return [str(path) for path in sorted(paths)]

    def should_ignore(self, path):
        return path in self.ignore or path.name in BLACKLIST

    @classmethod
    def is_module_library(cls, path):
        return (path / "__init__.py").is_file() and cls.has_keywords(path)

    @classmethod
    def is_keyword_file(cls, path):
        return cls.is_library_file(path) or cls.is_resource_file(path)

    @classmethod
    def is_library_file(cls, path):
        return (
            path.suffix == ".py"
            and path.name != "__init__.py"
            and cls.has_keywords(path)
        )

    @staticmethod
    def is_resource_file(path):
        if path.name in INIT_FILES or path.suffix not in EXTENSIONS:
            return False

        def contains(data, pattern):
            return bool(re.search(pattern, data, re.MULTILINE | re.IGNORECASE))

        with open(path, "r", encoding="utf-8", errors="ignore") as fd:
            data = fd.read()
            has_keywords = contains(data, r"^\*+\s*((?:User )?Keywords?)")
            has_tasks = contains(data, r"^\*+\s*(Test Cases?|Tasks?)")
            return not has_tasks and has_keywords

    @staticmethod
    def has_keywords(path):
        return bool(LibraryDocumentation(str(path)).keywords)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("paths", help="Input directory path(s)", type=Path, nargs="+")
    parser.add_argument(
        "-o", "--output", help="Output for library list", type=Path, default=None
    )
    parser.add_argument(
        "-i",
        "--ignore",
        help="Ignore given path",
        action="append",
        default=[],
        type=Path,
    )
    parser.add_argument(
        "-v", "--verbose", help="Be more talkative", action="store_true"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    finder = LibraryFinder(args.paths, args.ignore)
    libraries = finder.find(args.paths)

    output = json.dumps(libraries, indent=2)
    if args.output:
        with open(output, "w") as fd:
            fd.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
