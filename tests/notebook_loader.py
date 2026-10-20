"""Pull plain Python out of the Fabric notebooks so it can be tested without Spark.

A notebook is a JSON file. This loader reads its code cells, keeps only the top-level
imports, functions and simple constants (the parts that need no Spark session), and runs
just those. Everything else in the notebook (Spark reads, writes, widgets) is skipped.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_notebook_symbols(relative_path, names=None):
    """Return a dict with the functions and constants defined at the top level of a notebook.

    names: optional list. If given, only those names (plus the imports they need) are returned.
    """
    nb = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    keep = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        try:
            tree = ast.parse("".join(cell["source"]))
        except SyntaxError:
            continue  # cells with notebook magics are not plain Python
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
                keep.append(node)
            elif isinstance(node, ast.Assign) and _is_plain_value(node.value):
                keep.append(node)
    ns = {}
    # imports first, so a function defined before its import cell still works
    for node in [n for n in keep if isinstance(n, (ast.Import, ast.ImportFrom))]:
        try:
            exec(compile(ast.Module([node], []), "<nb>", "exec"), ns)
        except ImportError:
            pass  # a Spark import on a machine without Spark: the tested functions do not use it
    for node in [n for n in keep if not isinstance(n, (ast.Import, ast.ImportFrom))]:
        exec(compile(ast.Module([node], []), "<nb>", "exec"), ns)
    if names:
        missing = [n for n in names if n not in ns]
        assert not missing, f"not found in {relative_path}: {missing}"
        return {n: ns[n] for n in names}
    return ns


def _is_plain_value(node):
    """True for literals and containers of literals, such as 36, 'x', [..] or {'a': 1}."""
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, SyntaxError):
        return False
