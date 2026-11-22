# -*- coding: utf-8 -*-
"""Patch Qoder 0.5.17 renderer/main files to add a zh-TW language option.

Reads pristine files from work/cn-original (Qoder CN 0.5.17 app.asar) and
writes the patched copies to work/0517-stage/out.

0.5.17 differences vs 0.5.13:
- i18n chunk is D7G81Cst.js; all namespaces merged into one `Ye` object that
  already contains zh-HK and ko-KR resources.
- Language list/normalizer moved to UnNhyzqB.js (`Oe`, `Xe`); settings value is
  derived through `Xe`, so adding zh-TW there is enough for the dropdown.
- Main renderer bundle is DMzt2vcU.js and embeds a ~20k-entry single-character
  IME dictionary. Conversion is therefore restricted to literals with at least
  two CJK characters (template text is always converted).
- Native menu function is wHt. Qoder CN forces the app locale to zh-CN, so the
  Traditional check also consults `xt.getSystemLocale()`.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_app_files import patch  # noqa: E402
from tw import Converter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "work" / "cn-original"
DICT = ROOT / "work" / "0517-dict"
OUT = ROOT / "work" / "0517-stage" / "out"

I18N_FILE = "D7G81Cst.js"
LANG_CHUNK = "UnNhyzqB.js"
MAIN_BUNDLE = "DMzt2vcU.js"
TITLE_VALIDATOR = "ClMoALKS.js"

CONVERT_CHUNKS = [
    "B7xIIv6H.js", "KSrj1L-v.js", "CFNPMAwa.js", "Bp5ml99Y.js",
    "Cx4X391Y.js", "D1eLu6vA.js", "A_9LZ4mC.js", "BHmloleD.js",
    "B01Tds90.js",
]

CJK_RE = re.compile(r"[\u3400-\u9fff\u201c\u201d\u2018\u2019]")
CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff]")
TYPED_EXTRACTOR = Path(__file__).resolve().parent / "jsparse" / "extract_ranges_typed.js"


def write(rel, text):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")
    print(f"wrote {rel} ({len(text)} chars)")


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def convert_js_strings_filtered(text, source_type="module"):
    """Convert display strings while leaving the single-char IME table alone."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(text)
        tmp = f.name
    try:
        r = subprocess.run(
            ["node", str(TYPED_EXTRACTOR), tmp, source_type],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise SystemExit("acorn parse failed: " + r.stderr[:2000])
        ranges = json.loads(r.stdout)
    finally:
        import os

        os.unlink(tmp)
    conv = Converter()
    # acorn reports UTF-16 code-unit offsets; slice the same units so astral
    # characters (emoji) in the bundle do not shift every later range.
    src = text.encode("utf-16-le")
    out = []
    cursor = 0
    for a, b, kind in ranges:
        if a < cursor:
            continue
        out.append(src[cursor * 2:a * 2])
        seg = src[a * 2:b * 2].decode("utf-16-le")
        if CJK_RE.search(seg) and (kind == "tpl" or len(CJK_CHAR_RE.findall(seg)) >= 2):
            seg = conv.convert(seg)
        out.append(seg.encode("utf-16-le"))
        cursor = b
    out.append(src[cursor * 2:])
    return b"".join(out).decode("utf-16-le")


def patch_i18n():
    s = (ORIG / f"out/renderer/assets/{I18N_FILE}").read_text("utf-8")
    tw = json.loads((DICT / "tw_base.json").read_text("utf-8"))
    s = patch(
        s,
        ',Ae="loop.language";',
        ',Ae="loop.language";Ye["zh-TW"]={translation:' + compact(tw) + "};",
        "i18n-resource",
    )
    write(f"out/renderer/assets/{I18N_FILE}", s)


def patch_language_chunk():
    s = (ORIG / f"out/renderer/assets/{LANG_CHUNK}").read_text("utf-8")
    s = patch(
        s,
        '{value:"zh-HK",label:"繁體中文（香港）"}',
        '{value:"zh-TW",label:"繁體中文"},{value:"zh-HK",label:"繁體中文（香港）"}',
        "language-list",
    )
    s = patch(
        s,
        'return/^zh-(?:hant-)?(?:hk|mo)(?:-|$)/.test(e)?"zh-HK":',
        'return/^zh-(?:hant-?)?tw(?:-|$)/.test(e)||e==="zh-hant"?"zh-TW":'
        '/^zh-(?:hant-)?(?:hk|mo)(?:-|$)/.test(e)?"zh-HK":',
        "locale-normalize",
    )
    write(f"out/renderer/assets/{LANG_CHUNK}", s)


def patch_main_bundle():
    s = (ORIG / f"out/renderer/assets/{MAIN_BUNDLE}").read_text("utf-8")

    s = patch(
        s,
        'value:d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",H=>{Ke.changeLanguage(H)}',
        'value:d==="zh-TW"?"zh-TW":d?.startsWith("zh")?"zh":"en",'
        'onValueChange:C("gui_c281a341ec7887fa",H=>{Ke.changeLanguage(H),'
        'localStorage.setItem("loop.language",H)}',
        "avatar-value",
    )
    s = patch(
        s,
        'children:[s.jsx(f0,{value:"zh","data-qoder-gui-id":"gui_eb678b6ad75f0c40",'
        '"data-qoder-gui-activation":"pointerup","data-qoder-gui-target":Se("zh",X4[1]),'
        'children:"中文"}),',
        'children:[s.jsx(f0,{value:"zh","data-qoder-gui-id":"gui_eb678b6ad75f0c40",'
        '"data-qoder-gui-activation":"pointerup","data-qoder-gui-target":Se("zh",X4[1]),'
        'children:"中文"}),s.jsx(f0,{value:"zh-TW","data-qoder-gui-id":"gui_zh_tw_language",'
        '"data-qoder-gui-activation":"pointerup","data-qoder-gui-target":Se("zh-TW",X4[1]),'
        'children:"繁體中文"}),',
        "avatar-option",
    )
    s = patch(
        s,
        'u=["zh","en"].map(g=>o.getFixedT(g)("settings.agentBuilderWorkingStyle"))',
        'u=["zh","en","zh-TW"].map(g=>o.getFixedT(g)("settings.agentBuilderWorkingStyle"))',
        "agent-builder-languages",
    )
    s = patch(
        s,
        'languageOptions:i==="en"?[{value:"zh",label:"CN"},{value:"en",label:"EN"}]:'
        '[{value:"zh",label:"中文"},{value:"en",label:"英文"}]',
        'languageOptions:i==="en"?[{value:"zh",label:"CN"},{value:"en",label:"EN"},'
        '{value:"zh-TW",label:"TW"}]:[{value:"zh",label:"中文"},{value:"en",label:"英文"},'
        '{value:"zh-TW",label:"繁體中文"}]',
        "login-options",
    )
    s = patch(
        s,
        'onLanguageChange:C("gui_71055172be4221a9",V=>d(V==="en"?"en":"zh")',
        'onLanguageChange:C("gui_71055172be4221a9",V=>d(V)',
        "login-language-change",
    )
    s = patch(
        s,
        't==="zh"||t==="zh-HK"?"zh":"en"',
        't==="zh"||t==="zh-HK"||t==="zh-TW"?"zh":"en"',
        "motto-locale",
    )

    s = convert_js_strings_filtered(s)
    write(f"out/renderer/assets/{MAIN_BUNDLE}", s)


def patch_title_validator():
    s = (ORIG / f"out/renderer/assets/{TITLE_VALIDATOR}").read_text("utf-8")
    s = patch(
        s,
        '["zh","en","zh-HK","ko-KR"].includes(o)',
        '["zh","en","zh-TW","zh-HK","ko-KR"].includes(o)',
        "title-validator",
    )
    write(f"out/renderer/assets/{TITLE_VALIDATOR}", s)


def patch_chunks():
    for name in CONVERT_CHUNKS:
        s = (ORIG / f"out/renderer/assets/{name}").read_text("utf-8")
        write(f"out/renderer/assets/{name}", convert_js_strings_filtered(s))


def patch_index():
    s = (ORIG / "out/renderer/index.html").read_text("utf-8")
    s = patch(
        s,
        'aria-label="正在恢复登录状态"',
        'aria-label="正在還原登入狀態"',
        "splash-label",
    )
    write("out/renderer/index.html", s)


def patch_main_process():
    s = (ORIG / "out/main/electronMain.js").read_text("utf-8")
    old = 'function wHt(t,e=""){return t.toLowerCase().startsWith("zh")?{about:"关于 "+e,'
    tw_menu = (
        'return{about:"關於 "+e,checkForUpdates:"檢查更新",settings:"設定…",'
        'file:"檔案",edit:"編輯",view:"顯示",window:"視窗",help:"說明",'
        'close:"關閉視窗",undo:"還原",redo:"重做",cut:"剪下",copy:"拷貝",'
        'paste:"貼上",pasteAndMatchStyle:"貼上並符合樣式",delete:"刪除",'
        'selectAll:"全選",reload:"重新載入",forceReload:"強制重新載入",'
        'toggleDevTools:"切換開發人員工具",resetZoom:"實際大小",zoomIn:"放大",'
        'zoomOut:"縮小",toggleFullscreen:"切換全螢幕",minimize:"最小化",'
        'zoom:"縮放",front:"全部置於最前",services:"服務",hide:"隱藏 "+e,'
        'hideOthers:"隱藏其他",unhide:"全部顯示",quit:"結束 "+e,'
        'newWindow:"新增視窗"}'
    )
    new = (
        'function wHt(t,e=""){const zq=String(t).toLowerCase().replace(/_/g,"-"),'
        'zs=String(xt?.getSystemLocale?.()||"").toLowerCase().replace(/_/g,"-"),'
        'zw=v=>v.startsWith("zh-tw")||v.startsWith("zh-hant")||v==="zh-hk"||v==="zh-mo";'
        "if(zw(zq)||zw(zs))" + tw_menu + ";"
        'return t.toLowerCase().startsWith("zh")?{about:"关于 "+e,'
    )
    s = patch(s, old, new, "main-menu-tw")
    write("out/main/electronMain.js", s)

    s = (ORIG / "out/main/chunks/C1jqE3Um.js").read_text("utf-8")
    s = patch(
        s,
        'const bn=[{value:"zh",label:"简体中文"},{value:"en",label:"English"},'
        '{value:"zh-HK",label:"繁體中文（香港）"},{value:"ko-KR",label:"한국어"}];',
        'const bn=[{value:"zh",label:"简体中文"},{value:"en",label:"English"},'
        '{value:"zh-TW",label:"繁體中文"},{value:"zh-HK",label:"繁體中文（香港）"},'
        '{value:"ko-KR",label:"한국어"}];',
        "main-language-list",
    )
    s = patch(
        s,
        'return/^zh-(?:hant-)?(?:hk|mo)(?:-|$)/.test(e)?"zh-HK":',
        'return/^zh-(?:hant-?)?tw(?:-|$)/.test(e)||e==="zh-hant"?"zh-TW":'
        '/^zh-(?:hant-)?(?:hk|mo)(?:-|$)/.test(e)?"zh-HK":',
        "main-locale-normalize",
    )
    write("out/main/chunks/C1jqE3Um.js", s)


def main():
    patch_i18n()
    patch_language_chunk()
    patch_main_bundle()
    patch_title_validator()
    patch_chunks()
    patch_index()
    patch_main_process()


if __name__ == "__main__":
    main()