shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_disabled;
uniform sampler2D source_texture : source_color, filter_nearest, repeat_disable;
uniform vec4 tint : source_color = vec4(1.0);
uniform bool fin = false;
uniform int edge_count = 0;
uniform vec4 edges[128];
uniform vec2 source_size = vec2(1024.0);
uniform vec3 ink : source_color = vec3(0.1);
uniform float ink_width = 2.0;
uniform int patch_count = 0;
uniform vec4 patch_meta[8]; // start/count/donor low/donor high
uniform vec4 patch_rect[8];
uniform vec2 patch_points[512];

void fragment() {
    vec2 donor = UV;
    vec4 repaired_color=vec4(0.0);
    bool repair=false;
    if (!fin) {
        for (int j=0;j<patch_count;j++) {
            vec4 rect=patch_rect[j];
            if (UV.x<rect.x || UV.x>rect.z || UV.y<rect.y || UV.y>rect.w) continue;
            int start=int(patch_meta[j].x); int count=int(patch_meta[j].y);
            bool inside=false;
            float top_y=1.0;float bottom_y=0.0;
            for (int k=0;k<count;k++) {
                vec2 a=patch_points[start+k]; vec2 b=patch_points[start+(k+1)%count];
                if ((a.y>UV.y)!=(b.y>UV.y)) {
                    float at_x=a.x+(UV.y-a.y)*(b.x-a.x)/(b.y-a.y);
                    if (UV.x<at_x) inside=!inside;
                }
                if ((a.x>UV.x)!=(b.x>UV.x)) {
                    float at_y=a.y+(UV.x-a.x)*(b.y-a.y)/(b.x-a.x);
                    top_y=min(top_y,at_y);bottom_y=max(bottom_y,at_y);
                }
            }
            if (inside) {
                float width=max(0.0001,patch_meta[j].w-patch_meta[j].z);
                donor.x=patch_meta[j].z+mod(UV.x-rect.x,width);
                // Belly footprints can extend beyond the source silhouette.
                // Search upward for opaque skin, never reuse the painted fin.
                for (int k=0;k<24;k++) {
                    if (texture(source_texture,donor).a>0.95) break;
                    donor.y=max(0.0,donor.y-2.0/source_size.y);
                }
                vec4 grain=texture(source_texture,donor);
                vec4 above=texture(source_texture,vec2(UV.x,max(0.0,top_y-4.0/source_size.y)));
                vec4 below=texture(source_texture,vec2(UV.x,min(1.0,bottom_y+4.0/source_size.y)));
                float donor_light=dot(grain.rgb,vec3(0.2126,0.7152,0.0722));
                if (above.a<0.95 || dot(above.rgb,vec3(0.2126,0.7152,0.0722))<donor_light*0.65) above=grain;
                if (below.a<0.95 || dot(below.rgb,vec3(0.2126,0.7152,0.0722))<donor_light*0.65) below=grain;
                float along=clamp((UV.y-top_y)/max(0.0001,bottom_y-top_y),0.0,1.0);
                repaired_color=mix(above,below,along);
                vec4 nearby=texture(source_texture,vec2(donor.x,max(0.0,donor.y-3.0/source_size.y)));
                repaired_color.rgb=clamp(repaired_color.rgb+0.35*(grain.rgb-nearby.rgb),vec3(0.0),vec3(1.0));
                repaired_color.a=1.0;repair=true;
                break;
            }
        }
    }
    vec4 color=(repair ? repaired_color : texture(source_texture,donor))*tint*COLOR;
    if (fin) {
        float distance_px=100000.0;
        for (int i=0;i<edge_count;i++) {
            vec2 a=edges[i].xy*source_size; vec2 b=edges[i].zw*source_size;
            vec2 ab=b-a; float t=clamp(dot(UV*source_size-a,ab)/max(dot(ab,ab),0.00001),0.0,1.0);
            distance_px=min(distance_px,length(UV*source_size-a-t*ab));
        }
        if (distance_px<ink_width) color.rgb=min(color.rgb,ink);
    }
    ALBEDO=color.rgb;
    ALPHA=color.a;
    ALPHA_SCISSOR_THRESHOLD=0.5;
    ROUGHNESS=1.0;
    METALLIC=0.0;
}
