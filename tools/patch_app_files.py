# -*- coding: utf-8 -*-
"""Patch Qoder renderer/main files to add a zh-TW language option.

Sources are read from work/original (pristine copies) and written to
/tmp/qoder_asar/out so the patch can be reapplied deterministically.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tw import Converter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "work" / "original"
OUT = Path("/tmp/qoder_asar/out")
TW = ROOT / "translations" / "zh-TW"

CJK = "\u3400-\u9fff"
KEYWORDS_BEFORE_REGEX = {
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "throw", "case", "do", "else", "yield", "await",
}
REGEX_PREFIX_CHARS = set("([{,;:=!&|?+-*%^~<>")


def _scan_regex(text, start):
    i = start + 1
    n = len(text)
    in_class = False
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
            i += 1
            continue
        if c == "[":
            in_class = True
            i += 1
            continue
        if c == "/":
            i += 1
            while i < n and text[i].isalpha():
                i += 1
            return i
        i += 1
    return start + 1


def _scan_template_expr(text, start):
    """Return end offset of a ${...} expression (start points at '$')."""
    i = start + 2
    n = len(text)
    depth = 1
    while i < n:
        c = text[i]
        if c in "\"'":
            q = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "`":
            i += 1
            depth_t = 1
            while i < n and depth_t:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "`":
                    depth_t -= 1
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def convert_js_strings(text):
    """Convert Chinese text inside JS string literals, leaving code intact."""
    out = []
    i = 0
    n = len(text)
    last = ""

    def convert(value):
        return Converter().convert(value) if value else value

    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                j = text.find("\n", i)
                j = n if j < 0 else j
                out.append(text[i:j])
                i = j
                continue
            if nxt == "*":
                j = text.find("*/", i + 2)
                j = n if j < 0 else j + 2
                out.append(text[i:j])
                i = j
                continue
            prev_char = last[-1] if last else ""
            if (last in KEYWORDS_BEFORE_REGEX or prev_char in REGEX_PREFIX_CHARS
                    or (last == "" and c == "/")):
                j = _scan_regex(text, i)
                out.append(text[i:j])
                i = j
                last = "/"
                continue

        if c in "\"'" and not (c == "'" and last.endswith("\\")):
            q = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    break
                j += 1
            out.append(q + convert(text[i + 1:j]) + q)
            i = j + 1
            last = q
            continue

        if c == "`":
            out.append("`")
            i += 1
            seg = i
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "`":
                    out.append(convert(text[seg:i]))
                    out.append("`")
                    i += 1
                    last = "`"
                    break
                if text[i] == "$" and i + 1 < n and text[i + 1] == "{":
                    out.append(convert(text[seg:i]))
                    j = _scan_template_expr(text, i)
                    out.append(convert_js_strings(text[i:j]))
                    i = j
                    seg = i
                    continue
                i += 1
            continue

        out.append(c)
        if not c.isspace():
            if c.isalnum() or c in "_$":
                m = re.match(r"[A-Za-z0-9_$]+", text[i:])
                last = m.group(0) if m else c
            else:
                last = c
        i += 1
    return "".join(out)


def patch(text, old, new, label, count=1):
    found = text.count(old)
    if found != count:
        raise SystemExit(f"[{label}] expected {count} occurrence(s), found {found}")
    return text.replace(old, new)


def write(rel, text):
    path = OUT / rel
    path.write_text(text, "utf-8")
    print(f"wrote {rel} ({len(text)} chars)")


def patch_qwhg():
    s = (ORIG / "renderer/assets/QWhgX92t.js").read_text("utf-8")

    old_funcs = (
        'function gt(o){return o==="zh"||o==="en"?o:null}'
        'function gi(o){return o[0]?.toLowerCase().startsWith("zh")?"zh":"en"}'
        'function vi(o,e){return o==="zh"||o==="en"?o:gi(e)}'
        'function Bi(o){return o.toLowerCase().startsWith("zh")?"zh":"en"}'
    )
    new_funcs = (
        'function gt(o){return o==="zh"||o==="en"||o==="zh-TW"?o:null}'
        'function gi(o){const e=(o?.[0]||"").toLowerCase();'
        'return e.startsWith("zh-tw")||e.startsWith("zh-hant")||e==="zh-hk"||e==="zh-mo"?"zh-TW":e.startsWith("zh")?"zh":"en"}'
        'function vi(o,e){return o==="zh"||o==="en"||o==="zh-TW"?o:gi(e)}'
        'function Bi(o){const e=(o||"").toLowerCase();'
        'return e==="zh-tw"||e.startsWith("zh-hant")?"zh-TW":e.startsWith("zh")?"zh":"en"}'
    )
    s = patch(s, old_funcs, new_funcs, "qwhg-language-functions")

    base = json.loads((TW / "base.json").read_text("utf-8"))
    injected = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    s = patch(
        s,
        'me="loop.language";',
        f'me="loop.language";ht["zh-TW"]={injected};',
        "qwhg-resource",
    )
    write("renderer/assets/QWhgX92t.js", s)


def patch_cux():
    s = (ORIG / "renderer/assets/Cux9x6wn.js").read_text("utf-8")

    issue = json.loads((TW / "issueDrawer.json").read_text("utf-8"))["zh-TW"]
    project = json.loads((TW / "projectBoard.json").read_text("utf-8"))["zh-TW"]
    s = patch(
        s,
        "};for(const[e,t]of Object.entries(_n2))",
        "};_n2[\"zh-TW\"]=" + json.dumps(issue, ensure_ascii=False, separators=(",", ":"))
        + ";for(const[e,t]of Object.entries(_n2))",
        "issue-drawer-resource",
    )
    s = patch(
        s,
        "};for(const[e,t]of Object.entries(qb2))",
        "};qb2[\"zh-TW\"]=" + json.dumps(project, ensure_ascii=False, separators=(",", ":"))
        + ";for(const[e,t]of Object.entries(qb2))",
        "project-board-resource",
    )

    s = patch(
        s,
        '(y1==="zh"||y1==="en")&&Fw1(y1)',
        '(y1==="zh"||y1==="en"||y1==="zh-TW")&&Fw1(y1)',
        "profile-validator",
    )
    s = patch(
        s,
        'value:"zh",children:"简体中文"}),s.jsx(y2,{className:d3,onSelect:C("gui_e9307d6c06d73212"',
        'value:"zh",children:"简体中文"}),s.jsx(y2,{className:d3,onSelect:C("gui_zh_tw_language",m1,"zh-TW",S0[1],"activation"),value:"zh-TW",children:"繁體中文"}),s.jsx(y2,{className:d3,onSelect:C("gui_e9307d6c06d73212"',
        "profile-option",
    )

    s = patch(
        s,
        '($==="zh"||$==="en")&&Fw1($)',
        '($==="zh"||$==="en"||$==="zh-TW")&&Fw1($)',
        "appearance-validator",
    )
    s = patch(
        s,
        'children:"简体中文"}),s.jsx(Y0,{value:"en","data-qoder-gui-id":"gui_fd4e04c9f35bbeaf"',
        'children:"简体中文"}),s.jsx(Y0,{value:"zh-TW","data-qoder-gui-id":"gui_zh_tw_language","data-qoder-gui-activation":"pointerup","data-qoder-gui-target":b0("zh-TW",B3[15]),children:"繁體中文"}),s.jsx(Y0,{value:"en","data-qoder-gui-id":"gui_fd4e04c9f35bbeaf"',
        "appearance-option",
    )
    s = patch(
        s,
        'const B3=[[],["auto"],["light"],["dark"],["follow"],["manual"],["zh"],["en"],["sans"],["serif"],["default"],["wide"],["qoder"],["material"],["follow-app"]]',
        'const B3=[[],["auto"],["light"],["dark"],["follow"],["manual"],["zh"],["en"],["sans"],["serif"],["default"],["wide"],["qoder"],["material"],["follow-app"],["zh-TW"]]',
        "appearance-targets",
    )

    s = patch(
        s,
        'value:d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",R=>{K0.changeLanguage(R)}',
        'value:d==="zh-TW"?"zh-TW":d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",R=>{K0.changeLanguage(R),Fw1(R)}',
        "avatar-value",
    )
    s = patch(
        s,
        'children:"中文"}),s.jsx(Y0,{value:"en","data-qoder-gui-id":"gui_8d0ca484b6c46313"',
        'children:"中文"}),s.jsx(Y0,{value:"zh-TW","data-qoder-gui-id":"gui_zh_tw_language","data-qoder-gui-activation":"pointerup","data-qoder-gui-target":b0("zh-TW",l5[1]),children:"繁體中文"}),s.jsx(Y0,{value:"en","data-qoder-gui-id":"gui_8d0ca484b6c46313"',
        "avatar-option",
    )

    s = patch(
        s,
        'u=["zh","en"].map(f=>o.getFixedT(f)("settings.agentBuilderWorkingStyle"))',
        'u=["zh","en","zh-TW"].map(f=>o.getFixedT(f)("settings.agentBuilderWorkingStyle"))',
        "agent-builder-languages",
    )

    s = patch(
        s,
        'languageOptions:i==="en"?[{value:"zh",label:"CN"},{value:"en",label:"EN"}]:[{value:"zh",label:"中文"},{value:"en",label:"英文"}]',
        'languageOptions:i==="en"?[{value:"zh",label:"CN"},{value:"en",label:"EN"},{value:"zh-TW",label:"TW"}]:[{value:"zh",label:"中文"},{value:"en",label:"英文"},{value:"zh-TW",label:"繁體中文"}]',
        "login-options",
    )
    s = patch(
        s,
        'onLanguageChange:C("gui_71055172be4221a9",M=>d(M==="en"?"en":"zh")',
        'onLanguageChange:C("gui_71055172be4221a9",M=>d(M)',
        "login-language-change",
    )

    write("renderer/assets/Cux9x6wn.js", s)


def patch_c2():
    s = (ORIG / "renderer/assets/C2dqRQMK.js").read_text("utf-8")
    s = convert_js_strings(s)
    s = patch(s, 'schema:bt(["zh","en"])', 'schema:bt(["zh","en","zh-TW"])', "workbench-language-schema")
    s = patch(s, "演示畫面", "簡報畫面", "task-monitor-presentation")
    write("renderer/assets/C2dqRQMK.js", s)


def patch_small_and_index():
    for name in ("BMSxlLhu.js", "6pbfkziW.js", "D1eLu6vA.js"):
        s = (ORIG / f"renderer/assets/{name}").read_text("utf-8")
        s = convert_js_strings(s)
        if name == "6pbfkziW.js":
            s = patch(
                s,
                'language:w.language.startsWith("zh")?"zh":"en"',
                'language:w.language==="zh-TW"?"zh-TW":w.language.startsWith("zh")?"zh":"en"',
                "onboarding-language",
            )
        write(f"renderer/assets/{name}", s)

    s = (ORIG / "renderer/index.html").read_text("utf-8")
    s = patch(s, 'aria-label="正在恢复登录状态"', 'aria-label="正在還原登入狀態"', "splash-label")
    write("renderer/index.html", s)


def patch_main():
    s = (ORIG / "main/electronMain.js").read_text("utf-8")

    old_menu = (
        'function e(f,a){return n(a,f- -710)}'
        'return t[e(7827,17700)]()[e(18996,-5124)]("zh")?{about:e(14108,24483)+x+"",'
    )
    tw_menu = (
        'return{about:"關於 "+x+"",checkForUpdates:"檢查更新",settings:"設定",'
        'file:"檔案",edit:"編輯",view:"顯示",window:"視窗",help:"說明",'
        'close:"關閉視窗",undo:"還原",redo:"重做",cut:"剪下",copy:"拷貝",'
        'paste:"貼上",pasteAndMatchStyle:"貼上並符合樣式",delete:"刪除",'
        'selectAll:"全選",reload:"重新載入",forceReload:"強制重新載入",'
        'toggleDevTools:"切換開發人員工具",resetZoom:"重設縮放",zoomIn:"放大",'
        'zoomOut:"縮小",toggleFullscreen:"切換全螢幕",minimize:"縮到最小",'
        'zoom:"縮放",front:"全部置於最前",services:"服務",hide:"隱藏 "+x+"",'
        'hideOthers:"隱藏其他",unhide:"顯示全部",quit:"結束 "+x+"",'
        'newWindow:"新增視窗"}'
    )
    new_menu = (
        'function e(f,a){return n(a,f- -710)}'
        'const zq=String(t).toLowerCase(),'
        'zs=String(kx.getSystemLocale?.()||"").toLowerCase(),'
        'zw=v=>v.startsWith("zh-tw")||v.startsWith("zh-hant")||v==="zh-hk"||v==="zh-mo";'
        'if((zq.startsWith("zh")&&zw(zq))||zw(zs))' + tw_menu +
        ';return t[e(7827,17700)]()[e(18996,-5124)]("zh")?{about:e(14108,24483)+x+"",'
    )
    s = patch(s, old_menu, new_menu, "main-menu-tw")
    write("main/electronMain.js", s)


def main():
    patch_qwhg()
    patch_cux()
    patch_c2()
    patch_small_and_index()
    patch_main()


if __name__ == "__main__":
    main()
