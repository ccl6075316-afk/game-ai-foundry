using Godot;

namespace GameFactoryDemo;

/// <summary>Top-level game node — template only; extend via godot assemble.</summary>
public partial class Main : Node2D
{
    public override void _Ready()
    {
        GD.Print("GameFactory demo loaded. Use WASD or arrow keys to move.");
    }
}
