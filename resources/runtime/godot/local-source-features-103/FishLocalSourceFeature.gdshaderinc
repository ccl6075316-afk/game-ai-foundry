uniform vec4 feature_eye;
uniform vec2 feature_normal_fade;
uniform vec4 feature_donor_rect;
uniform int feature_mode=1;
uniform int feature_type=0;
uniform sampler2D feature_ink_mask : filter_nearest, repeat_disable;
uniform sampler2D feature_ink_donors : filter_nearest, repeat_disable;
float local_source_feature_mask(vec2 uv,vec3 pos,vec3 normal){
    if(feature_type==1)return texture(feature_ink_mask,friendly_eye_uv(uv)).r;
    float in_eye=1.-smoothstep(1.0,1.15,length((friendly_eye_uv(uv)-feature_eye.xy)/feature_eye.zw));
    float central=1.-smoothstep(feature_normal_fade.x,feature_normal_fade.y,abs(normal.z));
    return in_eye*central*step(.30,pos.x);
}
vec3 local_source_feature_color(vec2 uv,vec3 pos,vec3 normal,vec3 original){
    float selected=local_source_feature_mask(uv,pos,normal);
    if(feature_mode==0)return original;
    if(feature_mode==2)return vec3(selected>0.?1.:0.);
    if(feature_mode==3)return mix(original,vec3(1.,0.,0.),selected);
    if(selected<=0.)return original;
    if(feature_type==1){
        vec4 encoded=round(texture(feature_ink_donors,friendly_eye_uv(uv))*255.);
        vec2 pixel=vec2(encoded.r*256.+encoded.g,encoded.b*256.+encoded.a);
        return mix(original,texture(source_texture,(pixel+.5)/source_size).rgb,selected);
    }
    // Mirror-repeat a frozen clean native patch at source pixel density.
    // The source image, actual lateral eye and all exterior pixels outside
    // this small spatial/source intersection keep their existing color.
    vec2 span=(feature_donor_rect.zw-feature_donor_rect.xy)*source_size;
    vec2 offset=(friendly_eye_uv(uv)-feature_eye.xy)*source_size;
    vec2 reflected=1.-abs(2.*fract(offset/(2.*span)) - 1.);
    vec2 donor=feature_donor_rect.xy+reflected*(feature_donor_rect.zw-feature_donor_rect.xy-1./source_size);
    return mix(original,texture(source_texture,donor).rgb,selected);
}
