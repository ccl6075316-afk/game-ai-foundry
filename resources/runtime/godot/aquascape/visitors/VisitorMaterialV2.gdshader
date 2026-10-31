shader_type spatial;
render_mode cull_back, diffuse_lambert, specular_disabled;

uniform sampler2D visitor_atlas : source_color, filter_nearest, repeat_disable;
uniform float crowd_time = 0.0;
uniform bool clay_preview = false;
varying float region;
varying float palette;

vec3 rotate_x(vec3 v,float a) {
	float c=cos(a); float s=sin(a);
	return vec3(v.x,c*v.y-s*v.z,s*v.y+c*v.z);
}
vec3 rotate_y(vec3 v,float a) {
	float c=cos(a); float s=sin(a);
	return vec3(c*v.x+s*v.z,v.y,-s*v.x+c*v.z);
}

void vertex() {
	float appearance=clamp(round(INSTANCE_CUSTOM.w),0.0,2.0);
	if(appearance>1.5) { VERTEX+=CUSTOM2.xyz; UV=CUSTOM3.xy; }
	else if(appearance>0.5) { VERTEX+=CUSTOM1.xyz; UV=UV2; }
	float limb=CUSTOM0.w;
	vec3 pivot=CUSTOM0.xyz;
	float weight=CUSTOM3.z;
	float motion=clamp(INSTANCE_CUSTOM.y,0.0,1.0);
	float phase=crowd_time*7.6+INSTANCE_CUSTOM.x;
	if(limb>0.5&&limb<4.5) {
		float side=(limb<1.5||(limb>2.5&&limb<3.5))?1.0:-1.0;
		float swing=sin(phase)*side;
		float angle=swing*motion*(limb<2.5?-0.24:0.24);
		if(limb>2.5) {
			float knee=pivot.y*0.51;
			float knee_weight=1.0-smoothstep(knee-0.055,knee+0.025,VERTEX.y);
			float bend=max(0.0,-swing)*motion*0.30;
			vec3 kp=vec3(pivot.x,knee,pivot.z);
			VERTEX=mix(VERTEX,kp+rotate_x(VERTEX-kp,bend),knee_weight);
			NORMAL=normalize(mix(NORMAL,rotate_x(NORMAL,bend),knee_weight));
		}
		VERTEX=mix(VERTEX,pivot+rotate_x(VERTEX-pivot,angle),weight);
		NORMAL=normalize(mix(NORMAL,rotate_x(NORMAL,angle),weight));
	} else if(limb>8.5) {
		float look=sin(crowd_time*0.6+INSTANCE_CUSTOM.x)*0.07*(1.0-motion);
		VERTEX=mix(VERTEX,pivot+rotate_y(VERTEX-pivot,look),weight);
		NORMAL=normalize(mix(NORMAL,rotate_y(NORMAL,look),weight));
	}
	VERTEX.y+=abs(sin(phase))*0.009*motion;
	region=CUSTOM3.w;
	palette=INSTANCE_CUSTOM.z;
}

vec3 clothing(float index) {
	if(index<0.5)return vec3(1.0);
	if(index<1.5)return vec3(.83,.92,.96);
	if(index<2.5)return vec3(.96,.86,.80);
	if(index<3.5)return vec3(.88,.95,.83);
	if(index<4.5)return vec3(.94,.87,.96);
	if(index<5.5)return vec3(.80,.88,.94);
	if(index<6.5)return vec3(.98,.95,.84);
	return vec3(.85,.85,.85);
}

void fragment() {
	vec3 paint=texture(visitor_atlas,UV).rgb;
	if(region>.5&&region<1.5) paint*=clothing(palette);
	ALBEDO=clay_preview?vec3(.62,.59,.54):paint;
	ROUGHNESS=1.0;
}
