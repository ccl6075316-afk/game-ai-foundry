shader_type spatial;
render_mode unshaded, cull_disabled;

// Real 3D undulating liquid water surface (displaced vertices + smooth analytic wave normals):
// Shows physical 3D waves, shimmering silver-aqua liquid underside reflection,
// front-glass liquid meniscus, and smooth far-edge dissolution into upper ocean haze.
uniform float clock = 0.0;
uniform vec3 sky_glow_color : source_color = vec3(0.76, 0.90, 0.92);
uniform vec3 mirror_shallow_color : source_color = vec3(0.22, 0.52, 0.64);
uniform vec3 mirror_deep_color : source_color = vec3(0.06, 0.20, 0.32);
uniform vec3 wall_blend_color : source_color = vec3(0.09, 0.30, 0.42);
uniform float brightness = 0.88;
uniform float wave_amp = 0.095;
uniform vec2 half_xz = vec2(7.5, 4.0);

varying vec3 local_pos;
varying vec3 world_pos;

// Shared 6-direction smooth trochoidal wave field (used in vertex displacement & fragment normals)
vec3 trochoidal_surface(vec2 p, float t) {
	float h = 0.0;
	vec2 grad = vec2(0.0);
	float amp = 0.30;
	float freq = 1.05;
	float speed = 1.05;
	vec2 pos = p;

	vec2 dirs[6];
	dirs[0] = vec2(0.94, 0.34);
	dirs[1] = vec2(-0.28, 0.96);
	dirs[2] = vec2(-0.88, -0.47);
	dirs[3] = vec2(0.56, -0.83);
	dirs[4] = vec2(0.76, 0.65);
	dirs[5] = vec2(-0.62, 0.78);

	for (int i = 0; i < 6; i++) {
		vec2 d = dirs[i];
		float phase = dot(pos, d) * freq + t * speed + float(i) * 1.73;
		float s = sin(phase);
		float c = cos(phase);
		float w = exp(s - 1.0);
		float dw = w * c;
		h += w * amp;
		grad += d * (dw * freq * amp);
		pos -= d * (dw * amp * 0.32);
		amp *= 0.62;
		freq *= 1.42;
		speed *= 1.15;
	}
	return vec3(h, grad.x, grad.y);
}

void vertex() {
	vec3 surf = trochoidal_surface(VERTEX.xz, clock);
	float disp = (surf.x - 0.34) * wave_amp * 2.2;
	VERTEX.y += disp;
	local_pos = VERTEX;
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float fixture_glow(vec2 xz) {
	vec2 nxz = xz / max(half_xz, vec2(0.5));
	vec2 c0 = vec2(-0.48, 0.10);
	vec2 c1 = vec2(0.0, 0.04);
	vec2 c2 = vec2(0.48, 0.10);
	float p0 = exp(-dot((nxz - c0) * vec2(2.4, 1.8), (nxz - c0) * vec2(2.4, 1.8)));
	float p1 = exp(-dot((nxz - c1) * vec2(2.1, 1.6), (nxz - c1) * vec2(2.1, 1.6)));
	float p2 = exp(-dot((nxz - c2) * vec2(2.4, 1.8), (nxz - c2) * vec2(2.4, 1.8)));
	return clamp(0.18 + p0 * 0.64 + p1 * 0.88 + p2 * 0.64, 0.0, 1.18);
}

void fragment() {
	vec2 p = local_pos.xz;
	vec3 surf = trochoidal_surface(p, clock);
	float h0 = clamp(surf.x * 1.25, 0.0, 1.0);

	// Downward-facing rippling liquid underside normal
	vec3 n = normalize(vec3(-surf.y * 0.72, -1.0, -surf.z * 0.72));
	vec3 view_dir = normalize(CAMERA_POSITION_WORLD - world_pos);

	float cos_v = clamp(dot(n, view_dir), 0.0, 1.0);
	float snell_window = smoothstep(0.45, 0.84, cos_v);

	vec3 light_dir = normalize(vec3(0.20, -1.0, 0.14));
	vec3 half_vec = normalize(view_dir - light_dir);
	float spec_soft = pow(clamp(abs(dot(n, half_vec)), 0.0, 1.0), 12.0);
	float silver_wave = smoothstep(0.30, 0.88, h0);
	float pools = fixture_glow(p);

	// Total internal reflection mirrors luminous blue-silver underwater light + soft crest shimmer
	vec3 tir_col = mix(mirror_deep_color, mirror_shallow_color, h0 * 0.68 + 0.25) * (0.64 + 0.48 * pools);
	tir_col += sky_glow_color * (spec_soft * 0.30 * pools + silver_wave * 0.18 * pools);

	// Bright shimmering front-glass liquid meniscus line where wave meets the acrylic viewing pane
	float front_meniscus = smoothstep(half_xz.y - 0.24, half_xz.y - 0.01, p.y);
	vec3 meniscus_glow = mix(mirror_shallow_color * 1.35, sky_glow_color * 1.22, 0.55 + 0.45 * silver_wave);

	vec3 snell_col = mix(mirror_shallow_color * 1.12, sky_glow_color * 0.96, clamp(pools * 0.78, 0.0, 1.0));
	snell_col += vec3(0.18, 0.24, 0.24) * (spec_soft * 0.48 + silver_wave * 0.16) * pools;

	vec3 water_col = mix(tir_col, snell_col, snell_window) * brightness;
	water_col = mix(water_col, meniscus_glow, front_meniscus * 0.82);

	// Smooth far-back & side edge dissolution into upper ocean haze
	float back_blend = smoothstep(-half_xz.y + 2.2, -half_xz.y + 0.05, p.y);
	float side_blend = smoothstep(half_xz.x - 2.6, half_xz.x - 0.05, abs(p.x));
	float edge_dissolve = clamp(max(back_blend, side_blend), 0.0, 1.0);
	vec3 col = mix(water_col, wall_blend_color, edge_dissolve * 0.90);

	ALBEDO = col;
}
