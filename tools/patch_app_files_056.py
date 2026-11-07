# -*- coding: utf-8 -*-
"""Patch Qoder 0.5.6 renderer/main files to add a zh-TW language option.

Reads pristine files from work/056-original, writes patched copies to
/tmp/qoder_asar_056/out preserving the asar-relative paths (out/...).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_app_files import convert_js_strings_acorn as convert_js_strings, patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "work" / "056-original"
DICT = ROOT / "work" / "056-dict"
OUT = Path("/tmp/qoder_asar_056/out")

CONVERT_CHUNKS = [
    "S__Wc8-4.js", "Cs95m02g.js", "CV6Tk442.js", "4YlEfiER.js",
    "B57OAyso.js", "ByAKs9yR.js", "D1eLu6vA.js", "kiEFUCVZ.js",
    "BxpxNb8I.js", "DJSWlOHD.js",
]


def write(rel, text):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")
    print(f"wrote {rel} ({len(text)} chars)")


def load_dict(name):
    return json.loads((DICT / name).read_text("utf-8"))


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def patch_i18n():
    s = (ORIG / "out/renderer/assets/DidgxRds.js").read_text("utf-8")

    tw = load_dict("tw_base.json")
    s = patch(
        s,
        ',Be="loop.language";',
        ',Be="loop.language";Wt["zh-TW"]={translation:' + compact(tw) + "};",
        "i18n-resource",
    )
    s = patch(
        s,
        '{value:"en",label:"English"},{value:"zh-HK",label:"繁體中文（香港）"}',
        '{value:"en",label:"English"},{value:"zh-TW",label:"繁體中文"},{value:"zh-HK",label:"繁體中文（香港）"}',
        "i18n-language-list",
    )
    s = patch(
        s,
        'Yi=xt.filter(({value:i})=>i==="zh"||i==="en")',
        'Yi=xt.filter(({value:i})=>i==="zh"||i==="en"||i==="zh-TW")',
        "i18n-available-filter",
    )
    s = patch(
        s,
        'return/^zh-(?:hant-)?(?:hk|mo)(?:-|$)/.test(e)?"zh-HK":',
        'return/^zh-(?:hant-)?(?:tw|hk|mo)(?:-|$)/.test(e)?"zh-TW":',
        "i18n-locale-normalize",
    )
    write("out/renderer/assets/DidgxRds.js", s)


def mask_object(s, name):
    start = s.find(f"const {name}=")
    if start < 0:
        raise SystemExit(f"[mask] const {name} not found")
    j = s.find("{", start)
    depth = 0
    k = j
    instr = False
    esc = False
    q = ""
    while k < len(s):
        c = s[k]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == q:
                instr = False
        else:
            if c in "\"'`":
                instr = True
                q = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
        k += 1
    original = s[start:k + 1]
    masked = s[:start] + f"const {name}=0" + s[k + 1:]
    return masked, original


def patch_main_bundle():
    s = (ORIG / "out/renderer/assets/2NXLGhal.js").read_text("utf-8")

    s, mf2_orig = mask_object(s, "mf2")
    s, fT2_orig = mask_object(s, "fT2")
    name_orig = '"Siqi Liu （刘思齐）"'
    s = patch(s, name_orig, '"Siqi Liu QODERNAME"', "mask-developer-name")

    s = convert_js_strings(s)

    s = patch(s, '"Siqi Liu QODERNAME"', name_orig, "restore-developer-name")
    mf2_tw = load_dict("mf2_tw.json")
    fT2_tw = load_dict("fT2_tw.json")
    s = patch(
        s, "const mf2=0",
        mf2_orig + ';mf2["zh-TW"]=' + compact(mf2_tw),
        "issue-drawer-resource",
    )
    s = patch(
        s, "const fT2=0",
        fT2_orig + ';fT2["zh-TW"]=' + compact(fT2_tw),
        "project-board-resource",
    )

    s = patch(
        s,
        'value:d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",R=>{Fe.changeLanguage(R)}',
        'value:d==="zh-TW"?"zh-TW":d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",R=>{Fe.changeLanguage(R),lM1(R)}',
        "avatar-value",
    )
    s = patch(
        s,
        'children:"中文"}),s.jsx($e,{value:"en","data-qoder-gui-id":"gui_8d0ca484b6c46313"',
        'children:"中文"}),s.jsx($e,{value:"zh-TW","data-qoder-gui-id":"gui_zh_tw_language","data-qoder-gui-activation":"pointerup",children:"繁體中文"}),s.jsx($e,{value:"en","data-qoder-gui-id":"gui_8d0ca484b6c46313"',
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
    write("out/renderer/assets/2NXLGhal.js", s)


def patch_chunks():
    for name in CONVERT_CHUNKS:
        s = (ORIG / f"out/renderer/assets/{name}").read_text("utf-8")
        write(f"out/renderer/assets/{name}", convert_js_strings(s))


def patch_index():
    s = (ORIG / "out/renderer/index.html").read_text("utf-8")
    s = patch(s, 'aria-label="正在恢复登录状态"', 'aria-label="正在還原登入狀態"', "splash-label")
    write("out/renderer/index.html", s)


def patch_main_process():
    s = (ORIG / "out/main/electronMain.js").read_text("utf-8")
    old = (
        'function lKx(a,x=""){function e(f,n){return t(f- -1311,n)}'
        'return a[e(32212,24019)]()[e(49371,56259)]("zh")?{about:e(12115,23336)+x+"",'
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
    new = (
        'function lKx(a,x=""){function e(f,n){return t(f- -1311,n)}'
        'const zq=String(a).toLowerCase(),'
        'zs=String(Qx?.[t(11098,25291)]?.()||"").toLowerCase(),'
        'zw=v=>v.startsWith("zh-tw")||v.startsWith("zh-hant")||v==="zh-hk"||v==="zh-mo";'
        'if(zw(zq)||zw(zs))' + tw_menu + ';'
        'return a[e(32212,24019)]()[e(49371,56259)]("zh")?{about:e(12115,23336)+x+"",'
    )
    s = patch(s, old, new, "main-menu-tw")
    write("out/main/electronMain.js", s)


def main():
    patch_i18n()
    patch_main_bundle()
    patch_chunks()
    patch_index()
    patch_main_process()


if __name__ == "__main__":
    main()