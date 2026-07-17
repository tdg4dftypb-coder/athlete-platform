from pathlib import Path
import ast
import json
import py_compile
import traceback
import sys


ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


IGNORE = {
    ".git",
    ".venv",
    ".venv-1",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


FORBIDDEN_IMPORTS = {
    "collectors": {
        "decision",
        "performance",
        "recovery",
        "workout",
        "execution",
        "coach",
    },
    "repositories": {
        "decision",
        "workout",
        "execution",
    },
}


def skip(path: Path):
    return any(part in IGNORE for part in path.parts)


def python_files():
    return sorted(
        p
        for p in ROOT.rglob("*.py")
        if not skip(p)
    )


def compile_check():

    errors = []

    for file in python_files():

        try:
            py_compile.compile(file, doraise=True)

        except Exception as exc:
            errors.append((file.relative_to(ROOT), str(exc)))

    return errors


def architecture_check():

    required = [
        "collectors",
        "repositories",
        "core",
        "training",
        "performance",
        "recovery",
        "decision",
        "athlete",
        "workout",
        "execution",
        "scripts",
    ]

    return [
        item
        for item in required
        if not (ROOT / item).exists()
    ]


def import_check():

    violations = []

    for file in python_files():

        relative = file.relative_to(ROOT)

        layer = relative.parts[0]

        if layer not in FORBIDDEN_IMPORTS:
            continue

        tree = ast.parse(
            file.read_text(encoding="utf-8")
        )

        for node in ast.walk(tree):

            modules = []

            if isinstance(node, ast.Import):

                modules = [
                    n.name.split(".")[0]
                    for n in node.names
                ]

            elif isinstance(node, ast.ImportFrom):

                if node.module:
                    modules = [
                        node.module.split(".")[0]
                    ]

            for module in modules:

                if module in FORBIDDEN_IMPORTS[layer]:

                    violations.append({
                        "file": str(relative),
                        "layer": layer,
                        "import": module,
                    })

    return violations


def write_report(report):

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)

    report_file = reports / "project_health.json"

    report_file.write_text(
        json.dumps(
            report,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def section(title):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main():

    score = 100

    report = {}

    print()
    print("ATHLETE PLATFORM DOCTOR")
    print("-" * 70)

    #
    # Compile
    #

    compile_errors = compile_check()

    section("Compile")

    if compile_errors:

        score -= 50

        print("[FAIL]")

        for error in compile_errors:

            print(error[0])
            print(error[1])
            print()

    else:

        print("[PASS]")

    report["compile"] = {
        "status": len(compile_errors) == 0,
        "errors": compile_errors,
    }

    #
    # Architecture
    #

    missing = architecture_check()

    section("Architecture")

    if missing:

        score -= 20

        print("[FAIL]")

        for item in missing:
            print(item)

    else:

        print("[PASS]")

    report["architecture"] = {
        "status": len(missing) == 0,
        "missing": missing,
    }

    #
    # Layer Dependencies
    #

    violations = import_check()

    section("Layer Dependencies")

    if violations:

        score -= 20

        print("[FAIL]")

        for violation in violations:

            print(
                f"{violation['file']} : "
                f"{violation['layer']} -> "
                f"{violation['import']}"
            )

    else:

        print("[PASS]")

    report["layer_dependencies"] = {
        "status": len(violations) == 0,
        "violations": violations,
    }

    #
    # Score
    #

    score = max(score, 0)

    report["health_score"] = score

    write_report(report)

    section("Summary")

    print(f"Python files : {len(python_files())}")
    print(f"Health Score : {score}/100")

    print()

    if score == 100:

        print("Project Healthy")
        sys.exit(0)

    if score >= 80:

        print("Project Good")
        sys.exit(0)

    print("Project Needs Attention")
    sys.exit(1)


if __name__ == "__main__":

    try:
        main()

    except Exception:
        traceback.print_exc()
        sys.exit(1)