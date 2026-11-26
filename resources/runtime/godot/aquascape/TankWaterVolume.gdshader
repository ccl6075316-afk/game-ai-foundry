shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_test_disabled, depth_draw_never;
#include "res://scripts/aquarium/passage/PassageDryVolume.gdshaderinc"

// Stratified seawater spectral absorption, volumetric crepuscular light shafts,
// normal-aware benthic Voronoi caustics, elliptic/box shell clipping, and
// optional undulating 3D wave top meniscus. Shared by up to 8 tanks.

uniform sampler2D scene_color : hint_screen_texture, repeat_disable, filter_nearest;
uniform sampler2D scene_depth : hint_depth_texture, repeat_disable, filter_nearest;
uniform int water_count = 0;
uniform vec4 water_x[8];
uniform vec4 water_y[8];
uniform vec4 water_z[8];
uniform vec4 water_color[8];
uniform vec4 water_optics[8];
uniform vec4 water_extra[8];
uniform vec4 water_deep[8];
uniform vec4 water_shaft[8];
uniform vec4 water_extinction[8];
uniform vec4 water_caustic_tint[8];
uniform vec4 water_light_tilt[8];
uniform float clock = 0.0;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

vec3 unproject(vec2 uv, float depth, mat4 inverse_projection, mat4 inverse_view) {
	vec3 ndc;
	#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
		ndc = vec3(uv, depth) * 2.0 - 1.0;
	#else
		ndc = vec3(uv * 2.0 - 1.0, depth);
	#endif
	vec4 p = inverse_projection * vec4(ndc, 1.0);
	return (inverse_view * vec4(p.xyz / p.w, 1.0)).xyz;
}

vec3 local_point(vec3 p, int i) {
	return vec3(dot(water_x[i], vec4(p, 1.0)), dot(water_y[i], vec4(p, 1.0)), dot(water_z[i], vec4(p, 1.0)));
}

vec3 local_direction(vec3 d, int i) {
	return vec3(dot(water_x[i].xyz, d), dot(water_y[i].xyz, d), dot(water_z[i].xyz, d));
}

float front_wave_height(vec2 xz_m, float t, float wave_amp) {
	float h = 0.0;
	h += exp(sin(dot(xz_m, vec2(0.94, 0.34)) * 1.05 + t * 1.05) - 1.0) * 0.30;
	h += exp(sin(dot(xz_m, vec2(-0.28, 0.96)) * 1.49 + t * 1.21 + 1.73) - 1.0) * 0.186;
	h += exp(sin(dot(xz_m, vec2(-0.88, -0.47)) * 2.12 + t * 1.39 + 3.46) - 1.0) * 0.115;
	return (h - 0.30) * wave_amp * 2.2;
}

bool inside_water(vec3 p, float top_local, float shape_kind, float margin) {
	if (p.x < -3.0 - margin || p.x > 3.0 + margin || p.y < -margin || p.y > top_local + margin || p.z < -1.5 - margin || p.z > 1.5 + margin) {
		return false;
	}
	if (shape_kind > 0.5) {
		vec2 pe = vec2(p.x / 3.0, p.z / 1.5);
		return dot(pe, pe) <= 1.0 + margin * 0.35;
	}
	return true;
}

vec2 ray_box(vec3 p, vec3 d, float distance_to_hit, float top_local) {
	vec3 safe_d = mix(vec3(-1e-6), vec3(1e-6), greaterThanEqual(d, vec3(0.0)));
	safe_d = mix(d, safe_d, lessThan(abs(d), vec3(1e-6)));
	vec3 a = (vec3(-3.0, 0.0, -1.5) - p) / safe_d;
	vec3 b = (vec3(3.0, top_local, 1.5) - p) / safe_d;
	vec3 mn = min(a, b);
	vec3 mx = max(a, b);
	return vec2(max(0.0, max(mn.x, max(mn.y, mn.z))), min(distance_to_hit, min(mx.x, min(mx.y, mx.z))));
}

vec2 clip_ellipse(vec3 p, vec3 d, vec2 seg) {
	vec2 pe = vec2(p.x / 3.0, p.z / 1.5);
	vec2 de = vec2(d.x / 3.0, d.z / 1.5);
	float a = dot(de, de);
	float b = dot(pe, de);
	float c = dot(pe, pe) - 1.0;
	if (a < 1e-7) {
		return c <= 0.0 ? seg : vec2(1.0, -1.0);
	}
	float disc = b * b - a * c;
	if (disc < 0.0) {
		return vec2(1.0, -1.0);
	}
	float r = sqrt(disc);
	return vec2(max(seg.x, (-b - r) / a), min(seg.y, (-b + r) / a));
}

vec2 hash22(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453);
}

float voronoi_web(vec2 p, float t) {
	vec2 n = floor(p);
	vec2 f = fract(p);
	float d1 = 8.0;
	float d2 = 8.0;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 g = vec2(float(i), float(j));
			vec2 o = hash22(n + g);
			o = 0.5 + 0.42 * sin(t + 6.28318 * o);
			vec2 r = g + o - f;
			float d = dot(r, r);
			if (d < d1) {
				d2 = d1;
				d1 = d;
			} else if (d < d2) {
				d2 = d;
			}
		}
	}
	float edge = sqrt(d2) - sqrt(d1);
	return pow(clamp(1.0 - smoothstep(0.0, 0.34, edge), 0.0, 1.0), 1.55);
}

float dual_caustic(vec2 xz, float scale, float t) {
	vec2 p1 = xz * scale + vec2(t * 0.14, -t * 0.09);
	mat2 rot = mat2(vec2(0.80, -0.60), vec2(0.60, 0.80));
	vec2 p2 = (rot * xz) * (scale * 1.48) + vec2(-t * 0.11, t * 0.16);
	float c1 = voronoi_web(p1, t * 1.05);
	float c2 = voronoi_web(p2, t * 1.35 + 1.7);
	return clamp(c1 * 0.65 + c2 * 0.52 + c1 * c2 * 0.48, 0.0, 1.45);
}

float surface_light_pools(vec2 xz_m, vec2 half_xz_m) {
	vec2 nxz = xz_m / max(half_xz_m, vec2(0.5));
	vec2 c0 = vec2(-0.48, 0.10);
	vec2 c1 = vec2(0.0, 0.04);
	vec2 c2 = vec2(0.48, 0.10);
	float p0 = exp(-dot((nxz - c0) * vec2(2.55, 1.84), (nxz - c0) * vec2(2.55, 1.84)));
	float p1 = exp(-dot((nxz - c1) * vec2(2.10, 1.60), (nxz - c1) * vec2(2.10, 1.60)));
	float p2 = exp(-dot((nxz - c2) * vec2(2.55, 1.84), (nxz - c2) * vec2(2.55, 1.84)));
	return clamp(0.14 + p0 * 0.74 + p1 * 1.02 + p2 * 0.74, 0.0, 1.28);
}

float shaft_pattern(vec2 surf_xz_m, vec2 half_xz_m, float depth_below, float t) {
	float x_warp = surf_xz_m.x + sin(surf_xz_m.y * 0.65 + t * 0.28) * 0.45;
	float b1 = sin(x_warp * 1.55 + surf_xz_m.y * 0.35 + t * 0.38) * 0.5 + 0.5;
	float b2 = sin(x_warp * 2.85 - surf_xz_m.y * 0.70 - t * 0.32 + 1.4) * 0.5 + 0.5;
	float b3 = sin(x_warp * 0.92 + surf_xz_m.y * 0.48 + t * 0.22 + 2.6) * 0.5 + 0.5;
	float broad = pow(clamp(b1 * 0.52 + b2 * 0.33 + b3 * 0.25, 0.0, 1.0), 2.25);

	float s1 = sin(x_warp * 5.2 + surf_xz_m.y * 1.4 + t * 0.72) * 0.5 + 0.5;
	float s2 = sin(x_warp * 7.8 - surf_xz_m.y * 2.1 - t * 0.58) * 0.5 + 0.5;
	float streaks = pow(s1 * s2, 1.65) * exp(-depth_below * 0.52);

	return (broad * 0.85 + streaks * 0.90) * surface_light_pools(surf_xz_m, half_xz_m);
}

void fragment() {
	float raw_depth = texture(scene_depth, SCREEN_UV).r;
	vec3 hit = unproject(SCREEN_UV, raw_depth, INV_PROJECTION_MATRIX, INV_VIEW_MATRIX);
	vec3 near_point = unproject(SCREEN_UV, 1.0, INV_PROJECTION_MATRIX, INV_VIEW_MATRIX);
	vec3 far_point = unproject(SCREEN_UV, 0.00001, INV_PROJECTION_MATRIX, INV_VIEW_MATRIX);
	vec3 direction = normalize(far_point - near_point);
	vec3 origin = near_point;
	float distance_to_hit = max(0.0, dot(hit - origin, direction));

	// Compute screen-space world derivatives unconditionally before control flow for GLSL ES / Metal safety
	vec3 hit_dx = dFdx(hit);
	vec3 hit_dy = dFdy(hit);
	vec3 cross_n = cross(hit_dx, hit_dy);
	float clen = length(cross_n);
	vec3 hit_n_world = clen > 1e-6 ? (cross_n / clen) : vec3(0.0, 1.0, 0.0);
	if (dot(hit_n_world, -direction) < 0.0) {
		hit_n_world = -hit_n_world;
	}
	float deriv_guard = 1.0 - smoothstep(0.18, 0.50, max(length(hit_dx), length(hit_dy)));
	float up_mask = smoothstep(0.24, 0.78, hit_n_world.y) * deriv_guard;

	vec3 color = texture(scene_color, SCREEN_UV).rgb;
	vec3 total_trans = vec3(1.0);
	vec3 total_scatter = vec3(0.0);
	float meniscus_blend = 0.0;
	vec3 meniscus_target = vec3(0.0);
	bool covered = false;

	float ign = fract(52.9829189 * fract(dot(FRAGCOORD.xy, vec2(0.06711056, 0.00583715))));

	for (int i = 0; i < 8; i++) {
		if (i >= water_count) {
			break;
		}
		vec3 p = local_point(origin, i);
		vec3 d = local_direction(direction, i);

		float scale_x = 1.0 / max(length(water_x[i].xyz), 0.0001);
		float scale_y = 1.0 / max(length(water_y[i].xyz), 0.0001);
		float scale_z = 1.0 / max(length(water_z[i].xyz), 0.0001);
		vec3 half_m = vec3(3.0 * scale_x, 2.775 * scale_y, 1.5 * scale_z);

		float shape_kind = water_extra[i].y;
		float wave_amp_m = water_extra[i].z;
		float dynamic_top_local = 2.775;
		float dynamic_top_m = half_m.y;

		if (wave_amp_m > 0.001) {
			float top_pad_local = (wave_amp_m * 2.0) / max(scale_y, 0.001);
			vec2 rough_seg = ray_box(p, d, distance_to_hit, 2.775 + top_pad_local);
			vec3 approx_entry = p + d * rough_seg.x;
			vec2 approx_xz_m = vec2(approx_entry.x * scale_x, approx_entry.z * scale_z);
			float wave_dy_m = front_wave_height(approx_xz_m, clock, wave_amp_m);
			dynamic_top_local = 2.775 + wave_dy_m / max(scale_y, 0.001);
			dynamic_top_m = half_m.y + wave_dy_m;
		}

		vec2 segment = ray_box(p, d, distance_to_hit, dynamic_top_local);
		if (shape_kind > 0.5 && segment.y > segment.x) {
			segment = clip_ellipse(p, d, segment);
		}
		float wet_len = passage_wet_length(origin, direction, segment);
		if (wet_len < 0.0005) {
			continue;
		}
		covered = true;

		vec4 optics = water_optics[i];
		vec4 tint = water_color[i];
		vec3 shallow_scatter = tint.rgb;
		float scatter_strength = max(tint.a, 0.0);
		float visibility_m = max(optics.x, 0.5);
		float caustic_strength = max(optics.w, 0.0);
		float shaft_strength = water_extra[i].w > 0.0001 ? water_extra[i].w : clamp(optics.y * 2.8 + 0.14, 0.0, 0.58);

		vec3 deep_scatter = water_deep[i].a > 0.0001 ? water_deep[i].rgb : shallow_scatter * vec3(0.20, 0.34, 0.45);
		float vertical_decay = water_deep[i].a > 0.0001 ? water_deep[i].a : 0.24;
		vec3 shaft_color = water_shaft[i].a > 0.0001 ? water_shaft[i].rgb : mix(shallow_scatter, vec3(0.92, 0.96, 0.96), 0.72);
		float caustic_scale = water_shaft[i].a > 0.0001 ? water_shaft[i].a : 0.72;
		vec3 extinction_rgb = (water_extinction[i].x + water_extinction[i].y + water_extinction[i].z) > 0.01
			? water_extinction[i].rgb
			: mix(vec3(1.85, 0.85, 1.15), vec3(2.95, 1.02, 0.52), clamp((shallow_scatter.b - shallow_scatter.r) * 1.6 + 0.5, 0.0, 1.0));
		float meniscus_strength = water_extinction[i].a;
		vec3 caustic_color = water_caustic_tint[i].a > 0.0001 ? water_caustic_tint[i].rgb : mix(shallow_scatter, vec3(0.96, 0.98, 0.96), 0.82);
		float shaft_decay = water_caustic_tint[i].a > 0.0001 ? water_caustic_tint[i].a : 0.28;
		vec3 light_tilt = water_light_tilt[i].w > 0.0001 ? water_light_tilt[i].xyz : vec3(0.24, 1.0, 0.14);

		vec3 hit_local = local_point(hit, i);
		vec3 hit_m = vec3(hit_local.x * scale_x, hit_local.y * scale_y, hit_local.z * scale_z);
		bool hit_inside = inside_water(hit_local, dynamic_top_local, shape_kind, 0.06) && !passage_contains(hit);

		// 1) Normal-aware benthic Voronoi caustics on horizontal/sloped surfaces (zero vertical wall stripes)
		if (hit_inside && caustic_strength > 0.001 && hit_m.y < dynamic_top_m - 0.08) {
			float below_surface = smoothstep(0.08, 0.42, dynamic_top_m - hit_m.y);
			if (up_mask * below_surface > 0.005) {
				float depth_below = max(0.0, dynamic_top_m - hit_m.y);
				vec2 proj_xz = hit_m.xz + (light_tilt.xz / max(light_tilt.y, 0.25)) * depth_below;
				float disp = 0.020 * exp(-depth_below * 0.22);
				float c_r = dual_caustic(proj_xz + vec2(disp, 0.0), caustic_scale, clock);
				float c_g = dual_caustic(proj_xz, caustic_scale, clock);
				float c_b = dual_caustic(proj_xz - vec2(disp, 0.0), caustic_scale, clock);
				vec3 c_rgb = vec3(c_r, c_g, c_b) * caustic_color;
				float depth_fade = exp(-depth_below * 0.16);
				float pool = surface_light_pools(proj_xz, half_m.xz);
				vec2 floor_edge = abs(hit_m.xz) / max(half_m.xz, vec2(0.1));
				float edge_soft = 1.0 - 0.55 * smoothstep(0.68, 1.0, max(floor_edge.x, floor_edge.y));
				float surface_boost = mix(0.45, 1.25, clamp(dot(color, vec3(0.3, 0.55, 0.15)) * 2.2, 0.0, 1.0));
				color += c_rgb * up_mask * below_surface * depth_fade * pool * edge_soft * caustic_strength * 0.48 * surface_boost;
			}
		}

		// 2) Stratified spectral absorption + volumetric light shafts along the tank ray
		const int STEPS = 12;
		float seg_span = max(segment.y - segment.x, 0.0001);
		float dt = seg_span / float(STEPS);
		float wet_ratio = clamp(wet_len / seg_span, 0.0, 1.0);
		float sigma_t = 1.0 / visibility_m;
		vec3 step_ext = extinction_rgb * sigma_t * max(scatter_strength, 0.05);
		vec3 step_trans = exp(-step_ext * dt * wet_ratio);

		vec3 d_m_dir = normalize(vec3(d.x * scale_x, d.y * scale_y, d.z * scale_z));
		vec3 light_dir_norm = normalize(light_tilt);
		float cos_phase = dot(d_m_dir, -light_dir_norm);
		float mie_phase = 0.68 + 0.58 * pow(clamp(0.5 + 0.5 * cos_phase, 0.0, 1.0), 2.2);

		vec3 tank_trans = vec3(1.0);
		vec3 tank_scatter = vec3(0.0);

		for (int s = 0; s < STEPS; s++) {
			float t_s = segment.x + (float(s) + ign) * dt;
			if (dry_count > 0 && passage_contains(origin + direction * t_s)) {
				continue;
			}
			vec3 pos_local = p + d * t_s;
			vec3 pos_m = vec3(pos_local.x * scale_x, pos_local.y * scale_y, pos_local.z * scale_z);
			float h = clamp(pos_m.y / max(half_m.y, 0.1), 0.0, 1.0);
			float depth_below = max(0.0, half_m.y - pos_m.y);

			vec3 local_scatter = vec3(0.0);
			if (scatter_strength > 0.001) {
				float down_light = exp(-depth_below * vertical_decay);
				vec2 norm_xz = pos_m.xz / max(half_m.xz, vec2(0.1));
				float center_glow = mix(0.45, 1.08, exp(-dot(norm_xz * vec2(0.84, 0.72), norm_xz * vec2(0.84, 0.72))));
				vec3 water_col = mix(deep_scatter, shallow_scatter, pow(h, 0.70));
				float surface_halo = exp(-depth_below * 1.15) * 0.34 * surface_light_pools(pos_m.xz, half_m.xz);
				local_scatter += (water_col * down_light * center_glow + shallow_scatter * surface_halo) * scatter_strength * sigma_t * 1.15;
			}

			if (shaft_strength > 0.001) {
				vec2 surf_xz = pos_m.xz + (light_tilt.xz / max(light_tilt.y, 0.25)) * depth_below;
				float inside_top = smoothstep(half_m.x + 0.3, half_m.x - min(1.4, half_m.x * 0.35), abs(surf_xz.x))
								 * smoothstep(half_m.z + 0.2, half_m.z - min(1.0, half_m.z * 0.35), abs(surf_xz.y));
				float ray_val = shaft_pattern(surf_xz, half_m.xz, depth_below, clock) * inside_top;
				float ray_depth_fade = exp(-depth_below * shaft_decay) * smoothstep(0.06, 0.55, pos_m.y);
				float glass_clearance = smoothstep(0.15, 1.10, t_s - segment.x);
				local_scatter += shaft_color * ray_val * ray_depth_fade * glass_clearance * mie_phase * shaft_strength * 0.25;
			}

			vec3 integ = local_scatter * (vec3(1.0) - step_trans) / max(step_ext, vec3(0.0001));
			tank_scatter += tank_trans * integ;
			tank_trans *= step_trans;
		}

		total_scatter += total_trans * tank_scatter;
		total_trans *= tank_trans;

		// 3) Crisp silvery-aqua liquid meniscus highlight right along a moving front-glass waterline
		if (meniscus_strength > 0.01 && wave_amp_m > 0.001) {
			vec3 entry_local = p + d * segment.x;
			vec3 entry_m = vec3(entry_local.x * scale_x, entry_local.y * scale_y, entry_local.z * scale_z);
			if (abs(entry_m.z - half_m.z) < 0.08) {
				float dist_to_line = abs(entry_m.y - dynamic_top_m);
				float band = exp(-pow(dist_to_line / 0.042, 2.0));
				float shimmer = 0.72 + 0.28 * sin(entry_m.x * 3.8 + clock * 2.4 + sin(entry_m.x * 1.7 - clock * 1.3));
				meniscus_blend = max(meniscus_blend, band * meniscus_strength);
				meniscus_target = mix(shallow_scatter * 1.4, shaft_color * 1.15, 0.65) * shimmer;
			}
		}
	}

	// Preserve the original framebuffer outside water, including low-value room pixels.
	if (!covered) {
		discard;
	}

	vec3 final_col = color * total_trans + total_scatter;
	if (meniscus_blend > 0.001) {
		final_col = mix(final_col, meniscus_target, meniscus_blend);
	}
	ALBEDO = final_col;
	ALPHA = 1.0;
}
