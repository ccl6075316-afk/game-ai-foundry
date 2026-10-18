"""Parameter-only static oral-jaw geometry. No Blender, code or file fields.

Coordinates use normalized source u/v; gap, bevel and jaw projection use source
width native units. This is a production simplification, not a skeletal simulator.
"""
import math

FIELDS={'corner','front','gap','upper_retraction','lower_projection','lip_bevel','front_pigment_band'}
OPTIONAL_FIELDS={'slit_path','lip_roll','separate_lower','upper_lip_rounding','articulation'}

def validate_oral_jaws(data):
    def require(value,message):
        if not value:raise ValueError(message)
    def finite(value,lo,hi):
        return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and lo<=value<=hi
    require(isinstance(data,dict) and FIELDS<=set(data) and not set(data)-FIELDS-OPTIONAL_FIELDS,'oral_jaws requires the documented geometry and pigment fields only')
    for name in ('corner','front'):
        point=data[name]
        require(isinstance(point,list) and len(point)==2 and all(finite(x,0,1) for x in point),'Invalid oral '+name)
    require(data['front'][0]-data['corner'][0]>=.03,'Oral front must be at least 0.03 source width anterior to corner')
    for name,lo,hi in [('gap',.0002,.005),('upper_retraction',0,.025),('lower_projection',0,.025),('lip_bevel',0,.003)]:
        require(finite(data[name],lo,hi),'Invalid oral '+name)
    band=data['front_pigment_band']
    require(isinstance(band,list) and len(band)==2 and all(finite(x,0,1) for x in band) and band[1]-band[0]>=.02,'Invalid frontal painted-mouth removal band')
    if 'slit_path' in data:
        path=data['slit_path']
        require(isinstance(path,list) and 3<=len(path)<=16,'Oral path requires 3–16 landmarks')
        require(all(isinstance(p,list) and len(p)==2 and all(finite(x,0,1) for x in p) for p in path),'Invalid oral path point')
        require(path[0]==data['corner'] and path[-1]==data['front'],'Oral path must terminate at corner and front')
        require(all(a[0]<b[0] for a,b in zip(path,path[1:])),'Oral path u must increase')
    if 'lip_roll' in data:
        roll=data['lip_roll']
        require(isinstance(roll,dict) and set(roll)=={'radius','height','lower_ratio'},'Invalid lip roll fields')
        require(finite(roll['radius'],.002,.025) and finite(roll['height'],.0002,.008) and roll['height']<=roll['radius']*.6,'Invalid lip roll radius/height')
        require(finite(roll['lower_ratio'],.5,2) and roll['height']*roll['lower_ratio']<=roll['radius']*.75,'Invalid lower lip roll ratio')
    if 'upper_lip_rounding' in data:
        require('separate_lower' in data and finite(data['upper_lip_rounding'],.0002,.002),'Upper lip rounding requires separate jaw and radius 0.0002–0.002')
    if 'articulation' in data:
        motion=data['articulation']
        require('separate_lower' in data and isinstance(motion,dict) and set(motion)=={'hinge','max_open_degrees','fixed_root_u','rigid_start_u'},'Invalid jaw articulation fields')
        require(isinstance(motion['hinge'],list) and len(motion['hinge'])==2 and all(finite(x,0,1) for x in motion['hinge']),'Invalid jaw hinge')
        require(finite(motion['max_open_degrees'],1,18),'Jaw trial range must be 1–18 degrees')
        require(finite(motion['fixed_root_u'],data['separate_lower']['rear_u'],data['corner'][0]) and finite(motion['rigid_start_u'],data['corner'][0],data['front'][0]) and motion['rigid_start_u']>motion['fixed_root_u']+.01,'Invalid jaw root blend')
        require(abs(motion['hinge'][0]-data['corner'][0])<.03 and abs(motion['hinge'][1]-data['corner'][1])<.06,'Jaw hinge must lie near posterior mouth corner')
    if 'separate_lower' in data:
        lower=data['separate_lower']
        required={'rear_u','front_u','half_width','cup_depth','thickness','rim_rise','rim_height','planform_power'}
        require(isinstance(lower,dict) and required<=set(lower) and not set(lower)-required-{'heel_depth','bottom_width_ratio','root_thickness','lip_sections','root_surface_inset','lip_path','reference_shape'},'Invalid separate lower-jaw fields')
        for name,lo,hi in [('rear_u',0,1),('front_u',0,1.03),('half_width',.005,.10),('cup_depth',.001,.025),('thickness',.001,.015),('rim_rise',0,.008),('rim_height',0,.008),('planform_power',2,4),('heel_depth',0,.05)]:
            require(finite(lower.get(name,0),lo,hi),'Invalid separate lower-jaw '+name)
        require(lower['rear_u']<data['corner'][0]<lower['front_u'] and lower['rear_u']>=data['corner'][0]-.05 and abs(lower['front_u']-data['front'][0])<=.025,'Separate jaw must join behind corner and end near snout')
        require(finite(lower.get('bottom_width_ratio',1),.5,1),'Invalid lower-jaw bottom width ratio')
        require(finite(lower.get('root_thickness',lower['thickness']),.001,.015),'Invalid lower-jaw root thickness')
        if 'reference_shape' in lower:
            require(not ({'lip_path','lip_sections','root_surface_inset'}&set(lower)),'Reference jaw cannot also use legacy lip paths or sections')
            ref=lower['reference_shape']
            require(isinstance(ref,dict) and set(ref)=={'sections','open_degrees','web_end_u','side_projection_start_u'},'Invalid reference jaw fields')
            rows=ref['sections']
            require(isinstance(rows,list) and 4<=len(rows)<=128 and all(isinstance(row,list) and len(row)==4 and all(finite(x,0,1) for x in row) and row[1]<row[2] and .0001<=row[3]<=.1 for row in rows),'Invalid reference jaw sections')
            require(all(a[0]<b[0] for a,b in zip(rows,rows[1:])) and abs(rows[0][0]-lower['rear_u'])<1e-8 and abs(rows[-1][0]-lower['front_u'])<1e-8,'Reference jaw sections must span separate jaw bounds')
            require('articulation' in data and finite(ref['open_degrees'],1,18) and ref['open_degrees']==data['articulation']['max_open_degrees'],'Reference pose must match jaw controller range')
            require(finite(ref['web_end_u'],data['corner'][0]+.005,lower['front_u']-.01) and finite(ref['side_projection_start_u'],.6,data['corner'][0]),'Invalid reference jaw web or projection bounds')
        if 'lip_path' in lower:
            path=lower['lip_path']
            require(isinstance(path,list) and 3<=len(path)<=16 and all(isinstance(p,list) and len(p)==2 and all(finite(x,0,1) for x in p) for p in path),'Invalid independent lower lip path')
            require(path[0]==data['corner'] and abs(path[-1][0]-lower['front_u'])<1e-8 and all(a[0]<b[0] for a,b in zip(path,path[1:])),'Lower lip path must run from corner to separate jaw tip')
        if 'root_surface_inset' in lower:
            require('lip_sections' in lower and finite(lower['root_surface_inset'],.0001,.002),'Root fit requires section lips and a small surface inset')
        if 'lip_sections' in lower:
            rows=lower['lip_sections']
            require(isinstance(rows,list) and 3<=len(rows)<=12,'Lip sections need 3–12 stations')
            # u, half width, exposed lip band, edge thickness, rise, crest, underside width ratio.
            limits=[(0,1.03),(.005,.10),(.001,.015),(.001,.015),(0,.008),(0,.008),(.5,1)]
            require(all(isinstance(row,list) and len(row)==7 and all(finite(x,*limit) for x,limit in zip(row,limits)) for row in rows),'Invalid lip section values')
            require(all(a[0]<b[0] for a,b in zip(rows,rows[1:])) and rows[0][0]<=data['corner'][0] and rows[-1][0]>=lower['front_u'],'Lip sections must increase and span corner to jaw tip')
        require(not data.get('lip_roll') and data['lip_bevel']==0,'Separate-jaw study uses its own rolled rim; omit shell roll/bevel')

def validate_oral_context(data,body,spine):
    validate_oral_jaws(data)
    if spine[0][0]<=spine[-1][0]:raise ValueError('Oral cleft prototype currently requires head-right source orientation')
    rows=body['sections']
    if not rows[0][0]<data['corner'][0]<data['front'][0] or abs(data['front'][0]-rows[-1][0])>.025:
        raise ValueError('Oral landmarks must lie in anterior body and reach its tip')
    for u,v in data.get('slit_path',[data['corner'],data['front']]):
        row=rows[-1]
        for a,b in zip(rows,rows[1:]):
            if a[0]<=u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);row=[u,*[x+(y-x)*t for x,y in zip(a[1:],b[1:])]];break
        if not row[1]<v<row[2]:raise ValueError('Oral landmark must intersect body profile')

def slit_v(data,u):
    if data.get('slit_path'):
        path=data['slit_path']
        # Monotone cubic Hermite segments preserve the authored downturn without
        # overshooting a local high point. Legacy two-point profiles stay linear.
        slopes=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(path,path[1:])]
        tangents=[slopes[0]]
        for left,right in zip(slopes,slopes[1:]):
            tangents.append(2*left*right/(left+right) if left*right>0 else 0.)
        tangents.append(slopes[-1])
        if u<=path[0][0]:return path[0][1]+(u-path[0][0])*tangents[0]
        if u>=path[-1][0]:return path[-1][1]+(u-path[-1][0])*tangents[-1]
        for i,(a,b) in enumerate(zip(path,path[1:])):
            if a[0]<=u<=b[0]:
                width=b[0]-a[0];t=(u-a[0])/width
                return (2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*width*tangents[i]+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*width*tangents[i+1]
    a,b=data['corner'],data['front']
    return a[1]+(b[1]-a[1])*(u-a[0])/(b[0]-a[0])

def jaw_shift(data,u,v):
    a,b=data['corner'][0],data['front'][0]
    t=max(0.,min(1.,(u-(a+.28*(b-a)))/(.72*(b-a))))
    if data.get('slit_path'):
        blend=.5+.5*math.tanh((v-slit_v(data,u))/.015)
        return (-data['upper_retraction']*(1-blend)+data['lower_projection']*blend)*t**3
    if v<slit_v(data,u):return -data['upper_retraction']*t**3
    return data['lower_projection']*t**3
