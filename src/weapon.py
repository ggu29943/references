"""Image-reference Caiheng variant; the original plain text variant is preserved separately."""
import bpy,math,random,bmesh
from pathlib import Path
from mathutils import Vector,Matrix
from common import collection,material,mesh,curve,uv_sphere,loft
CHI_METERS=1/3
BLADE_LENGTH_M=2.5*CHI_METERS


def mat(name,col,metal=0,rough=.4):
    return material(name,(*col,1),metal,rough)

def rib(name,points,r,ma):
    return curve(name,points,r,ma)

def plate(name,outline,ma,depth=.003):
    # Outlines are (x,z), face towards -Y with actual thickness.
    n=len(outline);v=[(x,y,z) for y in [-depth,depth] for x,z in outline]
    f=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,v,f,ma)
    be=o.modifiers.new('Soft chased edge','BEVEL');be.width=.0006;be.segments=3
    return o

def petal(name,c,dx,dz,length,width,ma):
    c=Vector(c);d=Vector((dx,0,dz)).normalized();cross=Vector((-d.z,0,d.x));rows=[]
    for i in range(11):
        t=i/10;row=[]
        for j in range(7):
            u=-1+2*j/6;w=width*(math.sin(math.pi*t)**.8)
            p=c+d*(length*t)+cross*(w*u)
            p.y-=.0026*math.sin(math.pi*t)*(1-u*u)+.0006*math.sin(math.pi*t)*abs(u)
            row.append(tuple(p))
        rows.append(row)
    vs=[p for row in rows for p in row];fs=[]
    for i in range(10):
        for j in range(6):a=i*7+j;fs.append((a,a+1,a+8,a+7))
    o=mesh(name,vs,fs,ma);m=o.modifiers.new('Petal thickness','SOLIDIFY');m.thickness=.00045
    rib(name+' vein',[tuple(c),tuple(c+d*length*.5+Vector((0,-.003,0))),tuple(c+d*length*.95)],.0003,ma)
    return o

def flower(c,size,ma):
    for k in range(5):
        a=2*math.pi*k/5;petal('Silver flower petal',c,math.sin(a),math.cos(a),size,size*.29,ma)
    uv_sphere('Flower centre',c,(size*.14,.002,size*.14),ma,segments=16,rings=8)

def vine(x,z,length,y,ma):
    pts=[(x,y,z),(x+.006,y,z+length*.3),(x-.004,y,z+length*.65),(x,y,z+length)]
    rib('Silver botanical stem',pts,.00065,ma)
    for j in range(5):
        t=.12+j*.16;sg=1 if j%2 else -1
        petal('Small silver leaf',(x+.003*math.sin(t*5),y-.0003,z+length*t),sg*.7,.6,.017,.0035,ma)

def join_group(name,objects):
    # Convert all sculpted profiles to normal editable meshes before FBX export.
    for o in objects:
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        if o.type=='CURVE':bpy.ops.object.convert(target='MESH')
        for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    uv=o.data.uv_layers.active if o.data.uv_layers else o.data.uv_layers.new(name='UVMap')
    for p in o.data.polygons:
        for li in p.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(co.x*3+.5,co.z/(BLADE_LENGTH_M+.25)+.2)
    o['part']='caiheng_prop';o['variant']='image_reference';o['blade_length_m']=BLADE_LENGTH_M
    o['provisional_chi_meters']=CHI_METERS
    return o

def build():
    collection('PROPS · Caiheng image reference')
    silver=mat('Caiheng • chased silver',(.66,.68,.72),.82,.29)
    silverlight=mat('Caiheng • silver petal face',(.78,.79,.82),.72,.35)
    frost=mat('Caiheng • brushed frost blade',(.72,.75,.80),.65,.42)
    dark=mat('Caiheng • charcoal leather',(.023,.028,.043),0,.73)
    silk=mat('Caiheng • white silk tassel',(.88,.89,.93),0,.55)
    pearl=mat('Caiheng • pale pearl',(.78,.81,.90),.1,.20)
    # Blender close-up leather and brushed steel; export uses material constants.
    for ma,scale,strength in [(dark,350,.10),(frost,900,.045)]:
        ns=ma.node_tree.nodes;ls=ma.node_tree.links;p=ns.get('Principled BSDF')
        tc=ns.new('ShaderNodeTexCoord');noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale
        bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=strength;bump.inputs['Distance'].default_value=.00025
        ls.new(tc.outputs['Generated'],noise.inputs['Vector']);ls.new(noise.outputs['Fac'],bump.inputs['Height']);ls.new(bump.outputs['Normal'],p.inputs['Normal'])
    start=set(bpy.data.objects)
    # Diamond section, straight narrow blade and actual cutting bevels.
    sections=[(0,.022,.0027),(.045,.0215,.0026),(.60,.020,.0024),(BLADE_LENGTH_M-.075,.018,.0021),(BLADE_LENGTH_M-.018,.006,.0009)]
    vs=[];fs=[]
    for z,w,d in sections:vs.extend([(0,-d,z),(w*.78,-d*.68,z),(w,-.0001,z),(w,.0001,z),(w*.78,d*.68,z),(0,d,z),(-w*.78,d*.68,z),(-w,.0001,z),(-w,-.0001,z),(-w*.78,-d*.68,z)])
    for i in range(len(sections)-1):
        for j in range(10):a=i*10+j;b=i*10+(j+1)%10;fs.append((a,b,b+10,a+10))
    fs.append(tuple(reversed(range(10))));tip=len(vs);vs.append((0,0,BLADE_LENGTH_M))
    for j in range(10):fs.append(((len(sections)-1)*10+j,(len(sections)-1)*10+(j+1)%10,tip))
    blade=mesh('Caiheng blade',vs,fs,frost)
    for p in blade.data.polygons:p.use_smooth=False
    for sg in [-1,1]:rib('Blade fine ridge',[(sg*.0007,-.00285,.045),(sg*.0007,-.00265,.60),(0,-.001,BLADE_LENGTH_M-.018)],.00018,silverlight)
    loft('Dark unwrapped grip',[(-.165,.012,.008,0),(-.155,.014,.009,0),(-.032,.013,.009,0),(-.017,.015,.0095,0)],dark,segments=32)
    for z in [-.165,-.157,-.025,-.017]:loft('Grip silver ring',[(z-.002,.016,.011,0),(z+.002,.016,.011,0)],silver,segments=40)
    flower((0,-.010,-.108),.009,silverlight);vine(0,-.097,.065,-.010,silverlight)
    # Hollow flowing guard: paired rib outlines leave negative spaces.
    plate('Guard central frost spear',[(0,-.031),(.025,.012),(.018,.047),(0,.098),(-.018,.047),(-.025,.012)],frost,.005)
    for sg in [-1,1]:
        paths=[[(0,-.030),(.024,-.010),(.043,.010),(.085,.009),(.113,.028),(.128,.048)],[(.128,.048),(.110,.040),(.088,.044),(.057,.027),(.028,.043),(0,.098)],[(.018,-.010),(.040,.020),(.075,.022),(.094,.032),(.073,.036),(.037,.029),(.016,.062)],[(.010,.005),(.027,.014),(.035,.038),(.018,.052),(0,.082)]]
        for k,path in enumerate(paths):rib('Openwork guard rib',[(sg*x,-.004,z) for x,z in path],.0033 if k<2 else .0022,silver)
    # Symmetric leaf-form sword pommel, black handle and silver casing.
    plate('Pommel central leaf',[(0,-.225),(.026,-.193),(.019,-.171),(-.019,-.171),(-.026,-.193)],frost,.006)
    for sg in [-1,1]:
        for path in [[(0,-.227),(.014,-.211),(.032,-.205),(.037,-.188),(.022,-.192),(.015,-.171)],[(0,-.222),(.007,-.202),(.023,-.198),(.017,-.178)],[(0,-.216),(.014,-.195),(.004,-.177)]]:
            rib('Pommel chased ribs',[(sg*x,-.006,z) for x,z in path],.0022,silver)
    sword=join_group('Caiheng_Sword',list(set(bpy.data.objects)-start));sword['prop_kind']='sword'
    # Actual hollow scabbard body, sized to receive the straight blade.
    start=set(bpy.data.objects);length=BLADE_LENGTH_M+.026;n=32;v=[];f=[]
    outer=[(0,.025,.011),(.02,.025,.011),(length-.055,.023,.010),(length-.015,.010,.006),(length,.002,.002)]
    inner=[(0,.023,.004),(.02,.023,.004),(length-.06,.020,.0035),(length-.022,.003,.001)]
    for z,w,d in outer+inner:
        for j in range(n):a=2*math.pi*j/n;v.append((w*math.copysign(abs(math.cos(a))**.5,math.cos(a)),d*math.copysign(abs(math.sin(a))**.6,math.sin(a)),z))
    for i in range(len(outer)-1):
        for j in range(n):a=i*n+j;b=i*n+(j+1)%n;f.append((a,b,b+n,a+n))
    off=len(outer)*n
    for i in range(len(inner)-1):
        for j in range(n):a=off+i*n+j;b=off+i*n+(j+1)%n;f.append((a,a+n,b+n,b))
    for j in range(n):k=(j+1)%n;f.append((j,off+j,off+k,k))
    f.append(tuple((len(outer)-1)*n+j for j in range(n)));f.append(tuple(reversed([off+(len(inner)-1)*n+j for j in range(n)])))
    mesh('Dark leather scabbard',v,f,dark)
    for sg in [-1,1]:rib('Scabbard silver border',[(sg*.025,-.008,.016),(sg*.025,-.008,.3),(sg*.024,-.008,.68),(sg*.022,-.008,length-.055)],.0015,silver)
    for z,size in [(.14,.017),(.30,.014),(.65,.010),(.78,.008)]:flower((0,-.012,z),size,silverlight)
    vine(0,.04,.18,-.012,silverlight);vine(0,.20,.22,-.012,silverlight);vine(0,.60,.16,-.012,silverlight)
    # Elaborate throat collar and terminal chape echo the pommel.
    for end,sgz in [(0,1),(length-.012,-1)]:
        plate('Scabbard silver diamond',[(0,end+sgz*.067),(.016,end+sgz*.022),(0,end),(-.016,end+sgz*.022)],frost,.014)
        for sg in [-1,1]:
            for path in [[(0,0),(.026,.001),(.035,.012),(.026,.021),(.017,.039),(0,.067)],[(0,.008),(.018,.016),(.024,.029),(.009,.034),(0,.055)]]:
                rib('Throat and chape ribs',[(sg*x,-.014,end+sgz*z) for x,z in path],.0021,silver)
    sheath=join_group('Caiheng_Sheath',list(set(bpy.data.objects)-start));sheath['prop_kind']='sheath'
    # Separate white tassel with braided cord, pearl and multiple silk filaments.
    start=set(bpy.data.objects);rng=random.Random(624)
    for k in range(3):
        pts=[]
        for j in range(42):t=j/41;a=t*math.tau*8+k*math.tau/3;pts.append((.001*math.cos(a),.001*math.sin(a),-.065*t))
        rib('Braided white suspension',pts,.00065,silk)
    for z,r,ma in [(-.071,.005,silver),(-.086,.006,pearl),(-.107,.015,pearl),(-.129,.006,pearl),(-.145,.008,silver)]:uv_sphere('Tassel bead',(0,0,z),(r,r,r),ma,segments=24,rings=12)
    for sign,z in [(1,-.065),(-1,-.143)]:
        for k in range(3):a=2*math.pi*k/3;petal('Tassel lotus cap',(.001*math.sin(a),-.006,z),math.sin(a),sign,.013,.003,silverlight)
    for k in range(84):
        a=k*math.tau/84;r=.006*math.sqrt((k%11+1)/11);tip=.252+rng.uniform(-.004,.004)
        pts=[(r*math.cos(a),r*math.sin(a),-.149),((r+.004)*math.cos(a),(r+.004)*math.sin(a),-.20),((r+.008)*math.cos(a),(r+.008)*math.sin(a),-tip)]
        rib('White silk filament',pts,.00024,silk)
    tassel=join_group('Caiheng_Tassel',list(set(bpy.data.objects)-start));tassel['prop_kind']='tassel'
    sword['canonical_length_note']='Blade 2 chi 5 cun; 1 chi = 1/3 m remains a provisional conversion.'
    for o in [sword,sheath,tassel]:o['visual_authority']='Eight user-provided weapon images; differs from earlier undecorated text description.'
    # Scene arrangement is separate from export pivots.
    sheath.location.x=.21;tassel.location=(.08,0,-.22)
    return [sword,sheath,tassel]

def export_props(out):
    out=Path(out);objects=[o for o in bpy.context.scene.objects if o.get('part')=='caiheng_prop' and o.get('variant')=='image_reference']
    for o in objects:
        old=o.matrix_world.copy();o.matrix_world=Matrix.Identity(4)
        bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.export_scene.fbx(filepath=str(out/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY')
        bpy.ops.export_scene.gltf(filepath=str(out/(o.name+'.glb')),use_selection=True,export_format='GLB',export_animations=False)
        o.matrix_world=old
    return objects
