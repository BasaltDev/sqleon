# Copyright (C) 2026 BasaltDev
#
# SQLeon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
# 
# SQLeon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SQLeon. If not, see <https://www.gnu.org/licenses/>.

import argparse
import pathlib
import sys

from sqleon_src.interpreter import Interpreter

argpsr = argparse.ArgumentParser("SQLeon")
argpsr.add_argument("query_file", help="The SQLeon query to run")
argpsr.add_argument("--db", help="Database to run your SQLeon query on")
args = argpsr.parse_args()
query_path = pathlib.Path(args.query_file)
if not query_path.exists():
    print(f"Error: no such file `{query_path}`")
    sys.exit(1)
db_path = None
if args.db:
    db_path = pathlib.Path(args.db)
    if not db_path.exists():
        print(f"Error: no such file `{db_path}`")
        sys.exit(1)
Interpreter(query_path, db_path).interpret()
