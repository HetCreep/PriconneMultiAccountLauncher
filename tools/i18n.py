import glob
import re
from typing import Any

import yaml

def load_locale(path: str) -> dict:
    """Parse one locale file, refusing YAML aliases.

    A locale is a flat tree of strings; it has no use for anchors and aliases. They let a
    few lines expand into exponentially many paths in i18n_flatten (a contributed locale
    file could exhaust this checker's memory), so reject them before building anything.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if any(isinstance(event, yaml.AliasEvent) for event in yaml.parse(text, Loader=yaml.SafeLoader)):
        raise SystemExit(f"{path}: YAML aliases are not allowed in locale files")
    return yaml.safe_load(text)


yaml_load = {}
for lang in glob.glob("assets/i18n/*.yml"):
    yaml_load.update(load_locale(lang))


def in_py(key):
    for file in glob.glob("**/*.py", root_dir="PriconneMultiAccountLauncher", recursive=True):
        with open(f"PriconneMultiAccountLauncher/{file}", "r", encoding="utf-8") as f:
            if f'i18n.t("{key}"' in f.read():
                return False
    return True


def i18n_flatten(data: dict[str, Any], parent: str) -> list[str]:
    res = []
    for k, v in data.items():
        if isinstance(v, dict):
            res.extend(i18n_flatten(v, f"{parent}.{k}"))
        elif isinstance(v, str):
            res.append(f"{parent}.{k}")
    return res


def get_py():
    res = []
    for file in glob.glob("**/*.py", root_dir="PriconneMultiAccountLauncher", recursive=True):
        with open(f"PriconneMultiAccountLauncher/{file}", "r", encoding="utf-8") as f:
            match = re.findall(r'i18n.t\("([a-z\.\_]*?)"', f.read())
            res.extend(match)
    return res


i18n = i18n_flatten(yaml_load["en_US"], "app")

for lang in yaml_load.keys():
    target = i18n_flatten(yaml_load[lang], "app")
    for key in i18n:
        if key not in target:
            print(f"not found in {lang}: {key}")


print("===")
for key in i18n:
    if in_py(key):
        print(f"not found: {key}")

print("===")
for key in get_py():
    if key not in i18n:
        print(f"not used: {key}")
