// World-space dry tunnel segments; same cross-section equations as PassageRoute.
uniform int dry_count = 0;
uniform vec4 dry_a[48];
uniform vec4 dry_b[48];
uniform vec4 dry_profile = vec4(2.6,2.8,0.0,0.35); // width, top above floor, arch?, end overlap

vec3 dry_local(vec3 p,int i){
    vec3 a=dry_a[i].xyz;vec3 b=dry_b[i].xyz;
    vec2 axis=normalize(b.xz-a.xz);float length_xz=length(b.xz-a.xz);
    float z=dot(p.xz-a.xz,axis);
    return vec3(dot(p.xz-a.xz,vec2(-axis.y,axis.x)),p.y-a.y-z*(b.y-a.y)/length_xz,z);
}
float dry_radius(){return dry_profile.z<0.5?(dry_profile.y*dry_profile.y+dry_profile.x*dry_profile.x*0.25)/(2.0*dry_profile.y):dry_profile.x*0.5;}
bool passage_contains(vec3 p){
    float r=dry_radius();float center=dry_profile.y-r;
    for(int i=0;i<48;i++){
        if(i>=dry_count){break;}
        vec3 q=dry_local(p,i);float len=length(dry_b[i].xz-dry_a[i].xz);
        if(q.z< -dry_profile.w||q.z>len+dry_profile.w){continue;}
        float y=q.y-center;
        if(dry_profile.z>0.5){if(q.y<0.0){continue;}y=max(y,0.0);}
        if(dot(vec2(q.x,y),vec2(q.x,y))<=r*r){return true;}
    }
    return false;
}
vec2 dry_clip_axis(vec2 span,float p,float d,float lo,float hi){
    if(abs(d)<0.000001){return p<lo||p>hi?vec2(1.0,-1.0):span;}
    float a=(lo-p)/d;float b=(hi-p)/d;
    return vec2(max(span.x,min(a,b)),min(span.y,max(a,b)));
}
vec2 dry_circle(vec2 p,vec2 d,float r,vec2 span){
    float a=dot(d,d);float c=dot(p,p)-r*r;
    if(a<0.0000001){return c<=0.0?span:vec2(1.0,-1.0);}
    float b=dot(p,d);float disc=b*b-a*c;
    if(disc<0.0){return vec2(1.0,-1.0);}
    float root=sqrt(disc);
    return vec2(max(span.x,(-b-root)/a),min(span.y,(-b+root)/a));
}
vec2 dry_ray(vec3 origin,vec3 direction,int i,vec2 wet){
    vec3 p=dry_local(origin,i);vec3 d=dry_local(origin+direction,i)-p;
    float len=length(dry_b[i].xz-dry_a[i].xz);
    vec2 span=dry_clip_axis(wet,p.z,d.z,-dry_profile.w,len+dry_profile.w);
    if(span.y<=span.x){return vec2(1.0,-1.0);}
    float r=dry_radius();float center=dry_profile.y-r;
    vec2 circle=dry_circle(vec2(p.x,p.y-center),d.xy,r,span);
    if(dry_profile.z<0.5){return circle;}
    circle=dry_clip_axis(circle,p.y,d.y,center,dry_profile.y);
    vec2 rectangle=dry_clip_axis(span,p.x,d.x,-r,r);
    rectangle=dry_clip_axis(rectangle,p.y,d.y,0.0,center);
    bool c=circle.y>circle.x;bool b=rectangle.y>rectangle.x;
    if(c&&b){return vec2(min(circle.x,rectangle.x),max(circle.y,rectangle.y));}
    return c?circle:rectangle;
}
float passage_wet_length(vec3 origin,vec3 direction,vec2 wet){
    if(dry_count==0){return max(0.0,wet.y-wet.x);}
    vec2 spans[48];int count=0;
    for(int i=0;i<48;i++){
        if(i>=dry_count){break;}
        vec2 s=dry_ray(origin,direction,i,wet);
        if(s.y>s.x){spans[count]=s;count++;}
    }
    // Insertion-sort only actual intersections, then subtract their union once.
    for(int i=1;i<48;i++){
        if(i>=count){break;}
        vec2 value=spans[i];int target=i;
        for(int j=0;j<48;j++){
            if(target<=0){break;}
            if(spans[target-1].x<=value.x){break;}
            spans[target]=spans[target-1];target--;
        }
        spans[target]=value;
    }
    float dry_length=0.0;float end=wet.x;
    for(int i=0;i<48;i++){
        if(i>=count){break;}
        dry_length+=max(0.0,spans[i].y-max(end,spans[i].x));end=max(end,spans[i].y);
    }
    return max(0.0,wet.y-wet.x-dry_length);
}
