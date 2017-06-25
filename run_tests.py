#!/usr/bin/env python

from typing import List, Iterator, Tuple
from contextlib import contextmanager
import glob
import os
import os.path
import shutil
import subprocess
import sys
import textwrap

CORE_FILES = [
        "./src/typing_extensions.py", 
        "./tests/test_typing_extensions.py"
]
TEST_DIR = "test_data"

if sys.platform.startswith('win32'):
    PYTHON = "py -3"
else:
    PYTHON = "python3"


def get_test_dirs() -> List[str]:
    """Get all folders to test inside TEST_DIR."""
    return list(glob.glob(os.path.join(TEST_DIR, "*")))


@contextmanager
def temp_copy(src_files: List[str], dest_dir: str) -> Iterator[None]:
    """
    A context manager that temporarily copies the given files to the
    given destination directory, and deletes those temp files upon
    exiting.
    """
    # Copy
    for src_path in src_files:
        shutil.copy(src_path, dest_dir)

    yield

    # Delete
    for src_path in src_files:
        dst_path = os.path.join(dest_dir, os.path.basename(src_path))
        os.remove(dst_path)


@contextmanager
def change_directory(dir_path: str) -> Iterator[None]:
    """
    A context manager that temporarily changes the working directory
    to the specified directory, and changes back to the original
    upon exiting.
    """
    original = os.getcwd()
    os.chdir(dir_path)

    yield

    os.chdir(original)


def run_shell(command: str) -> Tuple[bool, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join([os.getcwd(), env["PYTHONPATH"], env["PATH"]])
    out = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            env=env)
    success = out.returncode == 0
    stdout = '' if out.stdout is None else out.stdout.decode('utf-8')
    return (success, stdout)


def main() -> None:
    test_dirs = get_test_dirs()
    for test_dir in test_dirs:
        _, version_number = test_dir.split('-')
        print("Testing Python {}".format(version_number))

        with temp_copy(CORE_FILES, test_dir), change_directory(test_dir):
            success, output = run_shell("{} {} {}".format(
                PYTHON, 
                "test_typing_extensions.py",
                version_number))
            if success:
                print("   All tests passed!")
            else:
                print(textwrap.indent(output, "    "))


if __name__ == '__main__':
    main()

