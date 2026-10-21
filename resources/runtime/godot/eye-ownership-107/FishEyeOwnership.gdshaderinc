// Explicit data textures: no source_color conversion and no mip levels.
uniform sampler2D eye_rest_lookup : filter_nearest, repeat_disable;
uniform sampler2D eye_uv_lookup : filter_nearest, repeat_disable;
uniform sampler2D eye_source_mask : filter_nearest, repeat_disable;
uniform vec2 eye_lookup_size;
uniform vec2 eye_source_size;
uniform int eye_vertex_count;
uniform int eye_mode = 0; //107:0 identity,1 local RGB trial,2 diagnostic
uniform int eye_probe = 0; // diagnostic only: 0 owners, 1 red, 2 green, 3 blue
uniform sampler2D eye_clean_source : source_color, filter_nearest, repeat_disable;
uniform sampler2D eye_clean_opaque : source_color, filter_nearest, repeat_disable;
uniform int eye_retired_probe = 0; //mode2 retirement-only RGB probe1/2/3
uniform sampler2D eye_fallback_mask : filter_nearest, repeat_disable;
uniform sampler2D eye_layer_mask : filter_nearest, repeat_disable;
uniform vec2 eye_anchor_xy;
uniform vec2 eye_pupil_uv;
uniform vec2 eye_pixel_native;
uniform float eye_downshift_pixels;
uniform vec2 eye_z_gap;
varying vec3 eye_reference_rest;
varying float eye_lookup_error;

vec4 eye_lookup_vertex(int index, vec2 actual_uv) {
    bool valid = index >= 0 && index < eye_vertex_count;
    int safe_index = clamp(index, 0, eye_vertex_count - 1);
    int width = int(eye_lookup_size.x);
    vec2 lookup_uv = (vec2(float(safe_index % width), float(safe_index / width)) + vec2(0.5)) / eye_lookup_size;
    vec4 reference = textureLod(eye_rest_lookup, lookup_uv, 0.0);
    vec4 expected_uv = textureLod(eye_uv_lookup, lookup_uv, 0.0);
    float mismatch = max(abs(actual_uv.x - expected_uv.x), abs(actual_uv.y - expected_uv.y));
    float error = (!valid || reference.w < 0.5 || expected_uv.w < 0.5 || mismatch > 0.000001) ? 1.0 : 0.0;
    return vec4(reference.xyz, error);
}

vec3 eye_probe_color(int probe) {
    if (probe == 1) return vec3(1.0,0.0,0.0);
    if (probe == 2) return vec3(0.0,1.0,0.0);
    return vec3(0.0,0.0,1.0);
}
vec4 eye_old_diagnostic(vec2 source_uv, vec4 original, float fallback) {
    if (eye_mode == 0 || eye_retired_probe > 0) return original;
    vec2 pixel = clamp(floor(source_uv * eye_source_size), vec2(0.0), eye_source_size - vec2(1.0));
    vec2 lookup = (pixel + vec2(0.5)) / eye_source_size;
    float mask = fallback > 0.5 ? texture(eye_fallback_mask, lookup).r : texture(eye_source_mask, lookup).r;
    if (mask < 0.5) return original;
    vec3 rgb;
    if (eye_mode == 1) rgb = fallback > 0.5 ? texture(eye_clean_opaque,lookup).rgb : texture(eye_clean_source,lookup).rgb;
    else rgb = eye_probe == 0 ? vec3(0.0,1.0,0.0) : eye_probe_color(eye_probe);
    return vec4(rgb,original.a);
}
vec4 eye_source_sample(vec2 source_uv) {
    return eye_old_diagnostic(source_uv, texture(source_texture, source_uv), 0.0);
}
vec4 eye_opaque_sample(vec2 source_uv) {
    return eye_old_diagnostic(source_uv, texture(opaque_skin, source_uv), 1.0);
}
vec3 eye_independent_diagnostic(vec3 original, vec3 point, vec3 modulation) {
    if (eye_mode == 0 || eye_retired_probe > 0) return original;
    vec2 anchor = eye_anchor_xy - vec2(0.0, eye_downshift_pixels * eye_pixel_native.y);
    vec2 uv = eye_pupil_uv + vec2((point.x-anchor.x)/(eye_pixel_native.x*eye_source_size.x), -(point.y-anchor.y)/(eye_pixel_native.y*eye_source_size.y));
    if (any(lessThan(uv,vec2(0.0))) || any(greaterThanEqual(uv,vec2(1.0)))) return original;
    vec2 lookup = (floor(uv * eye_source_size) + vec2(0.5)) / eye_source_size;
    vec4 source_eye = texture(source_texture,lookup);
    float alpha = source_eye.a * texture(eye_layer_mask,lookup).r;
    float owner = smoothstep(eye_z_gap.x,eye_z_gap.y,abs(point.z));
    if (eye_mode == 1) return mix(original,source_eye.rgb*modulation,alpha*owner);
    vec3 diagnostic = eye_probe > 0 ? eye_probe_color(eye_probe) : (point.z < 0.0 ? vec3(1.0,0.0,0.0) : vec3(0.0,0.0,1.0));
    vec3 result = mix(original,diagnostic*modulation,alpha*owner);
    // Orange explicitly identifies invalid eye footprint in the forbidden or
    // transition band; it is a diagnostic fault, never a rendered color eye.
    return eye_probe > 0 ? result : mix(result,vec3(1.0,0.5,0.0)*modulation,alpha*(1.0-owner));
}

vec3 eye_retired_diagnostic(vec3 original, float retired_weight) {
    if (eye_mode != 2) return original;
    int probe = eye_retired_probe > 0 ? eye_retired_probe : eye_probe;
    vec3 diagnostic = probe > 0 ? eye_probe_color(probe) : vec3(1.0,1.0,0.0);
    return mix(original,diagnostic,retired_weight);
}
