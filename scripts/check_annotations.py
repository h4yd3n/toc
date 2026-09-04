"""Evaluate every annotation in the product packages. Python 3.14 defers annotations (PEP 649), so a missing typing
import passes locally and fails on the 3.11 CI runner; this forces the evaluation the older interpreters do at import."""
import importlib, inspect, pkgutil, sys, typing

sys.path[:0] = ["shared", "coptoc/api", "sigtoc", "modtoc"]
failures = 0
for pkg in ("shared", "coptoc", "sigtoc", "modtoc"):
    mod = importlib.import_module(pkg)
    for m in pkgutil.walk_packages(mod.__path__, pkg + "."):
        try:
            module = importlib.import_module(m.name)
        except Exception as e:  # noqa: BLE001
            print(f"IMPORT FAILED {m.name}: {e}"); failures += 1; continue
        for name, obj in vars(module).items():
            if getattr(obj, "__module__", None) != module.__name__: continue
            targets = [obj] if inspect.isfunction(obj) else []
            if inspect.isclass(obj):
                targets += [v for v in vars(obj).values() if inspect.isfunction(v)]
                try: typing.get_type_hints(obj)
                except Exception as e:  # noqa: BLE001
                    print(f"{m.name}.{name}: {e}"); failures += 1
            for fn in targets:
                try: typing.get_type_hints(fn)
                except Exception as e:  # noqa: BLE001
                    print(f"{m.name}.{fn.__qualname__}: {e}"); failures += 1
print("annotations ok" if not failures else f"{failures} annotation failure(s)")
sys.exit(1 if failures else 0)
