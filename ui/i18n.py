"""UI strings for the three languages Recipe Lab Studio ships in.

A tiny hand-rolled catalogue rather than Qt Linguist: the UI has ~130 strings, and a dict keeps
each translation next to the code with no .ts/.qm build step. The language is picked once at
start-up (see init_language); the menu writes settings.json and asks for a restart, so no live
window ever has to be re-translated.

Camera enum names (creative styles, effects, brand groups) are deliberately NOT translated — they
are the literal values the camera stores, identical in every language (see core/ranges.py).

Add a language: append its code to LANGUAGES and add that key to every entry below (this module's
smoke test flags any entry that is missing one).
"""
import json
import os

from core.library import home

LANG_HANS = "zh-Hans"
LANG_HANT = "zh-Hant"
LANG_EN = "en"
LANGUAGES = [LANG_HANS, LANG_HANT, LANG_EN]

# ---- the release identity: the About box and the installer both read these from here -------------
AUTHOR = "jiajun zhou"                                                   # the copyright holder
GITHUB_URL = "https://github.com/jjingith/recipe-lab-studio-sony-pmca"   # the official release page
AFDIAN_URL = "https://afdian.com/a/jiajun2160"                           # the donation page
APP_VERSION = "1.4"

# the language names are shown in their own script in every UI language, so anyone can find theirs
LANG_LABEL = {LANG_HANS: "简体中文", LANG_HANT: "繁體中文", LANG_EN: "English"}


STRINGS = {
    # ---------------------------------------------------------------- shell
    "app_name":        {"zh-Hans": "Recipe Lab Studio", "zh-Hant": "Recipe Lab Studio",
                        "en": "Recipe Lab Studio"},
    "tagline":         {"zh-Hans": "把 .cube / 追色目标作品拟合成 RL 配方",
                        "zh-Hant": "把 .cube / 追色目標作品擬合成 RL 配方",
                        "en": "Fit a .cube or a colour target into an RL recipe"},
    "status_ready":    {"zh-Hans": "就绪", "zh-Hant": "就緒", "en": "Ready"},

    # ---------------------------------------------------------------- menu
    "menu_language":   {"zh-Hans": "语言", "zh-Hant": "語言", "en": "Language"},
    "menu_about":      {"zh-Hans": "关于", "zh-Hant": "關於", "en": "About"},
    "about_action":    {"zh-Hans": "关于 Recipe Lab Studio…", "zh-Hant": "關於 Recipe Lab Studio…",
                        "en": "About Recipe Lab Studio…"},
    "restart_title":   {"zh-Hans": "语言", "zh-Hant": "語言", "en": "Language"},
    "restart_body":    {"zh-Hans": "语言已切换为 {0}，重启程序后生效。",
                        "zh-Hant": "語言已切換為 {0}，重啟程式後生效。",
                        "en": "Language switched to {0}. It takes effect after you restart the app."},

    # ---------------------------------------------------------------- about
    "about_title":     {"zh-Hans": "关于 Recipe Lab Studio", "zh-Hant": "關於 Recipe Lab Studio",
                        "en": "About Recipe Lab Studio"},
    "about_version":   {"zh-Hans": "版本 {0}", "zh-Hant": "版本 {0}", "en": "Version {0}"},
    "about_role":      {"zh-Hans": "版权所有人", "zh-Hant": "版權所有人", "en": "Copyright holder"},
    "about_rights":    {"zh-Hans": "© 2026 {0}. 保留所有权利。", "zh-Hant": "© 2026 {0}. 保留所有權利。",
                        "en": "© 2026 {0}. All rights reserved."},
    "about_free_title": {"zh-Hans": "免费声明", "zh-Hant": "免費聲明", "en": "Free-of-charge notice"},
    "about_free_body": {
        "zh-Hans": "本软件永久免费，严禁任何形式的售卖、转卖或捆绑收费。若你是付费买到的，"
                   "说明你被骗了——请到下方的官方发布页免费获取。",
        "zh-Hant": "本軟體永久免費，嚴禁任何形式的販售、轉賣或綑綁收費。若你是付費買到的，"
                   "說明你被騙了——請到下方的官方發布頁免費取得。",
        "en": "This software is permanently free. Any form of selling, reselling or bundling it into "
              "a paid product is strictly forbidden. If you paid for it, you were scammed — get it "
              "for free from the official release page below.",
    },
    "about_repo":      {"zh-Hans": "官方发布地址", "zh-Hant": "官方發布位址", "en": "Official release page"},
    "about_close":     {"zh-Hans": "关闭", "zh-Hant": "關閉", "en": "Close"},

    # ---------------------------------------------------------------- header
    "settings":        {"zh-Hans": "设置", "zh-Hant": "設定", "en": "Settings"},
    "tip_settings":    {"zh-Hans": "程序设置（图像处理方式等）", "zh-Hant": "程式設定（影像處理方式等）",
                        "en": "Program settings (image-processing mode, etc.)"},
    "btn_import_cube": {"zh-Hans": "导入 CUBE", "zh-Hant": "匯入 CUBE", "en": "Import CUBE"},
    "tip_import_cube": {"zh-Hans": "载入 .cube 3D LUT，作为要精确套用的追色目标",
                        "zh-Hant": "載入 .cube 3D LUT，作為要精確套用的追色目標",
                        "en": "Load a .cube 3D LUT as the exact colour target to apply"},
    "btn_portfolio":   {"zh-Hans": "追色目标作品", "zh-Hant": "追色目標作品", "en": "Target photos"},
    "tip_portfolio":   {"zh-Hans": "从一组照片估计整体风格（跨场景统计签名），作为追色目标",
                        "zh-Hant": "從一組照片估計整體風格（跨場景統計簽名），作為追色目標",
                        "en": "Estimate an overall look from a set of photos (a cross-scene "
                              "statistical signature) as the target"},
    "btn_pair":        {"zh-Hans": "配对反推", "zh-Hant": "配對反推", "en": "Pair estimate"},
    "tip_pair":        {"zh-Hans": "给『原片 + 成片』两张同一机位、同一场景的照片，用两者的差异"
                                  "反推出调色风格（差异法抵消场景本身的影响）",
                        "zh-Hant": "給『原片 + 成片』兩張同一機位、同一場景的照片，用兩者的差異"
                                   "反推出調色風格（差異法抵消場景本身的影響）",
                        "en": "Give an original and a graded photo of the same scene from the same "
                              "position; their difference reveals the look (the difference method "
                              "cancels the scene itself)"},
    "btn_open_image":  {"zh-Hans": "打开图片", "zh-Hant": "開啟圖片", "en": "Open photo"},
    "tip_open_image":  {"zh-Hans": "打开一张自己的照片，在预览里试套当前配方",
                        "zh-Hant": "開啟一張自己的照片，在預覽裡試套當前配方",
                        "en": "Open one of your own photos to try the current recipe on it"},
    "btn_fit":         {"zh-Hans": "FIT 拟合", "zh-Hant": "FIT 擬合", "en": "FIT"},
    "tip_fit":         {"zh-Hans": "在当前目标与当前配方之间求解最接近的 RL 参数（拟合）",
                        "zh-Hant": "在當前目標與當前配方之間求解最接近的 RL 參數（擬合）",
                        "en": "Solve for the RL parameters closest to the current target and recipe"},
    "btn_detect":      {"zh-Hans": "检测相机", "zh-Hant": "偵測相機", "en": "Detect camera"},
    "tip_detect":      {"zh-Hans": "扫描可移动磁盘，寻找插着的相机存储卡",
                        "zh-Hant": "掃描可移動磁碟，尋找插著的相機記憶卡",
                        "en": "Scan removable drives for an inserted camera card"},

    # ---------------------------------------------------------------- left panel
    "mod_library":     {"zh-Hans": "滤镜库", "zh-Hant": "濾鏡庫", "en": "Library"},
    "card_none":       {"zh-Hans": "相机: 未检测", "zh-Hant": "相機: 未偵測", "en": "Camera: not detected"},
    "card_found":      {"zh-Hans": "相机: {0} ({1} 条配方)", "zh-Hant": "相機: {0} ({1} 條配方)",
                        "en": "Camera: {0} ({1} recipes)"},
    "filter_ph":       {"zh-Hans": "搜索 名称", "zh-Hant": "搜尋 名稱",
                        "en": "Search name"},
    "tip_filter":      {"zh-Hans": "按滤镜名称筛选左侧列表",
                        "zh-Hant": "依濾鏡名稱篩選左側清單",
                        "en": "Filter the list on the left by filter name"},
    "fav_only":        {"zh-Hans": "只看收藏", "zh-Hant": "只看收藏", "en": "Favourites only"},
    "tip_fav_only":    {"zh-Hans": "只显示已加星收藏的配方", "zh-Hant": "只顯示已加星收藏的配方",
                        "en": "Show only starred recipes"},
    "tip_tree":        {"zh-Hans": "双击内置滤镜可将它复制到自定义",
                        "zh-Hant": "雙擊內建濾鏡可將它複製到自訂",
                        "en": "Double-click a built-in filter to copy it into your own"},

    # ---------------------------------------------------------------- the filter manager
    "btn_manager":     {"zh-Hans": "滤镜管理", "zh-Hant": "濾鏡管理", "en": "Filter manager"},
    "tip_manager":     {"zh-Hans": "打开滤镜管理：自定义排序、分组、批量移动与删除",
                        "zh-Hant": "開啟濾鏡管理：自訂排序、分組、批次移動與刪除",
                        "en": "Open the filter manager: your own order and groups, bulk moves and "
                              "deletions"},
    "mgr_title":       {"zh-Hans": "滤镜管理", "zh-Hant": "濾鏡管理", "en": "Filter manager"},
    "mgr_hint":        {"zh-Hans": "用下面的按钮调整顺序、分组与删除。『应用』只在主界面预览，"
                                   "『保存』才写入磁盘；不保存直接关闭，磁盘不会有任何改动。",
                        "zh-Hant": "用下面的按鈕調整順序、分組與刪除。『套用』只在主介面預覽，"
                                   "『儲存』才寫入磁碟；不儲存直接關閉，磁碟不會有任何改動。",
                        "en": "Use the buttons below to reorder, group and delete. Apply only previews "
                              "the arrangement in the main window; Save is what writes it to disk. "
                              "Close without saving and nothing on disk changes."},
    "mgr_tree_tip":    {"zh-Hans": "Ctrl / Shift 可多选，然后批量移动、排序或删除",
                        "zh-Hant": "Ctrl / Shift 可多選，然後批次移動、排序或刪除",
                        "en": "Ctrl / Shift to select several, then move, reorder or delete them "
                              "together"},
    "mgr_new_group":   {"zh-Hans": "新建分组", "zh-Hant": "新建分組", "en": "New group"},
    "tip_mgr_new_group": {"zh-Hans": "新建一个分组，再把滤镜移动进去",
                          "zh-Hant": "新建一個分組，再把濾鏡移動進去",
                          "en": "Make a new group and move filters into it"},
    "mgr_ren_group":   {"zh-Hans": "重命名分组…", "zh-Hant": "重新命名分組…", "en": "Rename group…"},
    "tip_mgr_ren_group": {"zh-Hans": "重命名选中的分组", "zh-Hant": "重新命名選中的分組",
                          "en": "Rename the selected group"},
    "mgr_del_group":   {"zh-Hans": "删除分组", "zh-Hant": "刪除分組", "en": "Delete group"},
    "tip_mgr_del_group": {"zh-Hans": "删除选中的分组；组内滤镜会回到『未分组』，不会被删除",
                          "zh-Hant": "刪除選中的分組；組內濾鏡會回到『未分組』，不會被刪除",
                          "en": "Delete the selected group. Its filters go back to Ungrouped; none "
                                "of them are deleted"},
    "mgr_del_group_ask": {"zh-Hans": "删除分组『{0}』？组内 {1} 条滤镜会移到『未分组』，不会被删除。",
                          "zh-Hant": "刪除分組『{0}』？組內 {1} 條濾鏡會移到『未分組』，不會被刪除。",
                          "en": "Delete the group '{0}'? Its {1} filters move to Ungrouped and are "
                                "not deleted."},
    "mgr_group_prompt": {"zh-Hans": "分组名称：", "zh-Hant": "分組名稱：", "en": "Group name:"},
    "mgr_group_exists": {"zh-Hans": "已经有一个叫『{0}』的分组了。",
                         "zh-Hant": "已經有一個叫『{0}』的分組了。", "en": "There is already a group named '{0}'."},
    "mgr_name_empty":  {"zh-Hans": "分组名称不能为空。", "zh-Hant": "分組名稱不能為空。",
                        "en": "A group needs a name."},
    "mgr_need_group":  {"zh-Hans": "请先选中一个分组。", "zh-Hant": "請先選中一個分組。",
                        "en": "Select a group first."},
    "mgr_need_filter": {"zh-Hans": "请先选中至少一条滤镜。", "zh-Hant": "請先選中至少一條濾鏡。",
                        "en": "Select at least one filter first."},
    "mgr_move":        {"zh-Hans": "移动", "zh-Hant": "移動", "en": "Move"},
    "tip_mgr_move":    {"zh-Hans": "把选中的滤镜移动到右边下拉框选中的分组",
                        "zh-Hant": "把選中的濾鏡移動到右邊下拉框選中的分組",
                        "en": "Move the selected filters into the group picked in the list on the right"},
    "mgr_ungrouped":   {"zh-Hans": "未分组", "zh-Hant": "未分組", "en": "Ungrouped"},
    "tip_mgr_ungrouped": {"zh-Hans": "未分组：不属于任何自定义分组的滤镜",
                          "zh-Hant": "未分組：不屬於任何自訂分組的濾鏡",
                          "en": "Ungrouped: filters that are in no group of their own"},
    "tip_mgr_group":   {"zh-Hans": "该分组的滤镜", "zh-Hant": "該分組的濾鏡", "en": "The filters in this group"},
    "mgr_up":          {"zh-Hans": "上移", "zh-Hant": "上移", "en": "Up"},
    "tip_mgr_up":      {"zh-Hans": "选中项在所属分组内上移一位；只选中分组时移动分组本身",
                        "zh-Hant": "選中項在所屬分組內上移一位；只選中分組時移動分組本身",
                        "en": "Move the selection one place up inside its group; with only a group "
                              "selected, move that group"},
    "mgr_down":        {"zh-Hans": "下移", "zh-Hant": "下移", "en": "Down"},
    "tip_mgr_down":    {"zh-Hans": "选中项在所属分组内下移一位；只选中分组时移动分组本身",
                        "zh-Hant": "選中項在所屬分組內下移一位；只選中分組時移動分組本身",
                        "en": "Move the selection one place down inside its group; with only a group "
                              "selected, move that group"},
    "mgr_top":         {"zh-Hans": "置顶", "zh-Hant": "置頂", "en": "Top"},
    "tip_mgr_top":     {"zh-Hans": "选中项移到所属分组的最前面",
                        "zh-Hant": "選中項移到所屬分組的最前面",
                        "en": "Move the selection to the front of its group"},
    "mgr_bottom":      {"zh-Hans": "置底", "zh-Hant": "置底", "en": "Bottom"},
    "tip_mgr_bottom":  {"zh-Hans": "选中项移到所属分组的最后面",
                        "zh-Hant": "選中項移到所屬分組的最後面",
                        "en": "Move the selection to the end of its group"},
    "mgr_del_filter":  {"zh-Hans": "删除滤镜", "zh-Hant": "刪除濾鏡", "en": "Delete filters"},
    "tip_mgr_del_filter": {"zh-Hans": "删除选中的滤镜；保存后生效，删除前的副本存入库内 .history",
                           "zh-Hant": "刪除選中的濾鏡；儲存後生效，刪除前的副本存入庫內 .history",
                           "en": "Delete the selected filters. It takes effect on Save; a copy is "
                                 "kept in the library's .history folder"},
    "mgr_del_filter_ask": {"zh-Hans": "删除选中的 {0} 条滤镜？保存后才会真正删除"
                                     "（删除前的副本会存入库内 .history，可手工还原）。",
                           "zh-Hant": "刪除選中的 {0} 條濾鏡？儲存後才會真正刪除"
                                     "（刪除前的副本會存入庫內 .history，可手動還原）。",
                           "en": "Delete the {0} selected filters? They go for good on Save (a copy "
                                 "is kept in the library's .history folder and can be restored by hand)."},
    "mgr_apply":       {"zh-Hans": "应用", "zh-Hant": "套用", "en": "Apply"},
    "tip_mgr_apply":   {"zh-Hans": "只在主界面预览这个排序，不写入磁盘",
                        "zh-Hant": "只在主介面預覽這個排序，不寫入磁碟",
                        "en": "Preview this arrangement in the main window without writing anything"},
    "mgr_save":        {"zh-Hans": "保存", "zh-Hant": "儲存", "en": "Save"},
    "tip_mgr_save":    {"zh-Hans": "把排序、分组与删除写入磁盘并关闭",
                        "zh-Hant": "把排序、分組與刪除寫入磁碟並關閉",
                        "en": "Write the order, groups and deletions to disk, then close"},
    "mgr_cancel":      {"zh-Hans": "取消", "zh-Hant": "取消", "en": "Cancel"},
    "tip_mgr_cancel":  {"zh-Hans": "放弃改动并关闭，磁盘保持原样",
                        "zh-Hant": "放棄改動並關閉，磁碟保持原樣",
                        "en": "Discard the changes and close; the disk stays as it was"},
    "mgr_applied":     {"zh-Hans": "已在主界面预览新排序；点『保存』才会写入磁盘。",
                        "zh-Hant": "已在主介面預覽新排序；點『儲存』才會寫入磁碟。",
                        "en": "Previewing the new arrangement in the library. Save is what writes it "
                              "to disk."},
    "mgr_applied_del": {"zh-Hans": "已在主界面预览新排序（{0} 条待删除）；点『保存』才会写入磁盘。",
                        "zh-Hant": "已在主介面預覽新排序（{0} 條待刪除）；點『儲存』才會寫入磁碟。",
                        "en": "Previewing the new arrangement ({0} staged for deletion). Save is what "
                              "writes it to disk."},
    "mgr_saved":       {"zh-Hans": "滤镜库已保存：{1} 条滤镜，删除 {0} 条。",
                        "zh-Hant": "濾鏡庫已儲存：{1} 條濾鏡，刪除 {0} 條。",
                        "en": "Library saved: {1} filters, {0} deleted."},
    "btn_new":         {"zh-Hans": "新建", "zh-Hant": "新建", "en": "New"},
    "tip_new":         {"zh-Hans": "新建一条空白配方", "zh-Hant": "新建一條空白配方",
                        "en": "Start a blank recipe"},
    "btn_dup":         {"zh-Hans": "复制", "zh-Hant": "複製", "en": "Duplicate"},
    "tip_dup":         {"zh-Hans": "复制选中的配方为一条新配方",
                        "zh-Hant": "複製選中的配方為一條新配方",
                        "en": "Copy the selected recipe into a new one"},
    "btn_del":         {"zh-Hans": "删除", "zh-Hant": "刪除", "en": "Delete"},
    "tip_del":         {"zh-Hans": "从 PC 库删除选中配方（删除前的副本存入库内 .history，可还原）",
                        "zh-Hant": "從 PC 庫刪除選中配方（刪除前的副本存入庫內 .history，可還原）",
                        "en": "Delete the selected recipe from the PC library (a copy is kept in "
                              ".history and can be restored)"},
    "btn_fav":         {"zh-Hans": "☆ 收藏", "zh-Hant": "☆ 收藏", "en": "☆ Favourite"},
    "tip_fav":         {"zh-Hans": "加入 / 取消收藏", "zh-Hant": "加入 / 取消收藏",
                        "en": "Add or remove a favourite"},
    "btn_tags":        {"zh-Hans": "标签…", "zh-Hant": "標籤…", "en": "Tags…"},
    "tip_tags":        {"zh-Hans": "编辑标签（逗号分隔）", "zh-Hant": "編輯標籤（逗號分隔）",
                        "en": "Edit tags (comma-separated)"},
    "btn_dups":        {"zh-Hans": "查重", "zh-Hant": "查重", "en": "Find duplicates"},
    "tip_dups":        {"zh-Hans": "找出外观完全相同的重复配方",
                        "zh-Hant": "找出外觀完全相同的重複配方",
                        "en": "Find recipes that look exactly the same"},
    "btn_history":     {"zh-Hans": "历史", "zh-Hant": "歷史", "en": "History"},
    "tip_history":     {"zh-Hans": "查看并还原历史版本", "zh-Hant": "檢視並還原歷史版本",
                        "en": "View and restore earlier versions"},
    "menu_dup":        {"zh-Hans": "复制", "zh-Hant": "複製", "en": "Duplicate"},
    "menu_rename":     {"zh-Hans": "重命名…", "zh-Hant": "重新命名…", "en": "Rename…"},
    "menu_del":        {"zh-Hans": "删除", "zh-Hant": "刪除", "en": "Delete"},
    "tip_star":        {"zh-Hans": "点击星标加入 / 取消收藏", "zh-Hant": "點擊星標加入 / 取消收藏",
                        "en": "Click the star to add or remove a favourite"},
    "tip_name_only":   {"zh-Hans": "{0}\n{1}", "zh-Hant": "{0}\n{1}", "en": "{0}\n{1}"},
    "btn_push":        {"zh-Hans": "推送 → 卡", "zh-Hant": "推送 → 卡", "en": "Push → card"},
    "tip_push":        {"zh-Hans": "把 PC 库的自定义配方写入相机存储卡（覆盖前自动备份，写完回读校验）",
                        "zh-Hant": "把 PC 庫的自訂配方寫入相機記憶卡（覆蓋前自動備份，寫完回讀校驗）",
                        "en": "Write the PC library's custom recipes to the camera card "
                              "(auto-backup before overwrite, read back to verify)"},
    "btn_pull":        {"zh-Hans": "← 拉取", "zh-Hant": "← 拉取", "en": "← Pull"},
    "tip_pull":        {"zh-Hans": "把相机卡上的配方读入 PC 库",
                        "zh-Hant": "把相機卡上的配方讀入 PC 庫",
                        "en": "Read the recipes on the camera card into the PC library"},
    "btn_restore":     {"zh-Hans": "恢复备份", "zh-Hant": "還原備份", "en": "Restore backup"},
    "tip_restore":     {"zh-Hans": "把卡上 RECIPES/_backup 里的一份备份还原回卡",
                        "zh-Hant": "把卡上 RECIPES/_backup 裡的一份備份還原回卡",
                        "en": "Copy one backup from RECIPES/_backup on the card back onto the card"},
    "chk_fit":         {"zh-Hans": "允许特效(实验)", "zh-Hant": "允許特效(實驗)",
                        "en": "Allow effects (exp.)"},
    "tip_chk_fit":     {"zh-Hans": "允许拟合结果使用 Picture Effect 特效（实验，可能与相机不完全一致）",
                        "zh-Hant": "允許擬合結果使用 Picture Effect 特效（實驗，可能與相機不完全一致）",
                        "en": "Let a fit use Picture Effect styles (experimental; may differ from "
                              "the camera)"},
    "custom_group":    {"zh-Hans": "自定义 (PC 库)  ({0})", "zh-Hant": "自訂 (PC 庫)  ({0})",
                        "en": "Custom (PC library)  ({0})"},
    "builtin_tip":     {"zh-Hans": "{0}\n{1}\n(内置，双击可复制到自定义)",
                        "zh-Hant": "{0}\n{1}\n(內建，雙擊可複製到自訂)",
                        "en": "{0}\n{1}\n(built-in — double-click to copy into Custom)"},
    "tag_line":        {"zh-Hans": "标签: {0}", "zh-Hant": "標籤: {0}", "en": "Tags: {0}"},
    "library_count":   {"zh-Hans": "LIBRARY · {0} 条", "zh-Hant": "LIBRARY · {0} 條",
                        "en": "LIBRARY · {0}"},

    # ---------------------------------------------------------------- centre panel
    "mod_preview":     {"zh-Hans": "预览", "zh-Hant": "預覽", "en": "Preview"},
    "btn_compare":     {"zh-Hans": "对比视图", "zh-Hant": "對比視圖", "en": "Compare"},
    "tip_compare":     {"zh-Hans": "切成单屏对比：拖动中线在原图 / 结果之间擦除；双击中线复位",
                        "zh-Hant": "切成單屏對比：拖動中線在原圖 / 結果之間擦除；雙擊中線復位",
                        "en": "Switch to a single-plate wipe: drag the centre line between the "
                              "original and the result; double-click it to reset"},
    "label_src":       {"zh-Hans": "原图", "zh-Hant": "原圖", "en": "Original"},
    "label_result":    {"zh-Hans": "结果", "zh-Hant": "結果", "en": "Result"},
    "no_image":        {"zh-Hans": "无图像", "zh-Hant": "無影像", "en": "No image"},
    "tip_view":        {"zh-Hans": "滚轮缩放 · 拖拽平移 · 双击复位",
                        "zh-Hant": "滾輪縮放 · 拖曳平移 · 雙擊復位",
                        "en": "Wheel to zoom · drag to pan · double-click to reset"},
    "tip_split":       {"zh-Hans": "拖动中线在原图 / 结果间擦除 · 滚轮缩放 · 拖拽平移 · 双击复位",
                        "zh-Hant": "拖動中線在原圖 / 結果間擦除 · 滾輪縮放 · 拖曳平移 · 雙擊復位",
                        "en": "Drag the line to wipe between original and result · wheel to zoom · "
                              "drag to pan · double-click to reset"},
    "residual_none":   {"zh-Hans": "RESIDUAL —", "zh-Hant": "RESIDUAL —", "en": "RESIDUAL —"},
    "target_none":     {"zh-Hans": "TARGET · 未载入目标", "zh-Hant": "TARGET · 未載入目標",
                        "en": "TARGET · no target loaded"},
    "calib_none":      {"zh-Hans": "校准状态 · —", "zh-Hant": "校準狀態 · —", "en": "Calibration · —"},
    "conf_none":       {"zh-Hans": "置信度 —", "zh-Hant": "置信度 —", "en": "Confidence —"},
    "residual_fmt":    {"zh-Hans": 'RESIDUAL <span style="color:{0}">{1:.2f} Lab</span>  (目标≤{2:.0f})',
                        "zh-Hant": 'RESIDUAL <span style="color:{0}">{1:.2f} Lab</span>  (目標≤{2:.0f})',
                        "en": 'RESIDUAL <span style="color:{0}">{1:.2f} Lab</span>  (target ≤{2:.0f})'},
    "calib_init":      {"zh-Hans": "校准状态 · 初始估算（近似，未实机校准）",
                        "zh-Hant": "校準狀態 · 初始估算（近似，未實機校準）",
                        "en": "Calibration · initial estimate (approximate, not camera-calibrated)"},
    "conf_fmt":        {"zh-Hans": "置信度 {0} {1}%", "zh-Hant": "置信度 {0} {1}%",
                        "en": "Confidence {0} {1}%"},
    "conf_high":       {"zh-Hans": "高", "zh-Hant": "高", "en": "high"},
    "conf_mid":        {"zh-Hans": "中", "zh-Hant": "中", "en": "medium"},
    "conf_low":        {"zh-Hans": "低", "zh-Hant": "低", "en": "low"},
    "out_target_cube": {"zh-Hans": "结果 · 目标 CUBE", "zh-Hant": "結果 · 目標 CUBE",
                        "en": "Result · target CUBE"},
    "out_pair":        {"zh-Hans": "结果 · 配对成片（目标）", "zh-Hant": "結果 · 配對成片（目標）",
                        "en": "Result · pair result (target)"},
    "out_portfolio":   {"zh-Hans": "结果 · 追色目标作品", "zh-Hant": "結果 · 追色目標作品",
                        "en": "Result · target photos"},
    "out_recipe":      {"zh-Hans": "结果 · 配方近似", "zh-Hant": "結果 · 配方近似",
                        "en": "Result · recipe approximation"},
    "out_cube_src":    {"zh-Hans": "结果 · 原图套用 CUBE", "zh-Hant": "結果 · 原圖套用 CUBE",
                        "en": "Result · CUBE applied to original"},
    "out_recipe_src":  {"zh-Hans": "结果 · 配方近似（套用原图）",
                        "zh-Hant": "結果 · 配方近似（套用原圖）",
                        "en": "Result · recipe approximation (on original)"},
    "out_src":         {"zh-Hans": "结果 · 原图", "zh-Hant": "結果 · 原圖", "en": "Result · original"},

    # ---------------------------------------------------------------- right panel
    "mod_params":      {"zh-Hans": "参数", "zh-Hant": "參數", "en": "Parameters"},
    "name_label":      {"zh-Hans": "名称", "zh-Hant": "名稱", "en": "Name"},
    "name_ph":         {"zh-Hans": "≤24 字符，字母数字与 {0}", "zh-Hant": "≤24 字元，字母數字與 {0}",
                        "en": "≤24 chars, letters/digits and {0}"},
    "btn_save":        {"zh-Hans": "保存到库", "zh-Hant": "儲存到庫", "en": "Save to library"},
    "tip_save":        {"zh-Hans": "把当前参数保存为新配方到 PC 库（正在编辑的配方则更新它）",
                        "zh-Hant": "把當前參數儲存為新配方到 PC 庫（正在編輯的配方則更新它）",
                        "en": "Save the current parameters as a new recipe in the PC library "
                              "(or update the one being edited)"},
    "btn_reset":       {"zh-Hans": "还原", "zh-Hant": "還原", "en": "Reset"},
    "tip_reset":       {"zh-Hans": "放弃未保存的改动，回到载入时的参数",
                        "zh-Hant": "放棄未儲存的改動，回到載入時的參數",
                        "en": "Discard unsaved changes and return to the parameters as loaded"},

    # ---------------------------------------------------------------- start / model
    "start_status":    {"zh-Hans": "就绪。导入 .cube 或追色目标作品，然后按 FIT 生成 RL 配方。",
                        "zh-Hant": "就緒。匯入 .cube 或追色目標作品，然後按 FIT 生成 RL 配方。",
                        "en": "Ready. Import a .cube or a colour target, then press FIT to build an "
                              "RL recipe."},
    "model_busy":      {"zh-Hans": "SYS 正在建立前向模型…", "zh-Hant": "SYS 正在建立前向模型…",
                        "en": "SYS building the forward model…"},
    "model_ready":     {"zh-Hans": "SYS 就绪 · 前向模型 77 标定帧。",
                        "zh-Hant": "SYS 就緒 · 前向模型 77 標定幀。",
                        "en": "SYS ready · forward model, 77 calibration frames."},
    "model_fail_title": {"zh-Hans": "模型建立失败", "zh-Hant": "模型建立失敗",
                        "en": "Model build failed"},

    # ---------------------------------------------------------------- import
    "dlg_cube":        {"zh-Hans": "选择 .cube 滤镜", "zh-Hant": "選擇 .cube 濾鏡",
                        "en": "Choose a .cube LUT"},
    "flt_cube":        {"zh-Hans": "Cube LUT (*.cube);;所有文件 (*)", "zh-Hant": "Cube LUT (*.cube);;所有檔案 (*)",
                        "en": "Cube LUT (*.cube);;All files (*)"},
    "cube_fail_title": {"zh-Hans": "Cube 解析失败", "zh-Hant": "Cube 解析失敗", "en": "Cube parse failed"},
    "target_cube":     {"zh-Hans": "TARGET · {0} (cube {1}³)", "zh-Hant": "TARGET · {0} (cube {1}³)",
                        "en": "TARGET · {0} (cube {1}³)"},
    "status_cube":     {"zh-Hans": "已载入 cube：{0}。按 FIT 生成 RL 配方。",
                        "zh-Hant": "已載入 cube：{0}。按 FIT 生成 RL 配方。",
                        "en": "Loaded cube: {0}. Press FIT to build an RL recipe."},
    "dlg_portfolio":   {"zh-Hans": "选择追色目标作品图片", "zh-Hant": "選擇追色目標作品圖片",
                        "en": "Choose the target photos"},
    "flt_img":         {"zh-Hans": "图片 (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;所有文件 (*)",
                        "zh-Hant": "圖片 (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;所有檔案 (*)",
                        "en": "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;All files (*)"},
    "portfolio_noimg": {"zh-Hans": "没有可读的图片", "zh-Hant": "沒有可讀取的圖片",
                        "en": "No readable images"},
    "target_portfolio": {"zh-Hans": "TARGET · 追色目标作品 {0} 张（统计签名）",
                        "zh-Hant": "TARGET · 追色目標作品 {0} 張（統計簽名）",
                        "en": "TARGET · target set of {0} photos (statistical signature)"},
    "status_portfolio": {"zh-Hans": "已载入追色目标作品 {0} 张。跨场景为统计近似，按 FIT 拟合。",
                        "zh-Hant": "已載入追色目標作品 {0} 張。跨場景為統計近似，按 FIT 擬合。",
                        "en": "Loaded {0} target photos. The cross-scene signature is an "
                              "approximation; press FIT."},
    "dlg_pair_before": {"zh-Hans": "选择原图（未调色的原片）", "zh-Hant": "選擇原圖（未調色的原片）",
                        "en": "Choose the original (ungraded) photo"},
    "dlg_pair_after":  {"zh-Hans": "选择成片（目标效果）", "zh-Hant": "選擇成片（目標效果）",
                        "en": "Choose the graded result (the target look)"},
    "pair_fail_title": {"zh-Hans": "配对反推失败", "zh-Hant": "配對反推失敗", "en": "Pair estimate failed"},
    "target_pair":     {"zh-Hans": "TARGET · 配对 {0} → {1}", "zh-Hant": "TARGET · 配對 {0} → {1}",
                        "en": "TARGET · pair {0} → {1}"},
    "status_pair":     {"zh-Hans": "已按『原图→成片』估出风格（差异法，抵消场景本身的影响）。"
                                  "两图需为同一机位同一场景。",
                        "zh-Hant": "已按『原圖→成片』估出風格（差異法，抵消場景本身的影響）。"
                                   "兩圖需為同一機位同一場景。",
                        "en": "Estimated the look from original → result (difference method, "
                              "cancels the scene itself). Both photos must be the same scene from "
                              "the same position."},
    "dlg_open_image":  {"zh-Hans": "打开一张照片", "zh-Hant": "開啟一張照片", "en": "Open a photo"},
    "flt_img_arw":     {"zh-Hans": "图片 (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.arw);;所有文件 (*)",
                        "zh-Hant": "圖片 (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.arw);;所有檔案 (*)",
                        "en": "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.arw);;All files (*)"},
    "open_fail_title": {"zh-Hans": "打开图片失败", "zh-Hant": "開啟圖片失敗", "en": "Open photo failed"},

    # ---------------------------------------------------------------- fit
    "fit_title":       {"zh-Hans": "拟合", "zh-Hant": "擬合", "en": "Fit"},
    "fit_need_target": {"zh-Hans": "请先导入 cube 或追色目标作品作为目标。",
                        "zh-Hant": "請先匯入 cube 或追色目標作品作為目標。",
                        "en": "Import a cube or a colour target first."},
    "fit_not_ready":   {"zh-Hans": "前向模型尚未就绪，请稍候。", "zh-Hant": "前向模型尚未就緒，請稍候。",
                        "en": "The forward model is not ready yet, please wait."},
    "fit_busy":        {"zh-Hans": "FIT 正在拟合参数…", "zh-Hant": "FIT 正在擬合參數…",
                        "en": "FIT solving parameters…"},
    "fit_done":        {"zh-Hans": "拟合完成，残差 {0:.2f} Lab。", "zh-Hant": "擬合完成，殘差 {0:.2f} Lab。",
                        "en": "Fit done, residual {0:.2f} Lab."},
    "fit_fail_title":  {"zh-Hans": "拟合失败", "zh-Hant": "擬合失敗", "en": "Fit failed"},

    # ---------------------------------------------------------------- library ops
    "save_title":      {"zh-Hans": "保存", "zh-Hant": "儲存", "en": "Save"},
    "save_no_recipe":  {"zh-Hans": "没有正在编辑的配方。", "zh-Hant": "沒有正在編輯的配方。",
                        "en": "There is no recipe being edited."},
    "saved_update":    {"zh-Hans": "已更新『{0}』。", "zh-Hant": "已更新『{0}』。", "en": "Updated '{0}'."},
    "saved_add":       {"zh-Hans": "已保存『{0}』到库。", "zh-Hant": "已儲存『{0}』到庫。",
                        "en": "Saved '{0}' to the library."},
    "save_fail_title": {"zh-Hans": "保存失败", "zh-Hant": "儲存失敗", "en": "Save failed"},
    "del_title":       {"zh-Hans": "删除", "zh-Hant": "刪除", "en": "Delete"},
    "del_need_select": {"zh-Hans": "请在『自定义』中选择一条配方。",
                        "zh-Hant": "請在『自訂』中選擇一條配方。",
                        "en": "Select a recipe under Custom first."},
    "del_confirm":     {"zh-Hans": "从 PC 库删除『{0}』？\n（删除前的副本会存入库内 .history 文件夹，可手工还原）",
                        "zh-Hant": "從 PC 庫刪除『{0}』？\n（刪除前的副本會存入庫內 .history 資料夾，可手動還原）",
                        "en": "Delete '{0}' from the PC library?\n(A copy is kept in the .history folder "
                              "inside the library, and can be restored by hand)"},
    "del_done":        {"zh-Hans": "已删除（副本存于库内 .history 文件夹）。",
                        "zh-Hant": "已刪除（副本存於庫內 .history 資料夾）。",
                        "en": "Deleted (a copy is kept in the library's .history folder)."},
    "dup_builtin":     {"zh-Hans": "已复制内置滤镜『{0}』，改名后『保存到库』。",
                        "zh-Hant": "已複製內建濾鏡『{0}』，改名後『儲存到庫』。",
                        "en": "Copied the built-in filter '{0}'. Rename it, then Save to library."},
    "rename_title":    {"zh-Hans": "重命名", "zh-Hant": "重新命名", "en": "Rename"},
    "rename_prompt":   {"zh-Hans": "新的滤镜名称（最多 {0} 个字符）：", "zh-Hant": "新的濾鏡名稱（最多 {0} 個字元）：",
                        "en": "New filter name (up to {0} characters):"},
    "rename_done":     {"zh-Hans": "已重命名为『{0}』。", "zh-Hant": "已重新命名為『{0}』。",
                        "en": "Renamed to '{0}'."},
    "star_add":        {"zh-Hans": "已加入收藏『{0}』。", "zh-Hant": "已加入收藏『{0}』。",
                        "en": "Added '{0}' to favourites."},
    "star_remove":     {"zh-Hans": "已取消收藏『{0}』。", "zh-Hant": "已取消收藏『{0}』。",
                        "en": "Removed '{0}' from favourites."},
    "cube_filter_added": {"zh-Hans": "已按 LUT 名称生成滤镜『{0}』（残差 {1:.2f}）并存入库。",
                        "zh-Hant": "已按 LUT 名稱產生濾鏡『{0}』（殘差 {1:.2f}）並存入庫。",
                        "en": "Created filter '{0}' from the LUT (residual {1:.2f}) and saved it to the library."},
    "fav_title":       {"zh-Hans": "收藏", "zh-Hant": "收藏", "en": "Favourite"},
    "fav_added":       {"zh-Hans": "已加入收藏『{0}』。", "zh-Hant": "已加入收藏『{0}』。",
                        "en": "Added '{0}' to favourites."},
    "fav_removed":     {"zh-Hans": "已取消收藏『{0}』。", "zh-Hant": "已取消收藏『{0}』。",
                        "en": "Removed '{0}' from favourites."},
    "tags_title":      {"zh-Hans": "标签", "zh-Hant": "標籤", "en": "Tags"},
    "tags_prompt":     {"zh-Hans": "用逗号分隔多个标签：", "zh-Hant": "用逗號分隔多個標籤：",
                        "en": "Separate multiple tags with commas:"},
    "tags_done":       {"zh-Hans": "已更新标签。", "zh-Hant": "已更新標籤。", "en": "Tags updated."},
    "dups_title":      {"zh-Hans": "查重", "zh-Hant": "查重", "en": "Find duplicates"},
    "dups_none":       {"zh-Hans": "PC 库里没有外观完全相同的重复配方。",
                        "zh-Hant": "PC 庫裡沒有外觀完全相同的重複配方。",
                        "en": "No duplicate recipes (identical look) in the PC library."},
    "dups_confirm":    {"zh-Hans": "发现 {0} 组外观完全相同的配方：\n\n{1}\n\n保留每组第一条、删除其余？\n"
                                  "（被删的副本会存入库内 .history）",
                        "zh-Hant": "發現 {0} 組外觀完全相同的配方：\n\n{1}\n\n保留每組第一條、刪除其餘？\n"
                                   "（被刪的副本會存入庫內 .history）",
                        "en": "Found {0} groups of identical recipes:\n\n{1}\n\nKeep the first of "
                              "each group and delete the rest?\n(Deleted copies are kept in .history)"},
    "dups_done":       {"zh-Hans": "已删除 {0} 条重复配方。", "zh-Hant": "已刪除 {0} 條重複配方。",
                        "en": "Deleted {0} duplicate recipes."},
    "history_title":   {"zh-Hans": "历史", "zh-Hant": "歷史", "en": "History"},
    "history_dlg":     {"zh-Hans": "历史版本", "zh-Hant": "歷史版本", "en": "Version history"},
    "history_none":    {"zh-Hans": "『{0}』还没有历史版本。", "zh-Hant": "『{0}』還沒有歷史版本。",
                        "en": "'{0}' has no earlier versions yet."},
    "history_prompt":  {"zh-Hans": "『{0}』有 {1} 个历史版本，选择要还原的版本：",
                        "zh-Hant": "『{0}』有 {1} 個歷史版本，選擇要還原的版本：",
                        "en": "'{0}' has {1} earlier versions. Pick the one to restore:"},
    "history_done":    {"zh-Hans": "已还原到 v{0}（还原前的版本也存入了 .history）。",
                        "zh-Hant": "已還原到 v{0}（還原前的版本也存入了 .history）。",
                        "en": "Restored to v{0} (the version replaced is kept in .history too)."},

    # ---------------------------------------------------------------- card
    "card_none_status": {"zh-Hans": "未检测到相机卡。请确认相机处于『大容量存储』并已插入。",
                         "zh-Hant": "未偵測到相機卡。請確認相機處於『大容量儲存』並已插入。",
                         "en": "No camera card detected. Make sure the camera is in Mass Storage "
                               "mode and connected."},
    "card_connected":  {"zh-Hans": "CARD 已连接 {0}。", "zh-Hant": "CARD 已連接 {0}。",
                        "en": "CARD connected: {0}."},
    "card_skipped":    {"zh-Hans": " 跳过 {0} 个文件。", "zh-Hant": " 跳過 {0} 個檔案。",
                        "en": " Skipped {0} file(s)."},
    "push_title":      {"zh-Hans": "推送", "zh-Hant": "推送", "en": "Push"},
    "push_no_recipes": {"zh-Hans": "PC 库里没有自定义配方。", "zh-Hant": "PC 庫裡沒有自訂配方。",
                        "en": "The PC library has no custom recipes."},
    "push_not_writable": {"zh-Hans": "存储卡不能写入：{0}\n\n请检查：\n"
                                    "· 卡侧写保护开关是否处于锁定位置；\n"
                                    "· 相机是否仍占用此卡（先在相机上退出『大容量存储』再重试）；\n"
                                    "· 换一张卡，或改用 pmca-console 推送。",
                          "zh-Hant": "記憶卡不能寫入：{0}\n\n請檢查：\n"
                                     "· 卡側寫保護開關是否處於鎖定位置；\n"
                                     "· 相機是否仍占用此卡（先在相機上退出『大容量儲存』再重試）；\n"
                                     "· 換一張卡，或改用 pmca-console 推送。",
                          "en": "The card is not writable: {0}\n\nPlease check:\n"
                                "· whether the write-protect switch on the card is locked;\n"
                                "· whether the camera still holds the card (leave Mass Storage on "
                                "the camera, then retry);\n"
                                "· another card, or push with pmca-console instead."},
    "push_dlg_title":  {"zh-Hans": "推送到相机", "zh-Hant": "推送到相機", "en": "Push to camera"},
    "push_plan":       {"zh-Hans": "把 PC 库的 {0} 条配方写入 {1}{2}：\n\n· 新增 {3} 条\n"
                                  "· 覆盖 {4} 条（覆盖前自动备份到 {5}）\n· 跳过 {6} 条（卡上已相同）",
                        "zh-Hant": "把 PC 庫的 {0} 條配方寫入 {1}{2}：\n\n· 新增 {3} 條\n"
                                   "· 覆蓋 {4} 條（覆蓋前自動備份到 {5}）\n· 跳過 {6} 條（卡上已相同）",
                        "en": "Write {0} recipes from the PC library to {1}{2}:\n\n· {3} new\n"
                              "· {4} overwritten (auto-backed up to {5} first)\n"
                              "· {6} skipped (already identical on the card)"},
    "push_over_head":  {"zh-Hans": "\n\n将被覆盖的卡上配方：\n", "zh-Hant": "\n\n將被覆蓋的卡上配方：\n",
                        "en": "\n\nCard recipes that will be overwritten:\n"},
    "push_over_row":   {"zh-Hans": "   {0}（卡上为 {1}）", "zh-Hant": "   {0}（卡上為 {1}）",
                        "en": "   {0} (on card: {1})"},
    "push_over_more":  {"zh-Hans": "\n   … 其余 {0} 条", "zh-Hant": "\n   … 其餘 {0} 條",
                        "en": "\n   … {0} more"},
    "push_nothing":    {"zh-Hans": "卡上已有的配方与 PC 库完全一致，无需写入。",
                        "zh-Hant": "卡上已有的配方與 PC 庫完全一致，無需寫入。",
                        "en": "The card already matches the PC library; nothing to write."},
    "push_space_warn": {"zh-Hans": "\n\n⚠ 剩余空间可能不足：需要约 {0:.1f} KB，卡上仅剩 {1:.1f} KB。",
                        "zh-Hant": "\n\n⚠ 剩餘空間可能不足：需要約 {0:.1f} KB，卡上僅剩 {1:.1f} KB。",
                        "en": "\n\n⚠ Possibly not enough space: about {0:.1f} KB needed, only "
                              "{1:.1f} KB free on the card."},
    "push_err_title":  {"zh-Hans": "推送未全部成功", "zh-Hant": "推送未全部成功",
                        "en": "Push not fully successful"},
    "push_err_body":   {"zh-Hans": "{0} 条已写入，以下写入并校验失败：\n\n{1}\n\n"
                                  "失败文件覆盖前的原文件已备份在 {2}，可复制回 {3}{4} 恢复。"
                                  "请检查写保护开关、剩余空间，或改用 pmca-console。",
                        "zh-Hant": "{0} 條已寫入，以下寫入並校驗失敗：\n\n{1}\n\n"
                                   "失敗檔案覆蓋前的原檔案已備份在 {2}，可複製回 {3}{4} 還原。"
                                   "請檢查寫保護開關、剩餘空間，或改用 pmca-console。",
                        "en": "{0} written. These failed to write and verify:\n\n{1}\n\n"
                              "The originals were backed up to {2}; copy them back to {3}{4} to "
                              "recover. Check the write-protect switch and free space, or use "
                              "pmca-console."},
    "push_partial":    {"zh-Hans": "推送部分失败：{0} 条成功、{1} 条失败。",
                        "zh-Hant": "推送部分失敗：{0} 條成功、{1} 條失敗。",
                        "en": "Push partly failed: {0} ok, {1} failed."},
    "push_done_title": {"zh-Hans": "推送完成", "zh-Hant": "推送完成", "en": "Push complete"},
    "push_done_body":  {"zh-Hans": "已写入并回读校验 {0} 条到 {1}{2}。\n\n{3}\n\n"
                                  "拔卡前请先在任务栏『安全删除硬件并弹出媒体』弹出该盘"
                                  "（或让相机断电后再拔卡），否则写入可能还没真正落到卡上。",
                        "zh-Hant": "已寫入並回讀校驗 {0} 條到 {1}{2}。\n\n{3}\n\n"
                                   "拔卡前請先在任務列『安全移除硬體並退出媒體』退出該磁碟"
                                   "（或讓相機斷電後再拔卡），否則寫入可能還沒真正落到卡上。",
                        "en": "Wrote and verified {0} recipes to {1}{2}.\n\n{3}\n\n"
                              "Before unplugging, eject the drive from the taskbar's 'Safely Remove "
                              "Hardware' (or power the camera off first), otherwise the writes may "
                              "not have reached the card."},
    "push_tail_backup": {"zh-Hans": "被覆盖的原文件备份在 {0}",
                         "zh-Hant": "被覆蓋的原檔案備份在 {0}",
                         "en": "Originals that were overwritten are backed up in {0}"},
    "push_tail_none":  {"zh-Hans": "本次没有覆盖任何已有配方。", "zh-Hant": "本次沒有覆蓋任何已有配方。",
                        "en": "No existing recipes were overwritten."},
    "push_done_status": {"zh-Hans": "已推送并校验 {0} 条到 {1}。", "zh-Hant": "已推送並校驗 {0} 條到 {1}。",
                         "en": "Pushed and verified {0} recipes to {1}."},
    "pull_none":       {"zh-Hans": "卡上没有 RECIPES/*.YML 配方。", "zh-Hant": "卡上沒有 RECIPES/*.YML 配方。",
                        "en": "No RECIPES/*.YML recipes on the card."},
    "pull_done":       {"zh-Hans": "从卡拉取 {0} 条。{1}", "zh-Hant": "從卡拉取 {0} 條。{1}",
                        "en": "Pulled {0} from the card. {1}"},
    "restore_title":   {"zh-Hans": "恢复备份", "zh-Hant": "還原備份", "en": "Restore backup"},
    "restore_none":    {"zh-Hans": "卡上还没有备份（RECIPES\\{0}\\ 为空）。",
                        "zh-Hant": "卡上還沒有備份（RECIPES\\{0}\\ 為空）。",
                        "en": "No backups on the card yet (RECIPES\\{0}\\ is empty)."},
    "restore_prompt":  {"zh-Hans": "把一份备份复制回 RECIPES\\（会覆盖卡上当前同名文件）：",
                        "zh-Hant": "把一份備份複製回 RECIPES\\（會覆蓋卡上當前同名檔案）：",
                        "en": "Copy a backup back into RECIPES\\ (overwrites the current file of the "
                              "same name on the card):"},
    "restore_done":    {"zh-Hans": "已把 {0} 从备份还原到卡。", "zh-Hant": "已把 {0} 從備份還原到卡。",
                        "en": "Restored {0} from backup onto the card."},
    "err_prefix":      {"zh-Hans": "错误", "zh-Hant": "錯誤", "en": "Error"},

    # ---------------------------------------------------------------- parameter fields
    "f_style":         {"zh-Hans": "STL 风格", "zh-Hant": "STL 風格", "en": "STL Style"},
    "f_sat":           {"zh-Hans": "SAT 饱和", "zh-Hant": "SAT 飽和", "en": "SAT Saturation"},
    "f_con":           {"zh-Hans": "CON 对比", "zh-Hant": "CON 對比", "en": "CON Contrast"},
    "f_sharp":         {"zh-Hans": "SHP 锐度", "zh-Hant": "SHP 銳度", "en": "SHP Sharpness"},
    "f_pe":            {"zh-Hans": "FX  特效", "zh-Hant": "FX  特效", "en": "FX  Effect"},
    "f_sub":           {"zh-Hans": "SUB 选项", "zh-Hant": "SUB 選項", "en": "SUB Option"},
    "f_wb_mode":       {"zh-Hans": "WB  白平衡", "zh-Hant": "WB  白平衡", "en": "WB  White balance"},
    "f_kelvin":        {"zh-Hans": "KEL 色温", "zh-Hant": "KEL 色溫", "en": "KEL Kelvin"},
    "f_ab":            {"zh-Hans": "A-B", "zh-Hant": "A-B", "en": "A-B"},
    "f_gm":            {"zh-Hans": "G-M", "zh-Hant": "G-M", "en": "G-M"},
    "f_ev":            {"zh-Hans": "EV  曝光", "zh-Hant": "EV  曝光", "en": "EV  Exposure"},
    "f_dro":           {"zh-Hans": "DRO 动态", "zh-Hant": "DRO 動態", "en": "DRO Dynamic"},
    "tip_field_style": {"zh-Hans": "创意风格 STL：相机的色彩基调预设（Standard / Vivid / Neutral…）",
                        "zh-Hant": "創意風格 STL：相機的色彩基調預設（Standard / Vivid / Neutral…）",
                        "en": "Creative Style STL: the camera's base colour preset "
                              "(Standard / Vivid / Neutral…)"},
    "tip_field_sat":   {"zh-Hans": "饱和度 SAT：-3…+3，越大颜色越浓",
                        "zh-Hant": "飽和度 SAT：-3…+3，越大顏色越濃",
                        "en": "Saturation SAT: -3…+3, higher is more saturated"},
    "tip_field_con":   {"zh-Hans": "对比度 CON：-3…+3，越大明暗反差越强",
                        "zh-Hant": "對比度 CON：-3…+3，越大明暗反差越強",
                        "en": "Contrast CON: -3…+3, higher is stronger light/dark contrast"},
    "tip_field_sharp": {"zh-Hans": "锐度 SHP：-3…+3，越大边缘越清晰",
                        "zh-Hant": "銳度 SHP：-3…+3，越大邊緣越清晰",
                        "en": "Sharpness SHP: -3…+3, higher is crisper edges"},
    "tip_field_pe":    {"zh-Hans": "特效 FX：Picture Effect 相机内置特效（玩具相机 / 复古 / HDR 等）",
                        "zh-Hant": "特效 FX：Picture Effect 相機內建特效（玩具相機 / 復古 / HDR 等）",
                        "en": "Effect FX: Picture Effect, the camera's built-in effects "
                              "(Toy Camera / Retro / HDR…)"},
    "tip_field_sub":   {"zh-Hans": "特效子选项 SUB：如玩具相机的色调、半彩色的颜色",
                        "zh-Hant": "特效子選項 SUB：如玩具相機的色調、半彩色的顏色",
                        "en": "Effect sub-option SUB: e.g. the Toy Camera tone, the Part Colour hue"},
    "tip_field_wb_mode": {"zh-Hans": "白平衡 WB：自动 / 指定色温 K / 保持",
                          "zh-Hant": "白平衡 WB：自動 / 指定色溫 K / 保持",
                          "en": "White balance WB: Auto / Kelvin K / Keep"},
    "tip_field_kelvin": {"zh-Hans": "色温 KEL：2500–9900K，越低越暖黄、越高越冷蓝（需白平衡选『色温 K』）",
                         "zh-Hant": "色溫 KEL：2500–9900K，越低越暖黃、越高越冷藍（需白平衡選『色溫 K』）",
                         "en": "Kelvin KEL: 2500–9900K; lower is warmer yellow, higher is cooler "
                               "blue (requires White balance = Kelvin K)"},
    "tip_field_ab":    {"zh-Hans": "A-B 琥珀–蓝：正值偏暖（琥珀），负值偏冷（蓝）",
                        "zh-Hant": "A-B 琥珀–藍：正值偏暖（琥珀），負值偏冷（藍）",
                        "en": "A-B Amber–Blue: positive is warmer (amber), negative is cooler (blue)"},
    "tip_field_gm":    {"zh-Hans": "G-M 绿–品红：正值偏绿，负值偏品红",
                        "zh-Hant": "G-M 綠–洋紅：正值偏綠，負值偏洋紅",
                        "en": "G-M Green–Magenta: positive is greener, negative is more magenta"},
    "tip_field_ev":    {"zh-Hans": "曝光 EV：以 1/3 档为单位", "zh-Hant": "曝光 EV：以 1/3 檔為單位",
                        "en": "Exposure EV: in thirds of a stop"},
    "tip_field_dro":   {"zh-Hans": "动态范围 DRO：关 / 自动 / Lv1–5，提亮暗部",
                        "zh-Hant": "動態範圍 DRO：關 / 自動 / Lv1–5，提亮暗部",
                        "en": "Dynamic Range DRO: Off / Auto / Lv1–5, lifts the shadows"},
    "wb_auto":         {"zh-Hans": "自动", "zh-Hant": "自動", "en": "Auto"},
    "wb_kelvin":       {"zh-Hans": "色温 K", "zh-Hant": "色溫 K", "en": "Kelvin K"},
    "wb_keep":         {"zh-Hans": "保持", "zh-Hant": "保持", "en": "Keep"},
    "dro_off":         {"zh-Hans": "关", "zh-Hant": "關", "en": "Off"},
    "dro_auto":        {"zh-Hans": "自动", "zh-Hant": "自動", "en": "Auto"},

    # ---------------------------------------------------------------- score strip
    "m_light":         {"zh-Hans": "明暗", "zh-Hant": "明暗", "en": "Light"},
    "m_sat":           {"zh-Hans": "饱和", "zh-Hant": "飽和", "en": "Saturation"},
    "m_warm":          {"zh-Hans": "冷暖", "zh-Hant": "冷暖", "en": "Warm-Cool"},
    "m_skin":          {"zh-Hans": "肤色", "zh-Hant": "膚色", "en": "Skin"},
    "m_tone":          {"zh-Hans": "高光阴影", "zh-Hant": "高光陰影", "en": "Hi-Shadow"},
    "md_light":        {"zh-Hans": "ΔL 整体明暗偏差", "zh-Hant": "ΔL 整體明暗偏差",
                        "en": "ΔL overall lightness deviation"},
    "md_sat":          {"zh-Hans": "ΔChroma 彩度偏差", "zh-Hant": "ΔChroma 彩度偏差",
                        "en": "ΔChroma chroma deviation"},
    "md_warm":         {"zh-Hans": "Δb 冷暖（黄–蓝）偏差", "zh-Hant": "Δb 冷暖（黃–藍）偏差",
                        "en": "Δb warm/cool (yellow–blue) deviation"},
    "md_skin":         {"zh-Hans": "暖中间调窗口内的肤色偏差（无肤色样本时显示 —）",
                        "zh-Hant": "暖中間調視窗內的膚色偏差（無膚色樣本時顯示 —）",
                        "en": "Skin deviation within the warm mid-tone window (shows — when the "
                              "frame has no skin samples)"},
    "md_tone":         {"zh-Hans": "按亮度分带后的高光 / 阴影偏差",
                        "zh-Hant": "按亮度分帶後的高光 / 陰影偏差",
                        "en": "Highlight / shadow deviation, split into luminance bands"},
    "score_tip":       {"zh-Hans": "分项为 16×16 签名网格上的 RMS（Lab 单位），≤2 为达标；"
                                  "肤色仅在暖中间调窗口内统计",
                        "zh-Hant": "分項為 16×16 簽名網格上的 RMS（Lab 單位），≤2 為達標；"
                                   "膚色僅在暖中間調視窗內統計",
                        "en": "Each term is an RMS over the 16×16 signature grid, in Lab units; "
                              "≤2 is within tolerance; skin is counted only in the warm mid-tone "
                              "window"},

    # ---------------------------------------------------------------- settings dialog
    "settings_title":  {"zh-Hans": "设置", "zh-Hant": "設定", "en": "Settings"},
    "settings_sec":    {"zh-Hans": "图像处理", "zh-Hant": "影像處理", "en": "Image processing"},
    "settings_note":   {"zh-Hans": "选择图像分析与预览的运算方式。",
                        "zh-Hant": "選擇影像分析與預覽的運算方式。",
                        "en": "Choose how images are analysed and previewed."},
    "settings_cpu":    {"zh-Hans": "CPU 软解", "zh-Hant": "CPU 軟解", "en": "CPU (software)"},
    "settings_cpu_tip": {"zh-Hans": "用 CPU 完成图像分析与预览渲染（当前唯一实现）",
                         "zh-Hant": "用 CPU 完成影像分析與預覽渲染（當前唯一實現）",
                         "en": "Do image analysis and preview rendering on the CPU (currently the "
                               "only implementation)"},
    "settings_gpu":    {"zh-Hans": "GPU 硬解", "zh-Hant": "GPU 硬解", "en": "GPU (hardware)"},
    "settings_gpu_tip": {"zh-Hans": "GPU 硬件加速尚未实现，暂不可选",
                         "zh-Hant": "GPU 硬體加速尚未實現，暫不可選",
                         "en": "GPU acceleration is not implemented yet and cannot be selected"},
    "settings_hint":   {"zh-Hans": "GPU 硬件加速尚未实现，此项为灰色占位；"
                                  "配方拟合与图像分析当前均由 CPU 完成，结果一致。",
                        "zh-Hant": "GPU 硬體加速尚未實現，此項為灰色佔位；"
                                   "配方擬合與影像分析當前均由 CPU 完成，結果一致。",
                        "en": "GPU acceleration is not implemented; this option is a greyed "
                              "placeholder. Fitting and image analysis currently run entirely on "
                              "the CPU, with identical results."},
    "btn_ok":          {"zh-Hans": "确定", "zh-Hant": "確定", "en": "OK"},
    "tip_ok":          {"zh-Hans": "关闭设置", "zh-Hant": "關閉設定", "en": "Close settings"},

    # ---------------------------------------------------------------- theme / workspace
    "settings_action": {"zh-Hans": "图像处理方式…", "zh-Hant": "影像處理方式…",
                        "en": "Image processing…"},
    "theme_day":       {"zh-Hans": "日间模式", "zh-Hant": "日間模式", "en": "Day mode"},
    "theme_night":     {"zh-Hans": "夜间模式", "zh-Hant": "夜間模式", "en": "Night mode"},
    "tip_theme":       {"zh-Hans": "在黑夜 / 日间配色之间切换（立即生效）",
                        "zh-Hant": "在黑／日間配色之間切換（立即生效）",
                        "en": "Switch between the dark and light colour schemes (takes effect at once)"},
    "btn_save_ws":     {"zh-Hans": "保存工作区", "zh-Hant": "儲存工作區", "en": "Save workspace"},
    "tip_save_ws":     {"zh-Hans": "记住当前三个面板的宽度和窗口大小，下次启动自动恢复",
                        "zh-Hant": "記住當前三個面板的寬度與視窗大小，下次啟動自動還原",
                        "en": "Remember the current panel widths and window size, restored on the "
                              "next launch"},
    "ws_saved":        {"zh-Hans": "工作区已保存，下次启动自动恢复。",
                        "zh-Hant": "工作區已儲存，下次啟動自動還原。",
                        "en": "Workspace saved; it will be restored on the next launch."},

    # ---------------------------------------------------------------- compare orientation
    "btn_orient_h":    {"zh-Hans": "横线", "zh-Hant": "橫線", "en": "Horizontal"},
    "btn_orient_v":    {"zh-Hans": "竖线", "zh-Hant": "豎線", "en": "Vertical"},
    "tip_orient":      {"zh-Hans": "切换对比分界线方向：横线（上下擦除）/ 竖线（左右擦除）",
                        "zh-Hant": "切換對比分界線方向：橫線（上下擦除）／豎線（左右擦除）",
                        "en": "Flip the divider: horizontal (wipe top/bottom) or vertical "
                              "(wipe left/right)"},

    # ---------------------------------------------------------------- drag & drop
    "drop_bad":        {"zh-Hans": "只支持拖入图片文件（jpg / png / tif …）。",
                        "zh-Hant": "只支援拖入圖片檔（jpg / png / tif …）。",
                        "en": "Only image files can be dropped here (jpg / png / tif …)."},
    "tip_drop_preview": {"zh-Hans": "也可以直接把一张图片拖到这里当预览图",
                         "zh-Hant": "也可以直接把一張圖片拖到這裡當預覽圖",
                         "en": "You can also drop an image straight onto here to preview it"},
    "tip_drop_portfolio": {"zh-Hans": "也可以直接把多张图片拖到这里，导入为追色目标作品",
                           "zh-Hant": "也可以直接把多張圖片拖到這裡，匯入為追色目標作品",
                           "en": "You can also drop several images straight onto here to import "
                                 "them as a colour target"},

    # ---------------------------------------------------------------- portfolio browser
    "portfolio_view_title": {"zh-Hans": "追色目标作品", "zh-Hant": "追色目標作品",
                             "en": "Colour target"},
    "portfolio_view_count": {"zh-Hans": "已选 {0} / 共 {1} 张", "zh-Hant": "已選 {0} / 共 {1} 張",
                             "en": "{0} of {1} selected"},
    "portfolio_pick_hint": {"zh-Hans": "只有勾选的照片会参与 FIT 拟合。",
                            "zh-Hant": "只有勾選的照片會參與 FIT 擬合。",
                            "en": "Only the ticked photos are used when you fit."},
    "portfolio_need_one": {"zh-Hans": "至少要保留一张照片。", "zh-Hant": "至少要保留一張照片。",
                           "en": "At least one photo has to stay selected."},
    "portfolio_few_hint": {"zh-Hans": "（少于 2 张时统计意义会变弱）",
                           "zh-Hant": "（少於 2 張時統計意義會變弱）",
                           "en": "(with fewer than 2, the statistics get weak)"},
    "btn_all":         {"zh-Hans": "全选", "zh-Hant": "全選", "en": "Select all"},
    "btn_none":        {"zh-Hans": "全不选", "zh-Hant": "全不選", "en": "Select none"},
    "btn_ws_view":     {"zh-Hans": "查看作品集", "zh-Hant": "檢視作品集", "en": "View target"},
    "tip_ws_view":     {"zh-Hans": "打开浏览窗口，勾选参与拟合的照片",
                        "zh-Hant": "開啟瀏覽視窗，勾選參與擬合的照片",
                        "en": "Open the browser to tick which photos take part in the fit"},

    # ---------------------------------------------------------------- histogram / metadata
    "hist_title":      {"zh-Hans": "直方图", "zh-Hant": "直方圖", "en": "Histogram"},
    "hist_before":     {"zh-Hans": "应用滤镜前", "zh-Hant": "套用濾鏡前", "en": "Before"},
    "hist_after":      {"zh-Hans": "应用滤镜后", "zh-Hant": "套用濾鏡後", "en": "After"},
    "tip_hist_switch": {"zh-Hans": "切换直方图：应用滤镜前（原片）/ 应用滤镜后（结果图）",
                        "zh-Hant": "切換直方圖：套用濾鏡前（原片）／套用濾鏡後（結果圖）",
                        "en": "Switch the histogram between before (the original) and after "
                              "(the result)"},
    "meta_iso":        {"zh-Hans": "ISO {0}", "zh-Hant": "ISO {0}", "en": "ISO {0}"},
    "meta_shutter":    {"zh-Hans": "快门 {0}", "zh-Hant": "快門 {0}", "en": "Shutter {0}"},
    "meta_aperture":   {"zh-Hans": "光圈 {0}", "zh-Hant": "光圈 {0}", "en": "Aperture {0}"},
    "meta_focal":      {"zh-Hans": "焦距 {0}", "zh-Hant": "焦距 {0}", "en": "Focal {0}"},
    "meta_none":       {"zh-Hans": "无 EXIF 信息", "zh-Hant": "無 EXIF 資訊",
                        "en": "No EXIF data"},

    # ---------------------------------------------------------------- donation pop-up
    "donate_title":    {"zh-Hans": "请我喝杯咖啡？", "zh-Hant": "請我喝杯咖啡？",
                        "en": "Buy me a coffee?"},
    "donate_body": {
        "zh-Hans": "这个软件一直免费，也会继续免费，没有付费版。如果它帮你省了事，欢迎到爱发电"
                   "请我喝杯咖啡 —— 打赏完全自愿，不会获得额外功能或优先支持，软件对所有用户"
                   "一视同仁。",
        "zh-Hant": "這個軟體一直免費，也會繼續免費，沒有付費版。如果它幫你省了事，歡迎到愛發電"
                   "請我喝杯咖啡 —— 打賞完全自願，不會獲得額外功能或優先支援，軟體對所有使用者"
                   "一視同仁。",
        "en": "This software is free, and will stay free — there is no paid edition. If it saved "
              "you some work, you are welcome to buy me a coffee on Afdian. Donating is entirely "
              "voluntary: it unlocks no extra feature and no priority support, and every user is "
              "treated the same."},
    "donate_btn_open": {"zh-Hans": "打开爱发电", "zh-Hant": "開啟愛發電", "en": "Open Afdian"},
    "donate_btn_close": {"zh-Hans": "以后再说", "zh-Hant": "以後再說", "en": "Maybe later"},
    "donate_chk_hide": {"zh-Hans": "不再显示这个提醒", "zh-Hant": "不再顯示這個提醒",
                        "en": "Do not show this again"},
    "settings_donate": {"zh-Hans": "启动时显示爱发电支持提醒",
                        "zh-Hant": "啟動時顯示愛發電支持提醒",
                        "en": "Show the Afdian support reminder at start-up"},
    "settings_donate_tip": {"zh-Hans": "取消勾选后，程序启动时不再弹出支持提醒",
                            "zh-Hant": "取消勾選後，程式啟動時不再彈出支持提醒",
                            "en": "When unticked, the support reminder no longer appears at start-up"},
}


# ------------------------------------------------------------ state / config
SETTINGS_PATH = os.path.join(home(), "settings.json")

_current = LANG_HANS


def get_language():
    return _current


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else LANG_HANS


def load_config():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(**kw):
    data = load_config()
    data.update(kw)
    tmp = SETTINGS_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, SETTINGS_PATH)
    except OSError:
        pass


def detect_system_language():
    """the language to use when settings.json has none: Chinese script by territory, else English"""
    from PySide6 import QtCore
    loc = QtCore.QLocale.system()
    if loc.language() == QtCore.QLocale.Chinese:
        if loc.territory() in (QtCore.QLocale.Taiwan, QtCore.QLocale.HongKong, QtCore.QLocale.Macau):
            return LANG_HANT
        return LANG_HANS
    return LANG_EN


def init_language():
    """pick the language once, before any window is built: the saved choice, else the system's"""
    code = load_config().get("lang")
    set_language(code if code in LANGUAGES else detect_system_language())


def t(key, *args, **kw):
    """the string for `key` in the current language, with str.format applied to any arguments.

    A missing key returns the key itself, so an untranslated string is obvious on screen."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    s = entry.get(_current) or entry.get(LANG_EN) or key
    return s.format(*args, **kw) if (args or kw) else s
