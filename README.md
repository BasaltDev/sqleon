# SQLeon
<h3>A unique SQL-based database system and query language written in Python<br>
By BasaltDev</h3>

---

### Table of Contents
- [About](#about)
- [Features](#features)
- [Syntax](#syntax)
- [How to Run](#how-to-run)
- [License](#license)

<a name="about"></a>
## About
SQLeon is an SQL-based query language and database system built in Python.<br>

<a name="features"></a>
## Features

### Currently Implemented
- **JSON-based database format**: readable JSON-based database file format (`.sqleon`).
- **SQL-based syntax**: familiar query syntax with only a few tweaks.
- **Built-in Visualizer**: SQLeon comes with a built-in text-based database/table visualizer.
- **Custom DB and Query File Format**: `.sqleon` for databases, `.qsqleon` for queries.

### Work-In-Progress
- **More database operations**: Currently SQLeon only has tables, insertion, selection and dropping (as well as expressions). Things like aggregate functions, grouping and WHERE clauses are being worked on.

### Missing
- **More efficient, encrypted and compressed DB format**

<a name="syntax"></a>
## Syntax

### Operators
These are the current operators in SQLEON:

| Operator | Explanation | Syntax |
| - | - | - |
| `+` | Standard arithmetic addition operator | `a + b` |
| `-` | Standard arithmetic subtraction operator | `a - b` |
| `*` | Standard arithmetic multiplication operator | `a * b` |
| `/` | Standard arithmetic division operator | `a / b` |
| `%`, `MOD` | Standard arithmetic modulo operator. The `MOD` keyword functions differently from SQL, it works as a stand-in for the `%` operator, instead of being a function. | `a % b`, `a MOD b` |
| `=` | Standard ogical equality operator, returns a BOOLEAN value | `a = b` |
| `!=`, `<>` | Standard logical inequality operator, returns a BOOLEAN value | `a != b`, `a <> b` |
| `<`, `<=`, `>`, `>=` | Standard logical comparison operators, return BOOLEAN values | `a < b`, `a > b`, `a <= b`, `a >= b` |
| `AND` | Standard logical AND operator, works only on BOOLEAN values (or 0 and 1) and returns a BOOLEAN value | `a AND b` |
| `OR` | Standard logical OR operator, works only on BOOLEAN values (or 0 and 1) and returns a BOOLEAN value | `a OR b` |
| `BETWEEN` | Operator to check if a value is between to other values (only works on number values) | `a BETWEEN b AND c` |

<a name="syntax-types"></a>

### Types
There are currently 4 types in SQLeon:
- `INT` - average integer
- `BOOLEAN` - average boolean
- `VARCHAR(length)` - string type
- `DECIMAL(precision, scale)` - float type, precision = digits and scale = decimal places<br>
You can use these in [Table Creation](#syntax-tablecreation) and more.

<a name="syntax-tablecreation"></a>
### Table Creation
To create a table, you use the `CREATE TABLE name (column type constraint1 constraint2 ..., ...);` syntax. For example:

```sql
CREATE TABLE persons (
    id INT UNIQUE PRIMARY KEY,
    name VARCHAR(255),
    last_name VARCHAR(255) NOT NULL,
    age INT CHECK (age BETWEEN 1 AND 120)
);
```
Note that the parentheses are required.<br>

As you can see, the syntax is very SQL-like, which means it's readable. Column names are followed by a [type](#syntax-types) and any amount of [constraints](#syntax-tablecolumnconstraints).

<a name="syntax-tableinsertion"></a>

### Table Insertion
To insert a value into a table, you use the `INSERT INTO table (value1, value2, ...);` syntax.
Following the example in [Table Creation](#syntax-tablecreation):

```sql
INSERT INTO persons (1, 'John', 'Doe', 42);
```

This syntax differs from SQL by not using the VALUES keyword. Note that parentheses are also required here, and there must be at least 1 value inserted.

<a name="syntax-dropping"></a>

### Dropping

Dropping is the act of removing something, like a table, column or even a database.

#### Table Dropping

To drop a table, you use the familiar `DROP TABLE name;` syntax. Following the example from [Table Creation](#syntax-tablecreation):

```sql
DROP TABLE persons;
```

The syntax does not differ from SQL at all.

<a name="syntax-tablecolumnconstraints"></a>

### Table Column Constraints
Constraints are used to validate data when inserting values into tables.

Currently there are 4 constraint types:

| Syntax | Explanation |
| - | - |
| `NOT NULL` | Checks if the value being inserted into the column is not null. |
| `UNIQUE` | Makes sure the value being inserted into the column is unique. |
| `CHECK (condition)` | Checks if the condition specified is true for the value being inserted into the column. |
| `PRIMARY KEY` | No real use yet, it's just there for people who use SQL like this. |

<a name="how-to-run"></a>
## How to Run
### **Step 1:** Make sure you have Python installed.
If you don't have python installed, you can get it from [www.python.org](https://www.python.org/).
### **Step 2:** Clone the GitHub repository.
```Bash
git clone https://github.com/BasaltDev/SQLeon
cd SQLeon
```
### **Step 3:** Run SQLeon
You can run SQLeon using the following command:
```Powershell
python sqleon.py --help
```
You can figure out the rest from there.

---
<a name="license"></a>
## License
Licensed under the [GNU GPLv3 license](https://www.gnu.org/licenses/gpl-3.0.html). The license can be found in [LICENSE](LICENSE).

In short, you can use, modify and share this code however you want. However, if you distribute your own version of it, you must keep it open-source and release your changes under the same GPLv3 license.