# -*- coding: utf-8 -*-
"""Patch Qoder 0.5.12 renderer/main files to add a zh-TW language option.

Reads pristine files from work/0512-original, writes patched copies to
/tmp/qoder_asar_0512/out preserving the asar-relative paths (out/...).
Adapted from patch_app_files_057.py with 0.5.12 anchors.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_app_files import convert_js_strings_acorn as convert_js_strings, patch  # noqa: E402
from patch_app_files_056 import mask_object  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "work" / "0512-original"
DICT = ROOT / "work" / "0512-dict"
OUT = Path("/tmp/qoder_asar_0512/out")

I18N_FILE = "C4HI_h4X.js"
MAIN_BUNDLE = "CAGvh22m.js"

CONVERT_CHUNKS = [
    "Cc0Q_zSB.js", "DnRI3XG6.js", "Dta6yTTQ.js", "DonN8_qu.js",
    "BicF1FJE.js", "ozSfTnrI.js", "D1eLu6vA.js",
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
    s = (ORIG / f"out/renderer/assets/{I18N_FILE}").read_text("utf-8")

    tw = load_dict("tw_base.json")
    s = patch(
        s,
        ',Ye="loop.language";',
        ',Ye="loop.language";zt["zh-TW"]={translation:' + compact(tw) + "};",
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
        'on=Qt.filter(({value:i})=>i==="zh"||i==="en")',
        'on=Qt.filter(({value:i})=>i==="zh"||i==="en"||i==="zh-TW")',
        "i18n-available-filter",
    )
    s = patch(
        s,
        'return/^zh-(?:hant-)?(?:hk|mo)(?:-|$)/.test(e)?"zh-HK":',
        'return/^zh-(?:hant-)?(?:tw|hk|mo)(?:-|$)/.test(e)?"zh-TW":',
        "i18n-locale-normalize",
    )
    write(f"out/renderer/assets/{I18N_FILE}", s)


def patch_main_bundle():
    s = (ORIG / f"out/renderer/assets/{MAIN_BUNDLE}").read_text("utf-8")

    s, d2t_orig = mask_object(s, "D2t")
    s, kbt_orig = mask_object(s, "kBt")
    name_orig = '"Siqi Liu （刘思齐）"'
    s = patch(s, name_orig, '"Siqi Liu QODERNAME"', "mask-developer-name")

    s = convert_js_strings(s)

    s = patch(s, '"Siqi Liu QODERNAME"', name_orig, "restore-developer-name")
    mf2_tw = load_dict("mf2_tw.json")
    fT2_tw = load_dict("fT2_tw.json")
    s = patch(
        s, "const D2t=0",
        d2t_orig + ';D2t["zh-TW"]=' + compact(mf2_tw),
        "issue-drawer-resource",
    )
    s = patch(
        s, "const kBt=0",
        kbt_orig + ';kBt["zh-TW"]=' + compact(fT2_tw),
        "project-board-resource",
    )

    s = patch(
        s,
        'value:d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",O=>{Ue.changeLanguage(O)}',
        'value:d==="zh-TW"?"zh-TW":d?.startsWith("zh")?"zh":"en",onValueChange:C("gui_c281a341ec7887fa",O=>{Ue.changeLanguage(O),localStorage.setItem("loop.language",O)}',
        "avatar-value",
    )
    s = patch(
        s,
        'children:"中文"}),s.jsx(o0,{value:"en","data-qoder-gui-id":"gui_8d0ca484b6c46313"',
        'children:"中文"}),s.jsx(o0,{value:"zh-TW","data-qoder-gui-id":"gui_zh_tw_language","data-qoder-gui-activation":"pointerup",children:"繁體中文"}),s.jsx(o0,{value:"en","data-qoder-gui-id":"gui_8d0ca484b6c46313"',
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
        'languageOptions:i==="en"?[{value:"zh",label:"CN"},{value:"en",label:"EN"}]:[{value:"zh",label:"中文"},{value:"en",label:"英文"}]',
        'languageOptions:i==="en"?[{value:"zh",label:"CN"},{value:"en",label:"EN"},{value:"zh-TW",label:"TW"}]:[{value:"zh",label:"中文"},{value:"en",label:"英文"},{value:"zh-TW",label:"繁體中文"}]',
        "login-options",
    )
    s = patch(
        s,
        'onLanguageChange:C("gui_71055172be4221a9",A=>d(A==="en"?"en":"zh")',
        'onLanguageChange:C("gui_71055172be4221a9",A=>d(A)',
        "login-language-change",
    )
    write(f"out/renderer/assets/{MAIN_BUNDLE}", s)


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
        'function KLx(f,e=""){function x(c,n){return t(n,c-333)}'
        'return f[x(36462,30078)]()[x(40203,68735)]("zh")?{about:'
    )
    tw_menu = (
        'return{about:"關於 "+e+"",checkForUpdates:"檢查更新",settings:"設定",'
        'file:"檔案",edit:"編輯",view:"顯示",window:"視窗",help:"說明",'
        'close:"關閉視窗",undo:"還原",redo:"重做",cut:"剪下",copy:"拷貝",'
        'paste:"貼上",pasteAndMatchStyle:"貼上並符合樣式",delete:"刪除",'
        'selectAll:"全選",reload:"重新載入",forceReload:"強制重新載入",'
        'toggleDevTools:"切換開發人員工具",resetZoom:"重設縮放",zoomIn:"放大",'
        'zoomOut:"縮小",toggleFullscreen:"切換全螢幕",minimize:"縮到最小",'
        'zoom:"縮放",front:"全部置於最前",services:"服務",hide:"隱藏 "+e+"",'
        'hideOthers:"隱藏其他",unhide:"顯示全部",quit:"結束 "+e+"",'
        'newWindow:"新增視窗"}'
    )
    new = (
        'function KLx(f,e=""){function x(c,n){return t(n,c-333)}'
        'const zq=String(f).toLowerCase(),'
        'zs=String(xe?.[t(-8600,6468)]?.()||"").toLowerCase(),'
        'zw=v=>v.startsWith("zh-tw")||v.startsWith("zh-hant")||v==="zh-hk"||v==="zh-mo";'
        'if(zw(zq)||zw(zs))' + tw_menu + ';'
        'return f[x(36462,30078)]()[x(40203,68735)]("zh")?{about:'
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