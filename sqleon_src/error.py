# Copyright (C) 2026 BasaltDev
# SPDX-License-Identifier: GPL-3.0-only

def error(message: str, position: tuple[int, int]) -> None:
    print(f"Error (line: {position[0]}, column: {position[1]}): {message}")
    raise Exception