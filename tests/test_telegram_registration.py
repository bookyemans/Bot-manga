import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_telegram_routes_are_isolated_from_application_bootstrap():
    main_tree = ast.parse((PROJECT_ROOT / "main.py").read_text(encoding="utf-8"))
    main_imports = [
        node for node in ast.walk(main_tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(
            "systems.delivery.ui.handlers"
        )
    ]
    assert not main_imports
    assert "register_handlers(app)" in (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")


def test_registration_module_preserves_middleware_groups_and_message_routes():
    tree = ast.parse(
        (PROJECT_ROOT / "systems/delivery/ui/registration.py").read_text(encoding="utf-8")
    )
    function = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "register_handlers"
    )
    calls = [
        node for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_handler"
    ]
    groups = []
    for call in calls[:3]:
        group = next(keyword.value for keyword in call.keywords if keyword.arg == "group")
        groups.append(ast.literal_eval(group))
    assert groups == [-3, -2, -1]
    assert len(calls) == 41
    assert sum(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "MessageHandler"
        for node in ast.walk(function)
    ) == 7
