shader_type spatial;
render_mode unshaded, cull_back;

uniform sampler2D front_art : source_color, filter_nearest, repeat_disable;
uniform sampler2D right_art : source_color, filter_nearest, repeat_disable;
uniform sampler2D top_art : source_color, filter_nearest, repeat_disable;
uniform vec3 projection_size = vec3(0.38, 0.16, 0.19);
varying vec3 source_position;
varying vec3 source_normal;

void vertex() {
    source_position = VERTEX;
    source_normal = NORMAL;
}

void fragment() {
    vec3 q = vec3(source_position.x / projection_size.x + 0.5,
                  source_position.y / projection_size.y,
                  source_position.z / projection_size.z + 0.5);
    vec3 n = abs(normalize(source_normal));
    // Each direction reads its own actual generated image. Smooth only the
    // projection boundary; native PNG texels retain nearest sampling.
    vec3 weight = pow(n, vec3(5.0));
    weight /= max(dot(weight, vec3(1.0)), 0.00001);
    vec4 front_color = texture(front_art, clamp(vec2(q.x, 1.0-q.y),0.0,1.0));
    vec4 right_color = texture(right_art, clamp(vec2(1.0-q.z, 1.0-q.y),0.0,1.0));
    vec4 top_color = texture(top_art, clamp(vec2(q.x, q.z),0.0,1.0));
    // Alpha is donor validity only, never surface transparency. A missing
    // end-view patch must not spread a background-edge streak over a branch.
    weight *= vec3(right_color.a, top_color.a, front_color.a);
    if (dot(weight,vec3(1.0)) < .001) {
        weight=vec3(0.0, max(top_color.a,.1), max(front_color.a,.1));
    }
    weight /= max(dot(weight,vec3(1.0)),.00001);
    ALBEDO = front_color.rgb * weight.z + right_color.rgb * weight.x + top_color.rgb * weight.y;
    ROUGHNESS = 1.0;
    SPECULAR = 0.0;
}
