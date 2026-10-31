# -*- coding: utf-8 -*-
"""Build zh-TW translation resources from the extracted zh/en bundles."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tw import OVERRIDES, PROTECT_RE, Converter  # noqa: E402
from opencc import OpenCC  # noqa: E402

S2T = OpenCC("s2t")
T2S = OpenCC("t2s")
SUSPICIOUS_EXEMPT = set("准台游吃群峰干里秘夸")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "translations" / "source"
OUT = ROOT / "translations" / "zh-TW"
HAN_RE = re.compile(r"[\u3400-\u9fff]")


def placeholder_list(text):
    return sorted(m.group(0) for m in PROTECT_RE.finditer(text))


def get_path(tree, path):
    node = tree
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def set_path(tree, path, value):
    parts = path.split(".")
    node = tree
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def convert_tree(source, converter):
    if isinstance(source, dict):
        return {k: convert_tree(v, converter) for k, v in source.items()}
    if isinstance(source, list):
        return [convert_tree(v, converter) for v in source]
    if isinstance(source, str):
        return converter.convert(source)
    return source


def validate_structure(src, out, path, problems):
    if isinstance(src, dict):
        if not isinstance(out, dict):
            problems.append(f"{path}: expected object")
            return
        missing = sorted(set(src) - set(out))
        extra = sorted(set(out) - set(src))
        if missing:
            problems.append(f"{path}: missing keys {missing[:5]}")
        if extra:
            problems.append(f"{path}: extra keys {extra[:5]}")
        for key in src:
            if key in out:
                validate_structure(src[key], out[key], f"{path}.{key}".strip("."), problems)
    elif isinstance(src, str):
        if not isinstance(out, str):
            problems.append(f"{path}: expected string")
            return
        a, b = placeholder_list(src), placeholder_list(out)
        if a != b:
            problems.append(f"{path}: placeholder mismatch {a} != {b}")
        if "\ue000" in out or "\ue001" in out:
            problems.append(f"{path}: unresolved token")


def collect_leaves(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from collect_leaves(value, f"{path}.{key}".strip("."))
    elif isinstance(node, str):
        yield path, node


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base_src = json.loads((SRC / "base.json").read_text("utf-8"))
    zh_tree = base_src["zh"]["translation"]
    en_tree = base_src["en"]["translation"]

    converter = Converter()
    tw_tree = convert_tree(zh_tree, converter)

    overridden = []
    missing_overrides = []
    for key, value in OVERRIDES.items():
        _, exists = get_path(tw_tree, key)
        if not exists:
            missing_overrides.append(key)
            continue
        set_path(tw_tree, key, value)
        overridden.append(key)

    problems = []
    validate_structure(zh_tree, tw_tree, "base", problems)

    def validate_common_placeholders(src, out, path):
        if isinstance(src, dict) and isinstance(out, dict):
            for key in set(src) & set(out):
                validate_common_placeholders(src[key], out[key], f"{path}.{key}".strip("."))
        elif isinstance(src, str) and isinstance(out, str):
            if placeholder_list(src) != placeholder_list(out):
                problems.append(f"{path}: en placeholder mismatch")


    # Overrides must keep placeholders intact.
    for key in overridden:
        src_value, _ = get_path(zh_tree, key)
        tw_value, _ = get_path(tw_tree, key)
        if placeholder_list(src_value) != placeholder_list(tw_value):
            problems.append(f"override {key}: placeholder mismatch")

    (OUT / "base.json").write_text(
        json.dumps({"translation": tw_tree}, ensure_ascii=False, separators=(",", ":")),
        "utf-8",
    )

    report = {
        "base_strings": sum(1 for _ in collect_leaves(tw_tree)),
        "overrides": overridden,
        "missing_overrides": missing_overrides,
        "problems": problems,
    }

    for name, overrides in (
        ("issueDrawer", {"details": "Issue 側邊面板", "close": "關閉 Issue 側邊面板"}),
        ("projectBoard", {"details": "Issue 側邊面板", "close": "關閉 Issue 側邊面板"}),
    ):
        src = json.loads((SRC / f"{name}.json").read_text("utf-8"))
        converted = convert_tree(src["zh"], Converter())
        converted.update(overrides)
        problems = []
        validate_structure(src["zh"], converted, name, problems)
        (OUT / f"{name}.json").write_text(
            json.dumps({"zh-TW": converted}, ensure_ascii=False, separators=(",", ":")),
            "utf-8",
        )
        report[f"{name}_strings"] = sum(1 for _ in collect_leaves(converted))
        report[f"{name}_problems"] = problems

    dyn = json.loads((SRC / "dynamic-text.json").read_text("utf-8"))
    dyn_tw = convert_tree(dyn["zh"], Converter())
    problems = []
    validate_structure(dyn["zh"], dyn_tw, "dynamic-text", problems)
    (OUT / "dynamic-text.json").write_text(
        json.dumps({"en": dyn["en"], "zh-TW": dyn_tw}, ensure_ascii=False, separators=(",", ":")),
        "utf-8",
    )
    report["dynamic_text_strings"] = sum(1 for _ in collect_leaves(dyn_tw))
    report["dynamic_text_problems"] = problems

    # Characters that are Simplified-only (OpenCC s2t would change them).
    leftovers = []
    for path, value in collect_leaves(tw_tree):
        bad = [
            ch
            for ch in value
            if "\u3400" <= ch <= "\u9fff"
            and S2T.convert(ch) != ch
            and T2S.convert(ch) == ch
            and ch not in SUSPICIOUS_EXEMPT
        ]
        if bad:
            leftovers.append({"key": path, "chars": sorted(set(bad)), "value": value})
    report["leftover_count"] = len(leftovers)
    report["leftover_sample"] = leftovers[:30]

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
    )

    print(json.dumps({k: v for k, v in report.items() if k != "leftover_sample"}, ensure_ascii=False, indent=2))
    print("\nSamples:")
    samples = [
        "startup.cliConfigurationTitle",
        "deepLink.extensionInstall.warning.mcp",
        "error.101.message",
        "nav.workspacesDescription",
        "settings.networkProxy.restartConfirmDescription",
        "composer.permission.bypassPermissions.confirmation.capabilities.network.description",
        "chatSession.backgroundProcesses.title",
        "extensions.pluginsDescription",
        "discussion.leaveDescription",
        "workspace.review.markdownVisualEditingLimited",
        "settings.taskMonitor.description",
        "usage.renewsOn",
        "customAvatar.applyHint",
        "applicationMenu.help",
        "errors.does.not.exist",
    ]
    for key in samples:
        value, _ = get_path(tw_tree, key)
        if value is not None:
            print(f"{key}: {value[:220]}")
    if leftovers:
        print("\nLeftover sample:")
        for item in leftovers[:15]:
            print(f"* {item['key']}: {item['value'][:160]}")
            print(f"  -> leftovers: {''.join(item['chars'])}")


if __name__ == "__main__":
    main()
