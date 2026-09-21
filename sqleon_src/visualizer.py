# Copyright (C) 2026 BasaltDev
# SPDX-License-Identifier: GPL-3.0-only

import argparse
import json
import pathlib
import sys
from typing import Any


def visualize(database: dict[str, dict[str, Any]]):
    for table, keys in database.items():
        total_length = len(table)
        result_string = ""
        keys_result_string = ""
        temp_krs = ["", "", ""]
        for key in keys:
            key_length = len(key)
            if not keys_result_string.startswith("│"):
                keys_result_string += "│"
            elements = keys[key]["elements"]
            for value in elements:
                if len(str(value)) > key_length:
                    key_length = len(str(value))
            keys_result_string += f" {key: <{key_length}} │"
            temp_krs[0] += f"{'':─<{key_length+2}}┬"
            temp_krs[1] += f"{'':─<{key_length+2}}┼"
            temp_krs[2] += f"{'':─<{key_length+2}}┴"
            total_length += key_length + 1
        temp_krs[0] = temp_krs[0][:-1]
        temp_krs[1] = temp_krs[1][:-1]
        temp_krs[2] = temp_krs[2][:-1]
        for i in range(len(keys[list(keys.keys())[0]]["elements"])):  # noqa: RUF015
            keys_result_string += f"\n├{temp_krs[1]}┤\n"
            keys_result_string += "│"
            for key, info in keys.items():
                value = info["elements"][i]
                key_length = len(key)
                for v in info["elements"]:
                    if len(str(v)) > key_length:
                        key_length = len(str(v))
                keys_result_string += f" {value!s: <{key_length}} │"
        result_string += f"╭{'':─^{total_length}}╮\n"
        result_string += f"│{f'TABLE `{table}`': ^{total_length}}│\n"
        result_string += f"├{temp_krs[0]}┤\n"
        result_string += keys_result_string
        result_string += f"\n╰{temp_krs[2]}╯"
        print(result_string)

if __name__ == "__main__":
    argpsr = argparse.ArgumentParser("SQLeon")
    argpsr.add_argument("db_file", help="The SQLeon database to visualize")
    args = argpsr.parse_args()
    db_path = pathlib.Path(args.db_file)
    if not db_path.exists():
        print(f"Error: no such file `{db_path}`")
        sys.exit(1)
    with db_path.open(encoding="utf-8") as f:
        database = json.load(f)
    visualize(database)