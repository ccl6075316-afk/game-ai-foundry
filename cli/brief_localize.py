"""One-shot brief narrative localization (EN → Chinese) for catalog shards."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from brief_shards import (
    is_catalog_ref,
    load_json_shard,
    project_root_for_brief_path,
    resolve_shard_path,
    save_json_shard,
)

Translator = Callable[[str, str], str]

NARRATIVE_KEYS = frozenset(
    {
        "description",
        "art_direction",
        "gameplay_loop",
        "session_goal",
        "summary",
        "notes",
        "usage_description",
    }
)
# Catalog / shard labels — translate English only; leave CJK alone.
LABEL_KEYS = frozenset({"title", "name"})
NEVER_TOUCH = frozenset({"id", "path", "type", "content_class"})

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
BRIEF_ZH_DOC_NAME = "brief.zh.md"


def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _nonempty_str(value: Any) -> str:
    return str(value or "").strip()


def _iter_catalog_sections(brief: dict[str, Any]) -> list[tuple[str, str, list[Any]]]:
    project = brief.get("project") if isinstance(brief.get("project"), dict) else {}
    sections: list[tuple[str, str, list[Any]]] = []
    for key, kind in (("scenes", "scene"), ("systems", "system"), ("assets", "asset")):
        raw = brief.get(key)
        if raw is None and isinstance(project, dict):
            raw = project.get(key)
        if isinstance(raw, list):
            sections.append((key, kind, raw))
    assets_top = brief.get("assets")
    if isinstance(assets_top, list) and not any(s[0] == "assets" for s in sections):
        sections.append(("assets", "asset", assets_top))
    return sections


def _should_translate_field(key: str, text: str) -> bool:
    if key in NEVER_TOUCH:
        return False
    if not _nonempty_str(text):
        return False
    if key in LABEL_KEYS:
        return not contains_cjk(text)
    if key in NARRATIVE_KEYS:
        return True
    return False


def _rewrite_mapping(
    data: dict[str, Any],
    *,
    translator: Translator,
) -> bool:
    """Rewrite narrative/label string fields in place. Returns True if changed."""
    changed = False
    for key, value in list(data.items()):
        if key in NEVER_TOUCH:
            continue
        if isinstance(value, str) and _should_translate_field(key, value):
            new_text = translator(key, value)
            if isinstance(new_text, str) and new_text != value:
                data[key] = new_text
                changed = True
    return changed


def make_llm_translator(config: dict[str, Any]) -> Translator | None:
    """Build a translator that calls host LLM, or None if credentials missing."""
    from llm_config import resolve_host_api_settings
    from prompt_craft import PromptCraftError, chat_text_completion

    api = resolve_host_api_settings(config or {})
    if not api.get("api_key"):
        return None
    model = str(api.get("model") or "")
    api_key = str(api["api_key"])
    api_base = str(api.get("api_base") or "")
    proxy = api.get("proxy")

    def _translate(field_name: str, text: str) -> str:
        if not _nonempty_str(text):
            return text
        if contains_cjk(text):
            return text
        messages = [
            {
                "role": "system",
                "content": (
                    "You translate game brief narrative fields into Simplified Chinese. "
                    "Return ONLY the Chinese translation, no quotes or explanation. "
                    "Keep technical tokens (ids, English enums like 2d/side) when embedded. "
                    "Do not invent new gameplay."
                ),
            },
            {
                "role": "user",
                "content": f"Field: {field_name}\n\nText:\n{text}",
            },
        ]
        try:
            out = chat_text_completion(
                model=model,
                messages=messages,
                api_key=api_key,
                api_base=api_base,
                proxy=str(proxy) if proxy else None,
                timeout=120,
                temperature=0.2,
            )
        except PromptCraftError:
            return text
        cleaned = (out or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned or text

    return _translate


def localize_brief_narratives(
    brief_path: Path,
    *,
    translator: Translator,
    i_confirm: bool,
) -> dict[str, Any]:
    """Rewrite narrative fields to Chinese via translator(field_name, text)->text.

    Returns {ok, changed_paths, skipped} (and error when not confirmed).
    """
    if not i_confirm:
        return {
            "ok": False,
            "error": "brief localize requires --i-confirm",
            "changed_paths": [],
            "skipped": [],
        }

    path = Path(brief_path)
    brief = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(brief, dict):
        return {
            "ok": False,
            "error": "Brief must be a JSON object",
            "changed_paths": [],
            "skipped": [],
        }

    root = project_root_for_brief_path(path)
    changed_paths: list[str] = []
    skipped: list[str] = []
    brief_dirty = False

    project = brief.get("project")
    if isinstance(project, dict) and _rewrite_mapping(project, translator=translator):
        brief_dirty = True

    for section_key, kind, items in _iter_catalog_sections(brief):
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            if _rewrite_mapping(item, translator=translator):
                brief_dirty = True

            if not is_catalog_ref(item, kind=kind):  # type: ignore[arg-type]
                skipped.append(f"{section_key}[{item.get('id') or idx}]: not catalog ref")
                continue
            rel = _nonempty_str(item.get("path"))
            entry_id = _nonempty_str(item.get("id"))
            try:
                shard_path = resolve_shard_path(root, rel)
            except ValueError as exc:
                skipped.append(f"{section_key}[{entry_id}]: {exc}")
                continue
            if not shard_path.is_file():
                skipped.append(f"{section_key}[{entry_id}]: missing {rel}")
                continue
            try:
                shard = load_json_shard(shard_path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                skipped.append(f"{section_key}[{entry_id}]: {exc}")
                continue
            if _rewrite_mapping(shard, translator=translator):
                save_json_shard(shard_path, shard)
                resolved = str(shard_path.resolve())
                if resolved not in changed_paths:
                    changed_paths.append(resolved)

    if brief_dirty:
        path.write_text(
            json.dumps(brief, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        changed_paths.insert(0, str(path.resolve()))

    zh_path = root / BRIEF_ZH_DOC_NAME
    if zh_path.is_file():
        zh_path.unlink()
        zh_resolved = str(zh_path.resolve())
        if zh_resolved not in changed_paths:
            changed_paths.append(zh_resolved)

    return {
        "ok": True,
        "brief_path": str(path.resolve()),
        "changed_paths": changed_paths,
        "skipped": skipped,
    }


_FISH_SPECIES: dict[str, str] = {
    "Common carp": "鲤鱼",
    "Carp": "鲤鱼",
    "Grass carp": "草鱼",
    "Ribbon fish": "带鱼",
    "Sea bream": "鲷鱼",
    "Yellow croaker": "黄花鱼",
    "Atlantic salmon": "大西洋鲑",
    "Yellowfin tuna": "黄鳍金枪鱼",
    "Marlin": "枪鱼",
    "Nile tilapia": "尼罗罗非鱼",
    "Arapaima": "巨骨舌鱼",
    "Piranha": "食人鱼",
    "Peacock bass": "孔雀鲈",
    "Black seabream": "黑鲷",
    "Sea bass": "海鲈",
    "Bluegill": "蓝鳃太阳鱼",
    "Rainbow trout": "虹鳟",
    "Pikeperch": "梭鲈",
    "Trout": "鳟鱼",
    "Murray cod": "墨瑞鳕",
    "Red emperor": "红皇帝鱼",
    "African catfish": "非洲鲶",
    "Nile perch": "尼罗鲈",
    "Goliath tigerfish": "巨人虎鱼",
    "Silver arowana": "银龙鱼",
    "Electric eel": "电鳗",
    "Pacu": "帕库鱼",
    "Great white shark (colossal)": "巨型大白鲨",
    "Humpback whale (colossal, breach presentation)": "巨型座头鲸（跃出展示）",
    "Colossal squid (colossal)": "巨型鱿鱼",
    "Swimming": "游动",
}

_FISHING_EXACT: dict[str, str] = {
    "2D fishing simulation focused on catch-and-collect with endless play. Players roam a coastal hub, pick fishing spots, battle fish on the line, and grow an aquarium/collection. Soft cartoon coastal art; no final win state—fame, tanks, and routes keep expanding. Screen flows and rules live in project.scenes / project.systems shards; this field is overview only.": (
        "以钓获与收集为主的 2D 钓鱼模拟，强调无尽游玩。玩家在海岸枢纽活动、选择钓点、"
        "进行搏鱼，并经营水族馆/图鉴收藏。柔和卡通海岸风；无终局通关——声望、鱼缸与航线持续扩展。"
        "屏流与规则见 project.scenes / project.systems 分册；本字段仅为总览。"
    ),
    "High-density pixel art style inspired by Dave the Diver, with increased pixel density for more detailed and realistic rendering, yet unmistakably pixel art. Cozy nature-themed color palette. Scene-level polar-star / composition contracts live in scenes/<id>.json notes (especially spot_select and tank_view), not here.": (
        "高密度像素风，灵感来自《潜水员戴夫》，像素密度更高、细节更扎实，但仍明确是像素画。"
        "温馨自然色板。场景级北极星/构图契约写在 scenes/<id>.json 的 notes（尤其 spot_select 与 tank_view），不写在这里。"
    ),
    "Hub → choose spot (Harbor) → fish combat → land/sell or keep → aquarium/studio/shop/warehouse loops → return to hub. Tickets, bait, fame, and daily time gate optional routes. Endless; no campaign finale.": (
        "枢纽 → 选钓点（港口）→ 搏鱼战斗 → 上岸出售或保留 → 水族馆/工作室/商店/仓库循环 → 返回枢纽。"
        "门票、鱼饵、声望与每日时间门控为可选路线。无尽玩法；无战役终章。"
    ),
    "Free fishing, collecting species, building aquarium; this phase targets a playable core loop (catch → sell/store → aquarium → repeat) as the demo scope.": (
        "自由钓鱼、收集鱼种、建设水族馆；本阶段目标是可玩核心循环（钓获 → 出售/入库 → 水族馆 → 重复）作为演示范围。"
    ),
    "Seaside coastal environment background without embedded buildings. Clickable entrances are independent transparent building sprites (tackle shop, aquarium, studio, warehouse) placed organically along the coast by code — each building is a whole big button. Dock/harbor spot-select is a code hotspot on the painted pier. All other UI is code-built.": (
        "海边海岸环境背景，不内嵌建筑。可点击入口是独立透明建筑精灵（钓具店、水族馆、工作室、仓库），"
        "由代码沿海岸错落摆放——每栋建筑本身就是整块大按钮。码头/港口的钓点选择是画在码头上的代码热区。其余 UI 由代码搭建。"
    ),
    "View a specific tank as a walk-through aquarium exhibit at monumental scale (section of a vast tank, never the whole tank in one frame). Background art is EMPTY water + scenery only — no ambient fish, no schools. Player-owned fish are layered on by code. Even small tanks read as a window into a grand exhibit, not a home fishtank. Player can admire fish, inspect health/status, open warehouse to add fish, remove fish. Equipment install/upgrade is in this scene's equipment-slot panel. Background per tank type as asset.": (
        "以纪念碑尺度观赏指定鱼缸（巨大展缸的局部，从不整缸入画）。背景仅为空水+景，无环境鱼/鱼群；玩家鱼由代码叠放。"
        "即便小缸也读作宏大展窗而非家用鱼缸。可观赏、查看健康、开仓库加减鱼；装备安装/升级在本场景装备槽面板。缸型背景为资产。"
    ),
    "Documentary editing: select captured footage clips for an episode, then sell it (one-time income) or broadcast it (daily royalties). One episode in production at a time; broadcasted episodes play simultaneously.": (
        "纪录片剪辑：为成片挑选素材片段，然后买断出售（一次性）或播出（每日分成）。同时仅一部在制；已播出片可并行收分成。"
    ),
    "Scrollable world map with real fishing spots (千岛湖, Lake Biwa, Gulf of Alaska, Great Barrier Reef, Mediterranean, Lake Victoria, Amazon River, Paraná River, etc.). Each spot is marked by a small locally-flavored thumbnail. Entered via the Harbor building on main hub.": (
        "可滚动世界地图，标注真实钓点（千岛湖、琵琶湖、阿拉斯加湾、大堡礁、地中海、维多利亚湖、亚马逊河、巴拉那河等）。"
        "每个钓点有当地风味小缩略图。从主界面港口建筑进入。"
    ),
    "First-person sea-fishing view composed in layers: (1) sea/sky background only — no boat, no fisherman; (2) independent transparent boat hull + rod foreground; (3) fish as a dynamic overlay. Cast line, wait ≤3s for a bite, then reel/release tension combat. During normal reeling the fish is NOT rendered — implied by line angle, ripples, and a floating status bar. Fish visible only on leap and in the catch popup.": (
        "第一人称海钓分层构图：(1) 仅海/天背景——无船无渔夫；(2) 独立透明船体+钓竿前景；(3) 鱼为动态叠层。"
        "抛竿后≤3s 咬钩，进入收线/放线张力战斗。普通收线时不渲染鱼——靠线角、涟漪与悬浮状态栏暗示；仅跃出与收获弹窗可见。"
    ),
    "Buy rods, reels, lines, baits, tanks, aquarium equipment, and cosmetics. Reachable from main hub only (not from aquarium).": (
        "购买竿、轮、线、饵、鱼缸、水族设备与外观。仅从主界面可达（不可从水族馆进入）。"
    ),
    "Store equipment and caught fish not yet sold or placed in tanks; upgrade capacity with gold. Fish are stored in a grid inventory (one slot per fish), not row-based x3/x2. Reachable from main hub, and from aquarium hall / tank view (fish only).": (
        "存放尚未出售或入缸的装备与渔获；可用金币扩容。鱼为网格库存（一鱼一格），非 x3/x2 行列。"
        "可自主界面进入，也可从水族馆大厅/鱼缸观赏进入（仅鱼）。"
    ),
    "Full-screen overlay, book-like opening effect, displays all fish species as icon grid with caught/uncaught status and encyclopedia progress (e.g. milestones). UI entirely code-built; no separate background scene asset needed.": (
        "全屏叠层、书册打开效果；以图标网格展示全部鱼种的已/未钓状态与图鉴进度（如里程碑）。UI 全代码搭建，无需单独背景场景资产。"
    ),
    "Tension-based reel/release combat with explicit stamina & endurance bars; two loss conditions.": (
        "基于张力的收线/放线战斗，明确体力与耐力条；两种失败条件。"
    ),
    "Passive maintenance only — buy/upgrade equipment to slow health decay; no feeding/water-change/treatment actions. Lifespan extended by single-use elixirs applied to individual fish.": (
        "仅被动维护——购买/升级设备以减缓健康衰减；无喂食/换水/治疗。寿命靠对单鱼使用的一次性灵药延长。"
    ),
    "Each in-game day has ~10 min of fishing time, counted only by battle duration; settlement triggers at day end.": (
        "每个游戏日约 10 分钟钓鱼时间，仅按战斗时长计入；日终触发结算。"
    ),
    "All numbers interlock from one baseline: common fish battle ~20-30s is the reference beat; everything else derives from it.": (
        "全部数值由同一基线咬合：普通鱼战斗约 20–30 秒为参考节拍，其余由此推导。"
    ),
    "Hire crew before departure, collect footage from catches, edit in Studio into an episode by dragging clips onto a timeline, then sell once or broadcast for daily royalties.": (
        "出发前雇佣摄制组，从渔获收集素材，在工作室时间线拖片段剪成片，然后买断或播出赚每日分成。"
    ),
    "Catching new fish records entries; milestones unlock new spots on the world map.": (
        "钓到新鱼记入图鉴；里程碑解锁世界地图新钓点。"
    ),
    "Bait influences the size and rarity of caught fish; fishing without bait only yields small/common species.": (
        "鱼饵影响渔获体型与稀有度；空钩只能出小型/常见种。"
    ),
    "Fame level provides an income multiplier for aquarium and documentary revenue.": (
        "声望等级为水族馆与纪录片收入提供倍率。"
    ),
    "A fishing game.": "一款钓鱼游戏。",
    "Pixel art.": "像素画风。",
    "Coastal fishing pier overview.": "海岸钓场码头总览。",
    "English summary only.": "仅英文摘要。",
    "English desc.": "英文简介。",
    "English.": "英文。",
    "UI built in code; no text assets.": "UI 由代码搭建；无文字资产。",
    "UI built in code.": "UI 由代码搭建。",
    "Opens like an open book, left/right arrow buttons for page flipping, fish icons on the pages. Uses programmatic layout.": (
        "像打开的书册：左右翻页按钮，页上为鱼图标。程序化布局。"
    ),
    "Swimming. Generate as 1920×1080 landscape swim clip; fish fully in frame with left/right margin for combat/tank crop-scale.": (
        "游动。按 1920×1080 横构图生成游动片段；鱼体完整入框，左右留出战斗/鱼缸裁切边距。"
    ),
}

_PLACE_NAMES: dict[str, str] = {
    "Qiandao Lake": "千岛湖",
    "Lake Biwa (Japan)": "琵琶湖（日本）",
    "Gulf of Alaska (USA)": "阿拉斯加湾（美国）",
    "Great Barrier Reef (Australia)": "大堡礁（澳大利亚）",
    "Mediterranean Sea (Europe)": "地中海（欧洲）",
    "Lake Victoria (Africa)": "维多利亚湖（非洲）",
    "Lake Tanganyika (Africa)": "坦噶尼喀湖（非洲）",
    "Amazon River (South America)": "亚马逊河（南美）",
    "Parana River (South America)": "巴拉那河（南美）",
}

_ITEM_NAMES: dict[str, str] = {
    "Basic rod": "入门钓竿",
    "Basic reel (1x speed)": "入门卷线器（1x 速度）",
    "Metal reel (1.5x speed)": "金属卷线器（1.5x 速度）",
    "Braided line (high tensile)": "编织线（高拉力）",
    "Nylon line (longer)": "尼龙线（更长）",
    "Worm bait": "蚯蚓饵",
    "Shrimp bait": "虾饵",
    "Small tank (~50 units)": "小缸（约 50 容量）",
    "Medium tank (~150 units)": "中缸（约 150 容量）",
    "Large tank (~400 units)": "大缸（约 400 容量）",
    "Parade tank (~1200 units)": "巡游缸（约 1200 容量）",
    "Deep-sea tank (~1500 units)": "深海缸（约 1500 容量）",
    "Open pool (~4000 units)": "开放水池（约 4000 容量）",
    "Oxygenator": "增氧机",
    "Filtration": "过滤系统",
    "Temperature control": "温控",
    "Water quality monitor": "水质监测",
    "Pump": "水泵",
    "Seaweed decoration (cosmetic)": "海草装饰（外观）",
    "Rock decoration (cosmetic)": "岩石装饰（外观）",
    "Protein skimmer (saltwater only)": "蛋白分离器（仅海水）",
    "Salinity monitor (saltwater only)": "盐度监测（仅海水）",
    "Great white shark icon": "大白鲨图标",
    "Humpback whale icon": "座头鲸图标",
    "Colossal squid icon": "巨型鱿鱼图标",
    "Camera icon used on the hire-crew option and in the studio editing UI. No text.": (
        "摄像机图标，用于雇佣摄制组选项与工作室剪辑 UI。不要文字。"
    ),
}

_AQUARIUM_HALL_ZH = (
    "公共水族馆展厅——宽敞通透：大厅开阔、步道宽、层高足，刻意不是逼仄小房间，也不是巨型鱼墙展厅。"
    "背景表现开放大厅，步道两侧内置展缸有适量环境鱼（布景、非玩家鱼）；少量游客作为低细节环境人物。"
    "玩家已购鱼缸由代码动态叠放；点击进入鱼缸观赏。展厅开局即解锁，初始无玩家缸，需在厅内商店购买第一口缸。"
    "此处不可进商店；可进仓库取鱼。"
)


def register_fishing_disk_summaries(brief_root: Path) -> None:
    """Register on-disk English scene summaries (e.g. long aquarium_hall) into the map."""
    hall = Path(brief_root) / "scenes" / "aquarium_hall.json"
    if not hall.is_file():
        return
    try:
        body = load_json_shard(hall)
    except (OSError, json.JSONDecodeError, ValueError):
        return
    summary = body.get("summary")
    if isinstance(summary, str) and summary.strip() and not contains_cjk(summary):
        _FISHING_EXACT.setdefault(summary.strip(), _AQUARIUM_HALL_ZH)


def fishing_offline_translator(field_name: str, text: str) -> str:
    """Deterministic EN→ZH map + patterns for fishing-2d known narratives."""
    raw = text or ""
    s = raw.strip()
    if not s:
        return raw
    if contains_cjk(s) and field_name in LABEL_KEYS:
        return raw
    if contains_cjk(s) and field_name in NARRATIVE_KEYS:
        if len(_CJK_RE.findall(s)) >= 4:
            return raw

    exact = _FISHING_EXACT.get(s)
    if exact is not None:
        return exact

    m = re.match(
        r"^(.+?)\.\s*Generate as 1920[×xX]1080 landscape(?: swim clip)?;(.+)$",
        s,
        flags=re.DOTALL,
    )
    if m:
        species = m.group(1).strip()
        species_zh = _FISH_SPECIES.get(species, species)
        if "swim clip" in s.lower():
            return (
                f"{species_zh}。按 1920×1080 横构图生成游动片段；鱼体完整入框，"
                "左右留出战斗/鱼缸裁切边距。"
            )
        return (
            f"{species_zh}。按 1920×1080 横构图生成；鱼体完整入框，左右留出战斗边距；"
            "透明背景；侧面清晰可读的像素风鱼精灵。"
        )

    low = s.lower()
    if "battle background" in low and "open water" in low:
        water = (
            "淡水"
            if "freshwater" in low
            else "海水"
            if "saltwater" in low
            else "水域"
        )
        return (
            f"{water}战斗背景——仅开阔水面与天空；不要船、不要渔夫、不要鱼；"
            "船与竿作为独立前景精灵叠放。"
        )

    if s.startswith("Main hub coast environment"):
        return (
            "主界面海岸环境——仅海岸/天空/码头/海面；不要烘焙建筑；"
            "钓具店/水族馆/工作室/仓库等建筑为独立透明精灵由代码摆放。"
        )

    if s.startswith("Empty ") and "exhibition background" in low:
        return (
            "空缸展览背景——干净水体/玻璃、纵深与柔光；不要鱼、不要鱼群；"
            "玩家鱼由代码动态叠放。"
        )

    if s.startswith("Spacious, airy public-aquarium"):
        return (
            "宽敞通透的公共水族馆展厅室内：开阔大厅、宽步道；背景含适量环境鱼与游客布景；"
            "玩家鱼缸由代码动态放置。"
        )

    if s.startswith("Documentary editing studio interior"):
        return "纪录片剪辑室内背景（剪辑台、显示器）。UI 留白：目录与按钮由代码搭建。"

    if s.startswith("Fishing shop interior background"):
        return "钓具店室内背景。UI 留白：商品目录与购买按钮由代码搭建。"

    if s.startswith("Warehouse interior background"):
        return "仓库室内背景（货架）。UI 留白：库存网格与升级按钮由代码搭建。"

    if s.startswith("Blank high-density pixel-art stylized real-world map"):
        return (
            "空白高密度像素风写实世界地图背景：可识别大陆轮廓；钓点缩略图由代码叠加；"
            "不要文字/无 UI/无人。"
        )

    if s.startswith("Boat hull + rod foreground"):
        return "战斗用船体+钓竿前景叠层（透明底），风格与战斗背景一致。"

    if s.startswith("Generic locked-spot placeholder"):
        return "世界地图上未解锁钓点的通用锁定占位图。"

    if "thumbnail used whole as a big map button" in low:
        place = s.split(" thumbnail", 1)[0].strip()
        place_zh = _PLACE_NAMES.get(place, place)
        extra = "显示朋友的船码头。" if "friend" in low else "不要文字。"
        return f"{place_zh}缩略图，整图作为大地图按钮使用。{extra}"

    item = _ITEM_NAMES.get(s)
    if item is not None:
        return item

    if re.search(r"\bicon\b", s, flags=re.IGNORECASE) and len(s) < 48:
        base = re.sub(r"\s+icon$", "", s, flags=re.IGNORECASE).strip()
        base_zh = _FISH_SPECIES.get(base, base)
        return f"{base_zh}图标"

    return f"（待全文润色）{s}"
