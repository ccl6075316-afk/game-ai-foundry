using Godot;

namespace GameFactoryDemo;

/// <summary>Player with AnimatedSprite2D — C# only (no GDScript).</summary>
public partial class Player : CharacterBody2D
{
	private AnimatedSprite2D _sprite = null!;
	private Sprite2D? _idleStill;
	private const float Speed = 180f;

	public override void _Ready()
	{
		_sprite = GetNode<AnimatedSprite2D>("AnimatedSprite2D");
		_idleStill = GetNodeOrNull<Sprite2D>("IdleStill");
		SetMoving(false);
	}

	public override void _PhysicsProcess(double delta)
	{
		Vector2 direction = GetMoveDirection();
		Velocity = direction * Speed;
		MoveAndSlide();
		SetMoving(direction != Vector2.Zero, direction);
	}

	private void SetMoving(bool moving, Vector2 direction = default)
	{
		if (_idleStill != null)
			_idleStill.Visible = !moving;

		_sprite.Visible = moving;
		if (!moving)
		{
			_sprite.Stop();
			return;
		}

		if (_sprite.SpriteFrames != null && _sprite.SpriteFrames.HasAnimation("walk"))
			_sprite.Play("walk");

		if (direction.X != 0)
			_sprite.FlipH = direction.X < 0;
	}

	private static Vector2 GetMoveDirection()
	{
		Vector2 fromActions = Input.GetVector("ui_left", "ui_right", "ui_up", "ui_down");
		if (fromActions != Vector2.Zero)
			return fromActions.Normalized();

		float x = 0f;
		float y = 0f;
		if (Input.IsKeyPressed(Key.Right) || Input.IsKeyPressed(Key.D))
			x += 1f;
		if (Input.IsKeyPressed(Key.Left) || Input.IsKeyPressed(Key.A))
			x -= 1f;
		if (Input.IsKeyPressed(Key.Down) || Input.IsKeyPressed(Key.S))
			y += 1f;
		if (Input.IsKeyPressed(Key.Up) || Input.IsKeyPressed(Key.W))
			y -= 1f;

		Vector2 dir = new(x, y);
		return dir.LengthSquared() > 0f ? dir.Normalized() : Vector2.Zero;
	}
}
