"""Scaffold Godot .NET project shell from production.json."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from godot_assemble import init_project_from_template
from production import load_production, validate_production

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Godot 4 physical_keycode for common keys (InputEventKey)
_KEY_PHYSICAL: dict[str, int] = {
    "A": 65,
    "B": 66,
    "D": 68,
    "E": 69,
    "F": 70,
    "G": 71,
    "H": 72,
    "J": 74,
    "K": 75,
    "L": 76,
    "Q": 81,
    "R": 82,
    "S": 83,
    "W": 87,
    "Space": 32,
    "Left": 4194319,
    "Right": 4194321,
    "Up": 4194320,
    "Down": 4194322,
}


class GodotScaffoldError(RuntimeError):
    pass


def _pascal_case(name: str) -> str:
    parts = re.split(r"[_\-\s]+", name.strip())
    return "".join(p.capitalize() for p in parts if p) or "Player"


def _safe_namespace(slug: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]", "", _pascal_case(slug))
    if not base or base[0].isdigit():
        base = f"Game{base}"
    return base or "GameFactoryDemo"


def default_project_path(production: dict[str, Any]) -> Path:
    doc = production.get("production_doc") or {}
    slug = str(doc.get("slug") or "game").strip() or "game"
    return (_REPO_ROOT / "games" / slug).resolve()


def _key_event_line(physical_keycode: int) -> str:
    return (
        'Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"",'
        f'"device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,'
        f'"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,'
        f'"physical_keycode":{physical_keycode},"key_label":0,"unicode":0,'
        f'"location":0,"echo":false,"script":null)'
    )


def _input_map_block(input_map: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in input_map:
        action = str(entry.get("action", "")).strip()
        keys = entry.get("keys") or []
        if not action:
            continue
        events: list[str] = []
        for key in keys:
            code = _KEY_PHYSICAL.get(str(key).strip())
            if code is not None:
                events.append(_key_event_line(code))
        if not events:
            continue
        lines.append(f"{action}={{")
        lines.append('"deadzone": 0.5,')
        lines.append(f'"events": [{", ".join(events)}]')
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def _physics_layers_block(layers: dict[str, Any]) -> str:
    if not layers:
        return ""
    lines = ["", "[layer_names]", ""]
    for i, (name, _bit) in enumerate(sorted(layers.items(), key=lambda x: x[1]), start=1):
        lines.append(f'2d_physics/layer_{i}="{name}"')
    lines.append("")
    return "\n".join(lines)


def write_project_godot(project_path: Path, doc: dict[str, Any]) -> None:
    """Patch project.godot: name, viewport, main scene, input, layers, autoload."""
    godot_file = project_path / "project.godot"
    if not godot_file.is_file():
        raise GodotScaffoldError(f"Missing project.godot in {project_path}")

    title = str(doc.get("title") or "Game")
    slug = str(doc.get("slug") or "game")
    namespace = _safe_namespace(slug)
    viewport = doc.get("viewport") if isinstance(doc.get("viewport"), dict) else {}
    width = int(viewport.get("width", 1280))
    height = int(viewport.get("height", 720))
    scaffold = doc.get("scaffold") if isinstance(doc.get("scaffold"), dict) else {}
    main_scene = str(scaffold.get("main_scene") or "scenes/main.tscn")
    autoloads = scaffold.get("autoloads") or ["GameState"]

    content = godot_file.read_text(encoding="utf-8")
    content = re.sub(
        r'config/name="[^"]*"',
        f'config/name="{title}"',
        content,
        count=1,
    )
    content = re.sub(
        r'run/main_scene="[^"]*"',
        f'run/main_scene="res://{main_scene}"',
        content,
        count=1,
    )
    content = re.sub(
        r"project/assembly_name=\"[^\"]*\"",
        f'project/assembly_name="{namespace}"',
        content,
        count=1,
    )
    content = re.sub(
        r"window/size/viewport_width=\d+",
        f"window/size/viewport_width={width}",
        content,
        count=1,
    )
    content = re.sub(
        r"window/size/viewport_height=\d+",
        f"window/size/viewport_height={height}",
        content,
        count=1,
    )

    # Replace [input] section
    input_block = _input_map_block(doc.get("input_map") or [])
    if "[input]" in content:
        content = re.sub(
            r"\[input\][\s\S]*?(?=\n\[layer_names\]|\n\[physics\]|\Z)",
            f"[input]\n\n{input_block}",
            content,
            count=1,
        )
    else:
        content += f"\n[input]\n\n{input_block}"

    layers_block = _physics_layers_block(doc.get("physics_layers") or {})
    if layers_block and "[layer_names]" not in content:
        content += layers_block

    # Autoload GameState
    for name in autoloads:
        script = f"res://scripts/{name}.cs"
        autoload_line = f'{name}="*res://scripts/{name}.cs"'
        if "[autoload]" in content:
            if f'{name}=' not in content:
                content = content.replace("[autoload]\n", f"[autoload]\n\n{autoload_line}\n")
        else:
            content += f"\n[autoload]\n\n{autoload_line}\n"

    godot_file.write_text(content, encoding="utf-8")

    csproj = next(project_path.glob("*.csproj"), None)
    if csproj:
        text = csproj.read_text(encoding="utf-8")
        text = re.sub(r"<RootNamespace>[^<]+</RootNamespace>", f"<RootNamespace>{namespace}</RootNamespace>", text)
        text = re.sub(r"<AssemblyName>[^<]+</AssemblyName>", f"<AssemblyName>{namespace}</AssemblyName>", text)
        if "tests/**" not in text and "tests\\**" not in text:
            text = text.replace(
                "</PropertyGroup>",
                "    <DefaultItemExcludes>$(DefaultItemExcludes);tests\\**;tests/**</DefaultItemExcludes>\n  </PropertyGroup>",
                1,
            )
        csproj.write_text(text, encoding="utf-8")


def _write_player_scene(
    project_path: Path,
    scene: dict[str, Any],
    *,
    player_script: str,
    namespace: str,
) -> None:
    rel = str(scene.get("path") or "scenes/player.tscn")
    path = project_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    script_path = scene.get("script") or player_script
    hitbox = {"width": 28, "height": 44}

    text = f"""[gd_scene load_steps=3 format=3 uid="uid://gf_player"]

[ext_resource type="Script" path="res://{script_path}" id="1_player"]

[sub_resource type="RectangleShape2D" id="RectangleShape2D_hitbox"]
size = Vector2({hitbox['width']}, {hitbox['height']})

[node name="Player" type="CharacterBody2D"]
script = ExtResource("1_player")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
position = Vector2(0, {-hitbox['height'] // 2})
shape = SubResource("RectangleShape2D_hitbox")

[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]
"""
    path.write_text(text, encoding="utf-8")


def _write_main_scene(
    project_path: Path,
    scene: dict[str, Any],
    *,
    player_scene_rel: str,
    viewport: dict[str, Any],
) -> None:
    rel = str(scene.get("path") or "scenes/main.tscn")
    path = project_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    w = int(viewport.get("width", 1280))
    h = int(viewport.get("height", 720))
    spawn_x = w // 2
    spawn_y = int(h * 0.55)

    has_camera = any(
        isinstance(c, dict) and c.get("type") == "Camera2D"
        for c in (scene.get("children") or [])
    )
    has_hud = any(
        isinstance(c, dict) and c.get("role") == "hud"
        for c in (scene.get("children") or [])
    )

    lines = [
        '[gd_scene load_steps=3 format=3 uid="uid://gf_main"]',
        "",
        '[ext_resource type="Script" path="res://scripts/Main.cs" id="1_main"]',
        f'[ext_resource type="PackedScene" path="res://{player_scene_rel}" id="2_player"]',
        "",
        '[node name="Main" type="Node2D"]',
        'script = ExtResource("1_main")',
        "",
        '[node name="World" type="Node2D" parent="."]',
        "",
        f'[node name="PlayerSpawn" type="Marker2D" parent="."]',
        f"position = Vector2({spawn_x}, {spawn_y})",
        "",
        f'[node name="Player" parent="." instance=ExtResource("2_player")]',
        f"position = Vector2({spawn_x}, {spawn_y})",
        "",
    ]
    if has_camera:
        lines.extend(
            [
                '[node name="Camera2D" type="Camera2D" parent="Player"]',
                "position = Vector2(0, 0)",
                "",
            ]
        )
    if has_hud:
        lines.extend(
            [
                '[node name="HUD" type="CanvasLayer" parent="."]',
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _script_main(namespace: str) -> str:
    return f"""using Godot;

namespace {namespace};

/// <summary>Main scene root — scaffold shell from production.json.</summary>
public partial class Main : Node2D
{{
    public override void _Ready()
    {{
        GD.Print("{namespace}: main scene loaded (scaffold).");
    }}
}}
"""


def _script_player_controller(
    namespace: str,
    class_name: str,
    *,
    move_speed: float,
    jump_velocity: float,
    gravity: float,
    has_jump: bool,
    has_vertical_move: bool,
) -> str:
    if has_vertical_move:
        direction_expr = 'Input.GetVector("move_left", "move_right", "move_up", "move_down")'
    else:
        direction_expr = 'new Vector2(Input.GetAxis("move_left", "move_right"), 0)'
    jump_block = ""
    physics = "MoveAndSlide();"
    if has_jump:
        jump_block = f"""
    private float _gravity = {gravity}f;
    private float _jumpVelocity = {jump_velocity}f;

    public override void _PhysicsProcess(double delta)
    {{
        Vector2 velocity = Velocity;
        if (!IsOnFloor())
            velocity.Y += _gravity * (float)delta;
        if (Input.IsActionJustPressed("jump") && IsOnFloor())
            velocity.Y = _jumpVelocity;

        Vector2 direction = {direction_expr};
        velocity.X = direction.X * {move_speed}f;
        Velocity = velocity;
        MoveAndSlide();
        if (_sprite != null && direction.X != 0)
            _sprite.FlipH = direction.X < 0;
    }}
"""
        physics = ""
    else:
        jump_block = f"""
    public override void _PhysicsProcess(double delta)
    {{
        Vector2 direction = {direction_expr};
        Velocity = direction * {move_speed}f;
        MoveAndSlide();
        if (_sprite != null && direction.X != 0)
            _sprite.FlipH = direction.X < 0;
    }}
"""

    return f"""using Godot;

namespace {namespace};

/// <summary>Player controller — scaffold stub; extend per production.godot_tasks.</summary>
public partial class {class_name} : CharacterBody2D
{{
    private AnimatedSprite2D? _sprite;

    public override void _Ready()
    {{
        _sprite = GetNodeOrNull<AnimatedSprite2D>("AnimatedSprite2D");
    }}
{jump_block}
}}
"""


def _script_game_state(namespace: str, *, health: int = 3) -> str:
    return f"""using Godot;

namespace {namespace};

/// <summary>Global game state autoload — wraps unit-testable PlayerStats.</summary>
public partial class GameState : Node
{{
    public static GameState Instance {{ get; private set; }} = null!;

    private PlayerStats _stats = new({health});

    public int Health
    {{
        get => _stats.Health;
        set
        {{
            _stats = new PlayerStats(value, _stats.Score);
        }}
    }}

    public int Score
    {{
        get => _stats.Score;
        set
        {{
            _stats = new PlayerStats(_stats.Health, value);
        }}
    }}

    public bool IsAlive => _stats.IsAlive;

    public override void _Ready()
    {{
        Instance = this;
    }}

    public void TakeDamage(int amount) => _stats.TakeDamage(amount);

    public void AddScore(int points) => _stats.AddScore(points);
}}
"""


def _script_player_stats(namespace: str, *, health: int = 3) -> str:
    return f"""using System;

namespace {namespace};

/// <summary>Pure logic for health/score — unit-testable without Godot runtime.</summary>
public sealed class PlayerStats
{{
    public int Health {{ get; private set; }}
    public int Score {{ get; private set; }}
    public bool IsAlive => Health > 0;

    public PlayerStats(int health = {health}, int score = 0)
    {{
        if (health < 0)
            throw new ArgumentOutOfRangeException(nameof(health));
        Health = health;
        Score = Math.Max(0, score);
    }}

    public void TakeDamage(int amount)
    {{
        if (amount < 0)
            throw new ArgumentOutOfRangeException(nameof(amount));
        Health = Math.Max(0, Health - amount);
    }}

    public void Heal(int amount)
    {{
        if (amount < 0)
            throw new ArgumentOutOfRangeException(nameof(amount));
        Health += amount;
    }}

    public void AddScore(int points)
    {{
        if (points < 0)
            throw new ArgumentOutOfRangeException(nameof(points));
        Score += points;
    }}
}}
"""


def _script_camera_follow(namespace: str) -> str:
    return f"""using Godot;

namespace {namespace};

/// <summary>Camera follow — attach to Camera2D; scaffold stub.</summary>
public partial class CameraFollow : Camera2D
{{
    [Export] public NodePath TargetPath {{ get; set; }} = new("../..");

    public override void _Process(double delta)
    {{
        if (TargetPath.IsEmpty)
            return;
        var target = GetNodeOrNull<Node2D>(TargetPath);
        if (target != null)
            GlobalPosition = target.GlobalPosition;
    }}
}}
"""


def _script_collectible(namespace: str) -> str:
    return f"""using Godot;

namespace {namespace};

/// <summary>Pickup collectible — scaffold Area2D stub.</summary>
public partial class Collectible : Area2D
{{
    public override void _Ready()
    {{
        BodyEntered += OnBodyEntered;
    }}

    private void OnBodyEntered(Node2D body)
    {{
        if (body is CharacterBody2D)
        {{
            GameState.Instance.Score += 1;
            QueueFree();
        }}
    }}
}}
"""


def write_script_stubs(project_path: Path, doc: dict[str, Any]) -> list[str]:
    scripts_dir = project_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    namespace = _safe_namespace(str(doc.get("slug") or "game"))
    player = doc.get("player") if isinstance(doc.get("player"), dict) else {}
    world = doc.get("world") if isinstance(doc.get("world"), dict) else {}
    controls = {e.get("action") for e in (doc.get("input_map") or []) if isinstance(e, dict)}
    has_jump = "jump" in controls
    has_vertical_move = "move_up" in controls or "move_down" in controls

    written: list[str] = []

    main_path = scripts_dir / "Main.cs"
    main_path.write_text(_script_main(namespace), encoding="utf-8")
    written.append(str(main_path.relative_to(project_path)))

    player_asset = str(player.get("asset") or "player")
    class_name = f"{_pascal_case(player_asset)}Controller"
    player_path = scripts_dir / f"{class_name}.cs"
    player_path.write_text(
        _script_player_controller(
            namespace,
            class_name,
            move_speed=float(player.get("move_speed", 180)),
            jump_velocity=float(player.get("jump_velocity", -420)),
            gravity=float(world.get("gravity", 980)),
            has_jump=has_jump,
            has_vertical_move=has_vertical_move,
        ),
        encoding="utf-8",
    )
    written.append(str(player_path.relative_to(project_path)))

    stubs = {
        "PlayerStats.cs": _script_player_stats(namespace, health=int(player.get("health", 3))),
        "GameState.cs": _script_game_state(namespace, health=int(player.get("health", 3))),
        "CameraFollow.cs": _script_camera_follow(namespace),
        "Collectible.cs": _script_collectible(namespace),
    }
    system_ids = {s.get("id") for s in (doc.get("systems") or []) if isinstance(s, dict)}
    for filename, content in stubs.items():
        if filename in {"PlayerStats.cs", "GameState.cs"}:
            (scripts_dir / filename).write_text(content, encoding="utf-8")
            written.append(f"scripts/{filename}")
        elif filename == "CameraFollow.cs" and "camera_follow" in system_ids:
            (scripts_dir / filename).write_text(content, encoding="utf-8")
            written.append(f"scripts/{filename}")
        elif filename == "Collectible.cs" and "collectibles" in system_ids:
            (scripts_dir / filename).write_text(content, encoding="utf-8")
            written.append(f"scripts/{filename}")

    return written


def scaffold_from_production(
    production_path: Path,
    *,
    project_path: Path | None = None,
    template: str = "dotnet",
) -> dict[str, Any]:
    """Build compilable Godot shell from production.json."""
    production_path = production_path.resolve()
    data = load_production(production_path)
    errors = validate_production(data)
    if errors:
        raise GodotScaffoldError("Invalid production:\n" + "\n".join(f"  - {e}" for e in errors))

    doc = data["production_doc"]
    meta = data.get("production_meta") or {}
    title = str(doc.get("title") or "Game")
    out_path = (project_path or default_project_path(data)).resolve()

    init_project_from_template(out_path, project_name=title, template=template)

    scenes = doc.get("scenes") or []
    player_scene = next((s for s in scenes if isinstance(s, dict) and s.get("role") == "player"), None)
    main_scene = next((s for s in scenes if isinstance(s, dict) and s.get("role") == "main"), None)
    player_rel = str((player_scene or {}).get("path") or "scenes/player.tscn")

    if player_scene:
        player_script = str(player_scene.get("script") or "scripts/Player.cs")
        _write_player_scene(
            out_path,
            player_scene,
            player_script=player_script,
            namespace=_safe_namespace(str(doc.get("slug") or "game")),
        )
    if main_scene:
        _write_main_scene(
            out_path,
            main_scene,
            player_scene_rel=player_rel,
            viewport=doc.get("viewport") or {},
        )

    write_project_godot(out_path, doc)
    scripts = write_script_stubs(out_path, doc)

    from unit_test import ensure_unit_test_project

    player = doc.get("player") if isinstance(doc.get("player"), dict) else {}
    test_csproj = ensure_unit_test_project(
        out_path,
        health=int(player.get("health", 3)),
    )

    return {
        "ok": True,
        "project_path": str(out_path),
        "production_path": str(production_path),
        "brief_path": meta.get("brief_path"),
        "main_scene": (doc.get("scaffold") or {}).get("main_scene"),
        "scripts_written": scripts,
        "unit_test_project": str(test_csproj.relative_to(out_path)),
    }
