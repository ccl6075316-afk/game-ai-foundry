shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_disabled;
uniform sampler2D source_texture : source_color, filter_nearest, repeat_disable;
uniform vec4 tint : source_color = vec4(1.0);
uniform bool fin = false;
uniform sampler2D opaque_skin : source_color, filter_nearest, repeat_disable;
uniform int edge_count = 0;
uniform vec4 edges[128];
uniform vec2 source_size = vec2(1024.0);
uniform vec3 ink : source_color = vec3(0.1);
uniform float ink_width = 2.0;
uniform int patch_count = 0;
uniform vec4 patch_meta[8]; // start/count/donor low/donor high
uniform vec4 patch_rect[8];
uniform vec2 patch_points[512];

vec4 skin_sample(vec2 uv) {
    vec4 c=texture(source_texture,uv);
    return c.a<0.95 ? texture(opaque_skin,uv) : c;
}

uniform bool head_blend=false;
uniform sampler2D side_head : source_color,filter_nearest,repeat_disable;
uniform sampler2D front_head : source_color,filter_nearest,repeat_disable;
uniform float head_start=0.37;
uniform vec2 head_blend_x=vec2(0.44,0.49);
uniform vec4 head_side_uv=vec4(1.0,0.5,-2.995,0.5);
uniform vec4 head_front_uv=vec4(-18.0,0.5,-4.4646,0.5116);
uniform float head_front_x=0.0602;
varying vec3 rest_position;
#include "res://scripts/aquarium/FishHeadSource.gdshaderinc"
void vertex(){rest_position=VERTEX;}
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
                vec4 grain=skin_sample(donor);
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
    vec4 color=(repair ? repaired_color : skin_sample(donor))*tint*COLOR;
    if (fin) {
        float distance_px=100000.0;
        for (int i=0;i<edge_count;i++) {
            vec2 a=edges[i].xy*source_size; vec2 b=edges[i].zw*source_size;
            vec2 ab=b-a; float t=clamp(dot(UV*source_size-a,ab)/max(dot(ab,ab),0.00001),0.0,1.0);
            distance_px=min(distance_px,length(UV*source_size-a-t*ab));
        }
        if (distance_px<ink_width) color.rgb=min(color.rgb,ink);
    }
    if (head_blend && rest_position.x>head_start) {
        vec2 side_uv=vec2(rest_position.x*head_side_uv.x+head_side_uv.y,rest_position.y*head_side_uv.z+head_side_uv.w);
        vec4 side_color=texture(side_head,side_uv);
        vec2 front_uv=vec2(rest_position.z*head_front_uv.x+head_front_uv.y,rest_position.y*head_front_uv.z+head_front_uv.w+rest_position.x*head_front_x);
        vec4 front_color=texture(front_head,front_uv);
        color=mix(side_color,front_color,smoothstep(head_blend_x.x,head_blend_x.y,rest_position.x));
    }
    if(head_source_repair)color.rgb=repaired_head_color(UV,rest_position,UV2.y,color.rgb);
    ALBEDO=color.rgb;
    if(head_eye_debug>0){
        float eye=source_eye_footprint(UV)*(head_eye_debug==2?1.0:source_eye_keep(rest_position));
        ALBEDO=vec3(0.0);EMISSION=vec3(eye);
    }
    // Body surface coverage must never depend on a side artwork alpha mask.
    ROUGHNESS=1.0;
    METALLIC=0.0;
}
