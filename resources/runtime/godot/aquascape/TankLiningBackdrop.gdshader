shader_type spatial;
render_mode unshaded, cull_disabled;

// Seamless deep-ocean inner tank lining so back/side walls dissolve into open water
// instead of showing flat-grey rectangular box corners, with a dark humid dry-air band above waterline.
uniform vec3 upper_color : source_color = vec3(0.08, 0.34, 0.50);
uniform vec3 mid_color : source_color = vec3(0.03, 0.16, 0.30);
uniform vec3 lower_color : source_color = vec3(0.012, 0.06, 0.14);
uniform float tank_height = 5.1;
uniform float waterline = 4.38;
uniform vec2 half_xz = vec2(7.5, 4.0);
uniform vec3 tank_origin_world = vec3(0.0, 0.0, -2.45);
uniform float clock = 0.0;

varying vec3 tank_local;

void vertex() {
	tank_local = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz - tank_origin_world;
}

void fragment() {
	float h = clamp(tank_local.y / max(tank_height, 0.1), 0.0, 1.0);
	vec3 grad = mix(lower_color, mid_color, smoothstep(0.0, 0.52, h));
	grad = mix(grad, upper_color, smoothstep(0.45, 1.0, h));

	float rx = abs(tank_local.x) / max(half_xz.x, 0.1);
	float rz = clamp((half_xz.y - tank_local.z) / max(half_xz.y * 2.0, 0.1), 0.0, 1.0);
	float corner_soft = 1.0 - 0.32 * pow(clamp(rx, 0.0, 1.0), 2.2) - 0.12 * (1.0 - rz);

	float top_band = smoothstep(0.58, 0.86, h) * (1.0 - smoothstep(0.86, 0.90, h));
	float shimmer = 0.5 + 0.5 * sin(tank_local.x * 1.15 + tank_local.z * 0.9 + clock * 0.48);
	grad += upper_color * top_band * shimmer * 0.14;

	float above_water = smoothstep(waterline - 0.02, waterline + 0.10, tank_local.y);
	vec3 dry_upper = vec3(0.015, 0.025, 0.036);
	ALBEDO = mix(grad * clamp(corner_soft, 0.45, 1.05), dry_upper, above_water);
}
