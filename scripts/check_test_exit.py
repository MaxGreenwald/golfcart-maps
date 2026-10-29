#!/usr/bin/env python3
"""Fail the run if any scripts/test_*.py can print FAIL and still exit 0.

Every scripts/test_*.py must import finish from scripts/_check.py and call it
unconditionally at module level (a with-block is fine; an if/for/function is not).
Failures have to go through that module: a local fails list, a local ck/check/ok,
a hand-written RESULT or FAIL line, or sys.exit/SystemExit would let a FAIL
print while the process still exits 0. verify_live used to trust that exit code.

Usage:
  python scripts/check_test_exit.py
  python scripts/check_test_exit.py path/to/test_one.py
Exit 0 when every script is clean, 1 otherwise.
"""
from __future__ import annotations

import ast
import glob
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKIP_NEST = (
    ast.If,
    ast.For,
    ast.While,
    ast.AsyncFor,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.ExceptHandler,
)


def _status_kind(text):
    """Return 'FAIL' or 'RESULT' when a string literal is a hand-written status line."""
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if stripped == "RESULT" or stripped.startswith("RESULT ") or stripped.startswith("RESULT\t"):
        return "RESULT"
    if re.search(r"\bRESULT\b", text) and re.search(r"\b(PASS|FAIL)\b", text):
        return "RESULT"
    if stripped == "FAIL" or stripped.startswith("FAIL ") or stripped.startswith("FAIL:"):
        return "FAIL"
    if " FAIL:" in text or text.endswith(" FAIL") or " FAIL " in text:
        return "FAIL"
    return None


def _bound_names(target):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _bound_names(elt)


def _imports(tree):
    """Map local name -> attribute imported from _check."""
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module != "_check":
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            found[alias.asname or alias.name] = alias.name
    return found


def _calls_name(node, name):
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == name:
            return True
    return False


def _has_status_string(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and _status_kind(child.value):
            return _status_kind(child.value)
    return None


def _unconditional_finish(tree):
    found = []

    def walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, SKIP_NEST):
                continue
            if isinstance(stmt, ast.Try):
                walk(stmt.body)
                walk(stmt.finalbody)
                continue
            if isinstance(stmt, (ast.With, ast.AsyncWith)):
                walk(stmt.body)
                continue
            if _calls_name(stmt, "finish"):
                found.append(stmt)

    walk(tree.body)
    return bool(found)


def _print_status(tree):
    """Status literals passed to print(), including inside functions."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_print = (isinstance(func, ast.Name) and func.id == "print") or (
            isinstance(func, ast.Attribute) and func.attr == "print"
        )
        if not is_print:
            continue
        kind = _has_status_string(node)
        if kind:
            hits.append(kind)
    return hits


def _exit_calls(tree):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            exc = node.exc
            name = None
            if isinstance(exc, ast.Name):
                name = exc.id
            elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            if name == "SystemExit":
                hits.append("raise SystemExit")
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "exit" or not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id in {"sys", "_sys", "os"}:
            hits.append(f"{node.func.value.id}.exit")
    return hits


def _delegates(fn, imported):
    """A one-path wrapper that always calls the imported ck, with no status text of its own."""
    if _has_status_string(fn):
        return False
    for child in ast.walk(fn):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.FunctionDef)):
            if child is not fn:
                return False
    helpers = [local for local, orig in imported.items() if orig == "ck" and local != fn.name]
    return any(_calls_name(fn, helper) for helper in helpers)


def _assignment_targets(node):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            yield from _bound_names(target)
    elif isinstance(node, ast.AnnAssign) and node.target is not None:
        yield from _bound_names(node.target)
    elif isinstance(node, ast.AugAssign):
        yield from _bound_names(node.target)


def analyze_tree(tree, label):
    """Return problem strings for one parsed test script."""
    problems = []
    imported = _imports(tree)
    if imported.get("finish") != "finish":
        problems.append(f"{label}: does not import finish from _check")
    if not _unconditional_finish(tree):
        problems.append(
            f"{label}: does not call finish() unconditionally at module level "
            "(a FAIL can still exit 0)"
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "finish":
            problems.append(f"{label}: defines finish() locally, so the shared exit is skipped")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {"ck", "check", "ok"}:
            if not _delegates(node, imported):
                problems.append(
                    f"{label}: defines {node.name}() locally, so a FAIL can skip the shared counter and exit 0"
                )
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for name in _assignment_targets(node):
                if name in {"fails", "finish"}:
                    problems.append(
                        f"{label}: assigns {name} locally; finish() would not see those failures"
                    )
                if name == "ck":
                    problems.append(f"{label}: rebinds ck; call the imported ck so failures reach finish()")
                if name in {"check", "ok"} and isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Lambda) or any(
                        isinstance(child, ast.Lambda) for child in ast.walk(node.value)
                    ):
                        problems.append(
                            f"{label}: rebinds {name} to a lambda that can print FAIL and exit 0"
                        )

    for kind in _print_status(tree):
        if kind == "FAIL":
            problems.append(f"{label}: prints a FAIL status itself instead of ck()/finish()")
        else:
            problems.append(
                f"{label}: prints a RESULT line itself; finish() owns that line and the exit code"
            )
    for hit in _exit_calls(tree):
        problems.append(f"{label}: {hit} bypasses finish(); a FAIL line can still exit 0")
    return problems


def analyze_source(source, label):
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as exc:
        return [f"{label}: cannot parse ({exc})"]
    return analyze_tree(tree, label)


def analyze_path(path):
    label = os.path.relpath(path, ROOT) if path.startswith(ROOT) else path
    with open(path, encoding="utf-8") as handle:
        return analyze_source(handle.read(), label)


def default_paths():
    return sorted(glob.glob(os.path.join(ROOT, "scripts", "test_*.py")))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    paths = args or default_paths()
    if not paths:
        print("FAIL no scripts/test_*.py found")
        print("RESULT 1 FAIL")
        return 1
    problems = []
    for path in paths:
        problems.extend(analyze_path(path))
    if problems:
        for item in problems:
            print("FAIL", item)
        print(f"RESULT {len(problems)} FAIL")
        return 1
    print(f"RESULT ALL PASS ({len(paths)} scripts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
