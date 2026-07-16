"""L1 unit-test harness — discover/scaffold/run `dotnet test` for Godot C# projects."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from toolchain_paths import resolve_dotnet, toolchain_env

_REPO_ROOT = Path(__file__).resolve().parent.parent


class UnitTestError(RuntimeError):
    pass


def find_test_projects(project_path: Path) -> list[Path]:
    """Locate *Tests.csproj under project/tests or project root."""
    project_path = project_path.resolve()
    found: list[Path] = []
    tests_dir = project_path / "tests"
    if tests_dir.is_dir():
        found.extend(sorted(tests_dir.glob("*Tests.csproj")))
        found.extend(sorted(tests_dir.glob("*.Tests.csproj")))
    found.extend(sorted(project_path.glob("*Tests.csproj")))
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p.resolve())
    return out


def _assembly_name(project_path: Path) -> str:
    godot = project_path / "project.godot"
    if godot.is_file():
        text = godot.read_text(encoding="utf-8")
        m = re.search(r'project/assembly_name\s*=\s*"([^"]+)"', text)
        if m:
            return m.group(1)
    csprojs = list(project_path.glob("*.csproj"))
    if csprojs:
        return csprojs[0].stem
    return project_path.name.replace("-", "").replace("_", "")


def _namespace(project_path: Path) -> str:
    name = _assembly_name(project_path)
    parts = re.split(r"[^A-Za-z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Game"


def ensure_player_stats(project_path: Path, *, health: int = 3) -> Path:
    """Write pure-C# PlayerStats (no Godot) used by unit tests and GameState."""
    scripts = project_path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    ns = _namespace(project_path)
    path = scripts / "PlayerStats.cs"
    path.write_text(
        f"""using System;

namespace {ns};

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
""",
        encoding="utf-8",
    )
    return path


def exclude_tests_from_game_csproj(project_path: Path) -> None:
    """Godot.NET.Sdk globs all .cs under the project — keep tests/ out of the game assembly."""
    for csproj in project_path.glob("*.csproj"):
        if csproj.parent != project_path:
            continue
        text = csproj.read_text(encoding="utf-8")
        if "tests/**" in text or "tests\\**" in text:
            return
        if "</PropertyGroup>" not in text:
            return
        text = text.replace(
            "</PropertyGroup>",
            "    <DefaultItemExcludes>$(DefaultItemExcludes);tests\\**;tests/**</DefaultItemExcludes>\n  </PropertyGroup>",
            1,
        )
        csproj.write_text(text, encoding="utf-8")
        return


def ensure_unit_test_project(
    project_path: Path,
    *,
    health: int = 3,
) -> Path:
    """Create tests/<Assembly>.Tests.csproj + smoke tests if missing."""
    project_path = project_path.resolve()
    existing = find_test_projects(project_path)
    if existing:
        return existing[0]

    ensure_player_stats(project_path, health=health)
    exclude_tests_from_game_csproj(project_path)
    assembly = _assembly_name(project_path)
    ns = _namespace(project_path)
    tests_dir = project_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    csproj = tests_dir / f"{assembly}.Tests.csproj"
    csproj.write_text(
        f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
    <RootNamespace>{ns}.Tests</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
  </ItemGroup>
  <ItemGroup>
    <Compile Include="../scripts/PlayerStats.cs" Link="PlayerStats.cs" />
  </ItemGroup>
</Project>
""",
        encoding="utf-8",
    )
    (tests_dir / "PlayerStatsTests.cs").write_text(
        f"""using {ns};
using Xunit;

namespace {ns}.Tests;

public class PlayerStatsTests
{{
    [Fact]
    public void New_stats_are_alive_with_default_health()
    {{
        var stats = new PlayerStats({health});
        Assert.True(stats.IsAlive);
        Assert.Equal({health}, stats.Health);
        Assert.Equal(0, stats.Score);
    }}

    [Fact]
    public void TakeDamage_reduces_health_and_can_kill()
    {{
        var stats = new PlayerStats({health});
        stats.TakeDamage({health});
        Assert.Equal(0, stats.Health);
        Assert.False(stats.IsAlive);
    }}

    [Fact]
    public void AddScore_increases_score()
    {{
        var stats = new PlayerStats({health});
        stats.AddScore(10);
        Assert.Equal(10, stats.Score);
    }}
}}
""",
        encoding="utf-8",
    )
    return csproj


def run_unit_tests(
    project_path: Path,
    *,
    config: dict[str, Any] | None = None,
    scaffold_if_missing: bool = True,
    health: int = 3,
    timeout: int = 300,
) -> dict[str, Any]:
    """Run `dotnet test` on project unit tests. Returns structured report."""
    project_path = project_path.resolve()
    config = config or {}
    env = toolchain_env(config)
    dotnet = resolve_dotnet(config) or "dotnet"

    projects = find_test_projects(project_path)
    if not projects and scaffold_if_missing:
        projects = [ensure_unit_test_project(project_path, health=health)]
    if not projects:
        raise UnitTestError(
            "No *Tests.csproj found. Re-run with scaffold, or add tests/ under the Godot project."
        )

    results: list[dict[str, Any]] = []
    ok = True
    for csproj in projects:
        cmd = [dotnet, "test", str(csproj), "--nologo", "-v", "q"]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            cwd=str(project_path),
        )
        entry = {
            "project": str(csproj),
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
        }
        results.append(entry)
        if proc.returncode != 0:
            ok = False

    return {
        "ok": ok,
        "layer": "unit",
        "project_path": str(project_path),
        "dotnet": dotnet,
        "results": results,
    }


def write_unit_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path.resolve()


def default_unit_report_path(project_path: Path) -> Path:
    return _REPO_ROOT / "output" / project_path.name / "validation" / "unit-report.json"
