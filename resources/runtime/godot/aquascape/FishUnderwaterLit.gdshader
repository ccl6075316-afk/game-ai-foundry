shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

// Photographic underwater aquarium fish shading (matched to underwater optics: n_mucus ~= n_water = 1.33):
// - Supports both legacy single-albedo fish AND full multi-material PBR fish (Normal + ORM + 3D Eye + Fins)
// - No glassy/plastic air-water Fresnel clearcoat on skin; dedicated wet-cornea reflection only on 3D eyes
// - Soft 360-degree scattered underwater hemisphere ambient, out-of-focus dorsal caustic dapples,
//   warm coral-sand upward bounce light, per-scale pearlescent satin roll, and thin-fin translucency.

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic;
uniform bool has_albedo_tex = true;
uniform vec4 albedo_tint : source_color = vec4(1.0);
uniform bool use_vertex_color = false;
uniform bool is_fin = false;
uniform bool is_eye = false;
uniform float alpha_scissor = 0.5;

// Optional PBR channels (auto-bound by FishUnderwaterOptics when present on source material)
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic;
uniform bool has_normal_tex = false;
uniform float normal_depth = 1.0;

uniform sampler2D orm_tex : hint_default_white, filter_linear_mipmap_anisotropic;
uniform bool has_orm_tex = false;
uniform bool has_ao_tex = false;

// Species optical fallbacks (used when ORM texture is absent, or blended subtly with ORM)
uniform float wet_roughness = 0.84;
uniform float wet_specular = 0.10;
uniform float scale_metallic = 0.0;
uniform float scale_sheen = 0.04;
uniform float fin_translucency = 0.25;

// Tank lighting & water environment sync
uniform vec3 tank_origin_world = vec3(0.0, 0.0, -2.45);
uniform vec2 tank_half_xz = vec2(7.5, 4.0);
uniform float waterline = 4.38;
uniform float sand_y = 0.10;
uniform float clock = 0.0;
uniform vec3 light_tilt = vec3(0.24, 1.0, 0.14);
uniform vec3 top_water_light : source_color = vec3(0.76, 0.90, 0.92);
uniform vec3 side_water_ambient : source_color = vec3(0.16, 0.36, 0.48);
uniform vec3 sand_bounce_color : source_color = vec3(0.76, 0.78, 0.70);
uniform vec3 caustic_color : source_color = vec3(0.88, 0.96, 0.94);
uniform float caustic_strength = 0.55;
uniform float reflection_strength = 1.0;

varying vec3 v_world_pos;
varying vec3 v_world_normal;
varying vec3 v_world_tangent;
varying vec3 v_world_binormal;

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_world_tangent = normalize((MODEL_MATRIX * vec4(TANGENT, 0.0)).xyz);
	v_world_binormal = normalize((MODEL_MATRIX * vec4(BINORMAL, 0.0)).xyz);
}

vec2 hash22(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453);
}

float soft_caustic_cell(vec2 p, float t) {
	vec2 n = floor(p);
	vec2 f = fract(p);
	float d1 = 8.0;
	float d2 = 8.0;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 g = vec2(float(i), float(j));
			vec2 o = hash22(n + g);
			o = 0.5 + 0.40 * sin(t + 6.28318 * o);
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
	return pow(clamp(1.0 - smoothstep(0.0, 0.46, edge), 0.0, 1.0), 1.35);
}

float soft_fish_caustics(vec2 xz, float t) {
	vec2 p1 = xz * 1.45 + vec2(t * 0.20, -t * 0.14);
	mat2 rot = mat2(vec2(0.80, -0.60), vec2(0.60, 0.80));
	vec2 p2 = (rot * xz) * 2.25 + vec2(-t * 0.16, t * 0.21);
	float c1 = soft_caustic_cell(p1, t * 1.05);
	float c2 = soft_caustic_cell(p2, t * 1.35 + 1.9);
	return clamp(c1 * 0.62 + c2 * 0.48, 0.0, 1.25);
}

float overhead_pools(vec2 xz) {
	vec2 nxz = xz / max(tank_half_xz, vec2(0.5));
	vec2 c0 = vec2(-0.48, 0.10);
	vec2 c1 = vec2(0.0, 0.04);
	vec2 c2 = vec2(0.48, 0.10);
	float p0 = exp(-dot((nxz - c0) * vec2(2.25, 1.44), (nxz - c0) * vec2(2.25, 1.44)));
	float p1 = exp(-dot((nxz - c1) * vec2(1.95, 1.36), (nxz - c1) * vec2(1.95, 1.36)));
	float p2 = exp(-dot((nxz - c2) * vec2(2.25, 1.44), (nxz - c2) * vec2(2.25, 1.44)));
	return clamp(0.32 + p0 * 0.68 + p1 * 0.92 + p2 * 0.68, 0.0, 1.25);
}

void fragment() {
	vec4 tex = has_albedo_tex ? texture(albedo_tex, UV) : vec4(1.0);
	vec3 base_albedo = tex.rgb * albedo_tint.rgb;
	if (use_vertex_color) {
		base_albedo *= COLOR.rgb;
	}
	float alpha = tex.a * albedo_tint.a;
	if (is_fin) {
		if (alpha < alpha_scissor) {
			discard;
		}
	}

	vec3 n_w = normalize(v_world_normal);
	if (!FRONT_FACING) {
		n_w = -n_w;
	}
	if (has_normal_tex) {
		vec3 n_map = texture(normal_tex, UV).rgb;
		NORMAL_MAP = n_map;
		NORMAL_MAP_DEPTH = normal_depth;
		vec3 n_ts = n_map * 2.0 - 1.0;
		n_ts.xy *= normal_depth;
		vec3 t_w = normalize(v_world_tangent);
		vec3 b_w = normalize(v_world_binormal);
		if (!FRONT_FACING) {
			t_w = -t_w;
			b_w = -b_w;
		}
		n_w = normalize(t_w * n_ts.x + b_w * n_ts.y + n_w * max(n_ts.z, 0.1));
	}

	float ao_val = 1.0;
	float rough_val = is_fin ? 0.88 : wet_roughness;
	float metal_val = is_fin ? 0.0 : scale_metallic;
	if (has_orm_tex) {
		vec3 orm = texture(orm_tex, UV).rgb;
		if (has_ao_tex) {
			ao_val = orm.r;
		}
		// Keep underwater skin satin/velvety without harsh plastic glare; keep eyes glossy-wet
		rough_val = is_eye ? clamp(orm.g, 0.10, 0.55) : clamp(mix(orm.g, 0.68, is_fin ? 0.35 : 0.22), 0.32, 0.94);
		metal_val = is_eye ? orm.b : clamp(orm.b * 0.85, 0.0, 0.25);
	}

	vec3 v_w = normalize(CAMERA_POSITION_WORLD - v_world_pos);
	vec3 tank_pos = v_world_pos - tank_origin_world;
	float depth_below = max(0.0, waterline - tank_pos.y);
	float height_above_sand = max(0.0, tank_pos.y - sand_y);
	vec3 l_dir = normalize(light_tilt);

	// 1) Soft out-of-focus sunlit caustic dapples on dorsal back & upper sides
	vec2 proj_xz = tank_pos.xz + (light_tilt.xz / max(light_tilt.y, 0.25)) * depth_below;
	vec2 dapple_xz = proj_xz + vec2(0.0, tank_pos.y * 0.22);
	float pool = overhead_pools(proj_xz);
	float c_soft = soft_fish_caustics(dapple_xz, clock);
	float dorsal_wrap = smoothstep(-0.18, 0.72, dot(n_w, l_dir));
	float depth_atten = exp(-depth_below * 0.14);

	float c_active = is_eye ? 0.0 : clamp(caustic_strength * reflection_strength, 0.0, 1.2);
	float dapple_mod = mix(1.0, mix(0.84, 1.22, clamp(c_soft, 0.0, 1.0)), dorsal_wrap * c_active);

	ALBEDO = base_albedo * dapple_mod * mix(1.0, ao_val, 0.55);
	AO = ao_val;
	ROUGHNESS = rough_val;
	SPECULAR = is_eye ? 0.52 : (is_fin ? 0.10 : (has_orm_tex ? mix(0.28, 0.10, rough_val) : wet_specular));
	METALLIC = metal_val;

	// 2) Soft 360-degree underwater scattered ambient hemisphere
	float up_factor = clamp(n_w.y * 0.5 + 0.5, 0.0, 1.0);
	float down_factor = smoothstep(0.22, -0.70, n_w.y);
	float sand_prox = exp(-height_above_sand * 0.50);
	float bounce_soft = 0.85 + 0.22 * soft_fish_caustics(tank_pos.xz * 0.45, clock * 0.65);

	vec3 hemi_ambient = mix(side_water_ambient * 0.85, top_water_light * 0.42, smoothstep(0.35, 0.95, up_factor));
	vec3 ambient_fill = base_albedo * hemi_ambient * (0.30 + 0.28 * pool) * depth_atten * ao_val;
	vec3 sand_bounce = base_albedo * sand_bounce_color * down_factor * sand_prox * pool * bounce_soft * (is_eye ? 0.18 : 0.44) * ao_val;

	vec3 caustic_lift = is_eye ? vec3(0.0) : (base_albedo * caustic_color * c_soft * dorsal_wrap * depth_atten * pool * caustic_strength * 0.34 * ao_val);

	// 3) Per-scale silky satin light roll on silvery bony scales (or crisp subtle corneal catchlight on 3D eye)
	vec3 half_vec = normalize(l_dir + v_w);
	float ndoth = clamp(dot(n_w, half_vec), 0.0, 1.0);
	vec3 satin_roll = vec3(0.0);
	if (is_eye) {
		// Soft living corneal catchlight from overhead tank surface
		float cornea_glint = pow(ndoth, 36.0) * 0.55 + pow(ndoth, 8.0) * 0.12;
		satin_roll = top_water_light * cornea_glint * pool * depth_atten;
	} else {
		float effective_sheen = has_orm_tex ? (scale_sheen * (0.55 + 2.4 * metal_val) * (1.25 - rough_val)) : scale_sheen;
		float soft_satin = pow(ndoth, 6.5) * effective_sheen * pool * depth_atten * smoothstep(-0.2, 0.6, n_w.y + 0.35);
		satin_roll = mix(base_albedo, vec3(0.90, 0.95, 0.97), 0.48) * soft_satin * 0.42 * ao_val;
	}

	// 4) Delicate thin-fin translucency (stronger on thin membranes between rays, solid along bony spines!)
	vec3 fin_sss = vec3(0.0);
	if (is_fin && fin_translucency > 0.01) {
		float membrane_weight = has_orm_tex ? smoothstep(0.45, 0.72, rough_val) : 1.0;
		float backlit = pow(clamp(dot(-v_w, normalize(l_dir + n_w * 0.4)), 0.0, 1.0), 1.5);
		vec3 fin_tint = mix(base_albedo * 1.18, top_water_light, 0.34);
		fin_sss = fin_tint * (0.14 * pool + 0.30 * backlit * pool) * fin_translucency * mix(0.45, 1.25, membrane_weight) * depth_atten;
	}

	EMISSION = (ambient_fill + sand_bounce + caustic_lift + satin_roll + fin_sss) * reflection_strength;
}
