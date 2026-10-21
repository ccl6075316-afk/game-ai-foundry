// Injected after the original sampler uniforms, before its first function.
// Data textures have no source_color hint: their bytes encode labels/coordinates.
uniform sampler2D ink_mask : filter_nearest, repeat_disable;
uniform sampler2D ink_donors : filter_nearest, repeat_disable;
uniform vec2 ink_source_size = vec2(1.0);
uniform int ink_mode = 0; // 0 original, 1 donor, 2 red, 3 green, 4 blue

vec4 ink_replace_rgb(vec2 source_uv, vec4 original) {
    if (ink_mode == 0) return original;
    vec2 pixel = clamp(floor(source_uv * ink_source_size), vec2(0.0), ink_source_size - vec2(1.0));
    vec2 lookup = (pixel + vec2(0.5)) / ink_source_size;
    if (texture(ink_mask, lookup).r < 0.5) return original;
    vec3 rgb;
    if (ink_mode == 1) {
        vec4 bytes = floor(texture(ink_donors, lookup) * 255.0 + vec4(0.5));
        vec2 donor_pixel = vec2(bytes.r * 256.0 + bytes.g, bytes.b * 256.0 + bytes.a);
        // Read through the original source_color sampler, preserving its color conversion.
        rgb = texture(source_texture, (donor_pixel + vec2(0.5)) / ink_source_size).rgb;
    } else if (ink_mode == 2) {
        rgb = vec3(1.0, 0.0, 0.0);
    } else if (ink_mode == 3) {
        rgb = vec3(0.0, 1.0, 0.0);
    } else {
        rgb = vec3(0.0, 0.0, 1.0);
    }
    return vec4(rgb, original.a);
}

vec4 ink_source_sample(vec2 source_uv) {
    return ink_replace_rgb(source_uv, texture(source_texture, source_uv));
}
vec4 ink_opaque_sample(vec2 source_uv) {
    return ink_replace_rgb(source_uv, texture(opaque_skin, source_uv));
}
