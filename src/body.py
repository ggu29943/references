import bpy, math
from mathutils import Vector
from common import *
from math import sin,cos,pi,exp,sqrt
FINGER_POINTS={}
def head_surface(theta,z):
    profile=[(1.433,.012,.032),(1.445,.035,.048),(1.465,.055,.064),(1.495,.076,.076),(1.535,.096,.085),(1.575,.102,.090),(1.615,.100,.091),(1.650,.090,.083),(1.681,.070,.064),(1.702,.039,.038),(1.712,.002,.002)]
    for i in range(len(profile)-1):
        if profile[i][0]<=z<=profile[i+1][0]:
            a,b=profile[i],profile[i+1];t=(z-a[0])/(b[0]-a[0]);rx=a[1]*(1-t)+b[1]*t;ry=a[2]*(1-t)+b[2]*t;break
    else:rx,ry=.002,.002
    x=rx*sin(theta);c=cos(theta)
    y=-ry*(c**.42 if c>0 else -(-c)**.85)
    if c>0:
        y-=.019*exp(-(x/.014)**2-((z-1.535)/.020)**2)
        y-=.005*exp(-(x/.018)**2-((z-1.558)/.038)**2)
        y-=.003*exp(-(x/.029)**2-((z-1.487)/.015)**2)
    return x,y,z

def build():
    start=set(bpy.data.objects);collection('01_Body')
    skin=material('Skin · porcelain warm',(.84,.75,.72,1),roughness=.55)
    p=skin.node_tree.nodes.get('Principled BSDF');p.inputs['Subsurface Weight'].default_value=.12
    p.inputs['Specular IOR Level'].default_value=.25
    if 'Subsurface Scale' in p.inputs:p.inputs['Subsurface Scale'].default_value=.008
    pink=material('Lips · muted rose',(.65,.40,.41,1),roughness=.49)
    liplight=material('Lips · lower highlight',(.76,.49,.48,1),roughness=.36)
    crease=material('Lip seam',(.40,.24,.27,1),roughness=.6)
    earshade=material('Ear inner warm',(.60,.365,.35,1))
    whites=material('Eye · warm sclera',(.74,.79,.83,1),roughness=1)
    liner=material('Lashes · silver charcoal',(.08,.075,.094,1),roughness=.6)
    brow=material('Eyebrows · silver ash',(.35,.32,.39,1),roughness=.7)
    iris=material('Iris · ice blue',(.16,.34,.53,1),roughness=1)
    irisl=material('Iris · pale blue',(.21,.39,.57,1),roughness=1)
    irisd=material('Iris · limbal ring',(.09,.18,.29,1),roughness=1)
    pupil=material('Pupil · midnight blue',(.035,.055,.085,1),roughness=1)
    # Canon: no catchlights, glossy cornea highlights or emissive iris detail.
    for eye_mat in [whites,iris,irisl,irisd,pupil]:
        shader=eye_mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Specular IOR Level'].default_value=0
        shader.inputs['Coat Weight'].default_value=0
        shader.inputs['Emission Strength'].default_value=0
    # Dense quad head with integrated nose and pointed anime chin.
    verts=[];faces=[];nu=96;nv=64
    for i in range(nv+1):
        z=1.433+(1.712-1.433)*i/nv
        for j in range(nu):verts.append(head_surface(2*pi*j/nu,z))
    for i in range(nv):
        for j in range(nu):a=i*nu+j;b=i*nu+(j+1)%nu;faces.append((a,b,b+nu,a+nu))
    faces.extend([tuple(range(nu-1,-1,-1)),tuple(nv*nu+j for j in range(nu))])
    h=mesh('Head · quad surface',verts,faces,skin,'head')
    uv=h.data.uv_layers.new(name='UVMap')
    for poly in h.data.polygons:
        for li in poly.loop_indices:
            vi=h.data.loops[li].vertex_index;uv.data[li].uv=((vi%nu)/nu,(vi//nu)/nv)
    # Delicate ears and visible helix.
    for s,side in [(1,'l'),(-1,'r')]:
        uv_sphere('Ear '+side,(s*.101,.001,1.556),(.017,.016,.032),skin,'head',32,20)
        uv_sphere('Ear concha '+side,(s*.108,-.014,1.556),(.008,.003,.019),earshade,'head',24,16)
        curve('Ear helix '+side,[(s*(.105+.009*sin(a)),-.016,1.556+.025*cos(a)) for a in [0,.6,1.3,2,2.8,3.6,4.5,5.3,6.28]],.0028,skin,'head')
        curve('Ear antihelix '+side,[(s*.105,-.019,1.541),(s*.112,-.019,1.551),(s*.109,-.019,1.569)],.002,skin,'head')
    # Almond eyes: shallow continuous surfaces, no protruding eyeballs.
    for s,side in [(1,'l'),(-1,'r')]:
        cx=s*.043;cz=1.581
        def ep(t,v):
            x=cx+.031*t;mid=cz+s*.002*t;up=.0065*max(0,1-t*t)**.65;down=.0070*max(0,1-t*t)**.6
            z=mid+(up*v if v>=0 else down*v)
            y=-.0915-.004*max(0,1-t*t)*(1-v*v)
            return (x,y,z)
        rows=[[ep(-1+2*j/32,-1+2*i/12) for j in range(33)] for i in range(13)]
        eye=ribbon('Eye white '+side,rows,whites,'head')
        eye.shape_key_add(name='Basis');blink=eye.shape_key_add(name='Blink_'+side.upper())
        for v in blink.data:v.co.z=cz+s*.002*(v.co.x-cx)/.031
        # Skin lids stretch over the almond aperture when Blink is driven.
        for upper in [True,False]:
            lidrows=[]
            for row in range(3):
                rr=[]
                for j in range(33):
                    t=-1+2*j/32;x,y,z=ep(t,1 if upper else -1)
                    z+=(1 if upper else -1)*(.0008+row*.0018)*max(0,1-t*t)
                    rr.append((x,y-.0018,z))
                lidrows.append(rr)
            lid=ribbon(('Upper eyelid ' if upper else 'Lower eyelid ')+side,lidrows,skin,'head')

            if not upper:
                for poly in lid.data.polygons:poly.flip()
            lid.shape_key_add(name='Basis');bk=lid.shape_key_add(name='Blink_'+side.upper())
            for i,v in enumerate(bk.data):
                row=i//33;t=-1+2*(i%33)/32
                if row<2:
                    closure=cz+s*.002*t-.001*max(0,1-t*t)
                    v.co.z=closure*(1-row*.40)+v.co.z*(row*.40)
                    v.co.y=-.099+ .006*abs(t)
        # Radial iris, segmented color filaments on curved visible disk.
        rad=.0135;vs=[(cx,-.0971,cz)];fs=[];N=64
        for r in [.0031,.0118,.0135]:
            for j in range(N):
                a=2*pi*j/N;x=cx+r*sin(a);t=(x-cx)/.031
                top=ep(t,1)[2]-.0006;bottom=ep(t,-1)[2]+.0005
                vs.append((x,-.0967-.0004*(1-(r/rad)**2),max(bottom,min(top,cz+r*cos(a)))))
        for j in range(N):fs.append((0,1+j,1+(j+1)%N))
        for k in range(2):
            for j in range(N):a=1+k*N+j;b=1+k*N+(j+1)%N;fs.append((a,b,b+N,a+N))
        io=mesh('Iris '+side,vs,[tuple(reversed(f)) for f in fs],iris,'head');io.data.materials.clear()
        for m in [pupil,iris,irisl,irisd]:io.data.materials.append(m)
        for p in io.data.polygons:p.material_index=0 if p.index<N else (3 if p.index>=2*N else (2 if p.index%3==0 else 1))
        io.shape_key_add(name='Basis');bk=io.shape_key_add(name='Blink_'+side.upper())
        for v in bk.data:v.co.z=cz;v.co.y=-.090
        for upper in [True,False]:
            pts=[ep(-1+2*j/24,1 if upper else -1) for j in range(25)]
            pts=[(x,y-.0015,z) for x,y,z in pts]
            curve(('Upper lash ' if upper else 'Lower lid ')+side,pts,.0009 if upper else .00035,liner if upper else pink,'head')
        outer=cx+s*.031
        curve('Outer lash flick '+side,[(outer-s*.005,-.093,cz+.007),(outer+s*.004,-.09,cz+.008),(outer+s*.005,-.088,cz+.009)],.0008,liner,'head')
        curve('Lid fold '+side,[(cx-.024,-.091,cz+.012),(cx,-.095,cz+.014),(cx+.026,-.090,cz+.012)],.00055,earshade,'head')
        curve('Silver eyebrow '+side,[(cx-.027,-.087,cz+.034),(cx-.009,-.094,cz+.038),(cx+.009,-.094,cz+.038),(cx+.027,-.086,cz+.032)],.0010,brow,'head')
    # Lips stay small and quiet, matching reference expression.
    curve('Upper lip', [(-.018,-.081,1.503),(-.009,-.084,1.505),(0,-.085,1.504),(.009,-.084,1.505),(.018,-.081,1.503)],.0009,pink,'head')
    curve('Mouth line',[(-.017,-.082,1.5025),(0,-.086,1.5015),(.017,-.082,1.5025)],.00065,crease,'head')
    curve('Lower lip',[(-.013,-.082,1.500),(0,-.085,1.4985),(.013,-.082,1.500)],.0011,liplight,'head')
    for s in [-1,1]:curve('Nostril '+str(s),[(s*.005,-.1045,1.526),(s*.009,-.103,1.525),(s*.012,-.099,1.527)],.0005,earshade,'head')
    torso=loft('Body · torso',[(.86,.11,.072,.005),(.90,.14,.085,.006),(.96,.14,.088,.003),(1.02,.115,.071,0),(1.10,.098,.062,0),(1.16,.111,.069,0),(1.22,.137,.075,0),(1.27,.145,.080,0),(1.31,.151,.070,.003),(1.35,.155,.059,.004),(1.38,.11,.046,.002),(1.40,.047,.037,0),(1.43,.037,.033,0),(1.46,.037,.032,0)],skin)
    def tw(co):
        z=co.z;levels=[(.93,'pelvis'),(1.08,'spine_01'),(1.21,'spine_02'),(1.34,'spine_03'),(1.43,'neck_01')]
        if z<=levels[0][0]:return {'pelvis':1}
        for (a,an),(b,bn) in zip(levels,levels[1:]):
            if a<=z<=b:t=(z-a)/(b-a);return {an:1-t,bn:t}
        return {'neck_01':1}
    weights(torso,tw)
    nails=material('Nails · sheer ivory',(.85,.73,.71,1),roughness=.3)
    shoes=material('Shoes · black leather',(.027,.023,.033,1),roughness=.28)
    soles=material('Shoe sole',(.018,.016,.021,1),roughness=.65)
    socks=material('Socks · white silk',(.81,.83,.90,1),roughness=.65)
    for s,side in [(1,'l'),(-1,'r')]:
        armpts=[(s*.145,0,1.345),(s*.18,0,1.325),(s*.215,0,1.27),(s*.255,0,1.19),(s*.285,-.004,1.12),(s*.305,-.008,1.075),(s*.33,-.01,1.015),(s*.36,-.01,.925)]
        o=tube('Arm '+side,armpts,[.043,.041,.036,.030,.027,.028,.024,.018],skin,segments=24)
        weights(o,lambda co:{'upperarm_'+side:max(0,min(1,(co.z-1.095)/.05)),'lowerarm_'+side:1-max(0,min(1,(co.z-1.095)/.05))})
        # Palm is a tapered flattened tube, fingers have real joint loops.
        palm=tube('Palm '+side,[(s*.36,-.01,.935),(s*.369,-.012,.911),(s*.378,-.013,.881),(s*.380,-.014,.868)],[(.018,.011),(.022,.013),(.026,.012),(.023,.010)],skin,'hand_'+side,24)
        for j,(fn,flen) in enumerate([('index',.064),('middle',.074),('ring',.068),('pinky',.052)]):
            x=s*(.358+j*.0145);z=.881-abs(j-1)*.003
            pts=[]
            for k,t in enumerate([0,.12,.30,.44,.58,.73,.87,1]):pts.append((x+s*.008*t,-.015-.008*t*t,z-flen*t))
            radii=[.008,.0082,.0075,.007,.0068,.0062,.0053,.0025]
            finger=tube(fn+' '+side,pts,radii,skin,segments=12)
            def fw(co,z=z,flen=flen,fn=fn,side=side):
                t=(z-co.z)/flen
                if t<.36:return {fn+'_01_'+side:1}
                if t<.66:return {fn+'_02_'+side:1}
                return {fn+'_03_'+side:1}
            weights(finger,fw)
            FINGER_POINTS[(fn,side)]=[pts[0],pts[3],pts[5],pts[-1]]
            uv_sphere('Nail '+fn+' '+side,(pts[-2][0],pts[-2][1]-.005,pts[-2][2]),(.0042,.001,.007),nails,fn+'_03_'+side,16,8)
        pts=[(s*.351,-.012,.908),(s*.339,-.016,.896),(s*.330,-.020,.881),(s*.326,-.023,.866),(s*.329,-.026,.854)]
        o=tube('Thumb '+side,pts,[.011,.0095,.008,.007,.0035],skin,segments=14)
        weights(o,lambda co:{'thumb_01_'+side:1} if co.z>.884 else ({'thumb_02_'+side:1} if co.z>.869 else {'thumb_03_'+side:1}))
        FINGER_POINTS[('thumb',side)]=[pts[0],pts[1],pts[3],pts[4]]
        uv_sphere('Thumbnail '+side,(s*.329,-.031,.862),(.005,.001,.007),nails,'thumb_03_'+side,16,8)
        leg=tube('Leg '+side,[(s*.075,.005,.92),(s*.083,.002,.84),(s*.084,0,.70),(s*.083,-.012,.53),(s*.081,-.01,.49),(s*.082,.003,.40),(s*.082,.007,.25),(s*.082,0,.11)],[(.067,.070),(.067,.063),(.052,.052),(.035,.035),(.034,.035),(.046,.043),(.030,.030),(.021,.023)],skin,segments=24)
        weights(leg,lambda co:{'thigh_'+side:max(0,min(1,(co.z-.49)/.07)),'calf_'+side:1-max(0,min(1,(co.z-.49)/.07))})
        uv_sphere('Sock foot '+side,(s*.083,-.027,.087),(.032,.078,.038),socks,'foot_'+side,32,20)
        uv_sphere('Shoe '+side,(s*.083,-.044,.049),(.039,.091,.033),shoes,'foot_'+side,40,20)
        uv_sphere('Sole '+side,(s*.083,-.043,.024),(.0395,.091,.009),soles,'foot_'+side,32,12)
        # Low block heel.
        heel=loft('Heel '+side,[(.0,.028,.025,.012),(.028,.028,.027,.012)],soles,'foot_'+side,20)
        for v in heel.data.vertices:v.co.x+=s*.083
    return list(set(bpy.data.objects)-start)
