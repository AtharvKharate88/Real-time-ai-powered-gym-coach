import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
root=Path.cwd(); out=root/'artifacts/trainer'; web=root/'frontend/public/models/trainer'; web.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(out/'source-inspection.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); rig.animation_data_clear()
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
bones={b.name.split(':')[-1]:b for b in rig.pose.bones}
rest={n:b.bone.matrix_local.copy() for n,b in bones.items()}
scene=bpy.context.scene; scene.render.fps=30

def aim(n,d):
 b=bones[n]; bpy.context.view_layer.update(); m=b.matrix.copy(); q=(m.to_3x3()@Vector((0,1,0))).rotation_difference(Vector(d).normalized()); b.matrix=Matrix.Translation(m.translation)@q.to_matrix().to_4x4()@m.to_quaternion().to_matrix().to_4x4(); bpy.context.view_layer.update()
def two(upper,lower,target,pole):
 bpy.context.view_layer.update(); a=bones[upper].head.copy(); target=Vector(target); v=target-a; length=v.length; u=v.normalized()
 l1=(rest[lower].translation-rest[upper].translation).length
 end='LeftFoot' if lower=='LeftLeg' else 'RightFoot' if lower=='RightLeg' else lower.replace('ForeArm','Hand')
 l2=(rest[end].translation-rest[lower].translation).length
 length=min(length,l1+l2-.2); target=a+u*length
 along=(l1*l1-l2*l2+length*length)/(2*length); height=math.sqrt(max(0,l1*l1-along*along)); p=Vector(pole); perpendicular=(p-u*p.dot(u)).normalized(); knee=a+along*u+height*perpendicular
 aim(upper,knee-a); aim(lower,target-bones[lower].head)
def reset():
 for b in bones.values(): b.matrix_basis=Matrix.Identity(4); b.rotation_mode='QUATERNION'
 bpy.context.view_layer.update()
def arms_down():
 for side,sign in [('Left',1),('Right',-1)]:
  aim(side+'Arm',(sign*.16,-1,.08)); aim(side+'ForeArm',(sign*.05,-1,.05))
def pose(kind,t):
 reset()
 if kind=='ShoulderPress':
  amount=(1-math.cos(2*math.pi*t))/2
  for side,sign in [('Left',1),('Right',-1)]:
   shoulder=bones[side+'Arm'].head.copy(); target=shoulder+Vector((sign*(27-21*amount),16+31*amount,8))
   two(side+'Arm',side+'ForeArm',target,(sign,0,0))
   aim(side+'Hand',(0,1,0))
 else:
  # One controlled forward lunge per side, with planted endpoints while lowering.
  cycle=t*2; side_index=min(1,int(cycle)); u=cycle-side_index
  def smooth(v): v=max(0,min(1,v)); return v*v*(3-2*v)
  stride=smooth(u/.23) if u<.23 else 1 if u<.77 else 1-smooth((u-.77)/.23)
  depth=smooth((u-.23)/.22) if u<.45 else 1 if u<.55 else 1-smooth((u-.55)/.22)
  hips=bones['Hips']; m=hips.matrix.copy(); m.translation+=Vector((0,-25*depth,7*stride)); hips.matrix=m; bpy.context.view_layer.update()
  for side,index in [('Left',0),('Right',1)]:
   forward=index==side_index; ankle=rest[side+'Foot'].translation.copy(); ankle.z+=(43 if forward else -28)*stride
   if forward and (u<.23 or u>.77): ankle.y+=7*math.sin(math.pi*(u/.23 if u<.23 else (1-u)/.23))
   if not forward: ankle.y+=5*depth
   two(side+'UpLeg',side+'Leg',ankle,(0,0,1))
   foot=bones[side+'Foot']; foot.matrix=Matrix.Translation(foot.head)@rest[side+'Foot'].to_quaternion().to_matrix().to_4x4()
  arms_down()
 bpy.context.view_layer.update()
for name,duration in [('ShoulderPress',120),('AlternatingLunges',240)]:
 action=bpy.data.actions.new(name); action.use_fake_user=True; rig.animation_data_create(); rig.animation_data.action=action
 for f in range(duration+1):
  scene.frame_set(f); pose(name,f/duration)
  for b in bones.values():
   b.keyframe_insert('location',frame=f,group=b.name); b.keyframe_insert('rotation_quaternion',frame=f,group=b.name)
 print('CREATED',name)
# Reduce texture transfer size without changing source files.
for img in bpy.data.images:
 if img.size[0]>1024 or img.size[1]>1024:
  ratio=1024/max(img.size); img.scale(max(1,int(img.size[0]*ratio)),max(1,int(img.size[1]*ratio)))
rig.animation_data.action=bpy.data.actions['ShoulderPress']; scene.frame_start=0;scene.frame_end=240;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'trainer-custom-exercises.blend'))
bpy.ops.export_scene.gltf(filepath=str(web/'trainer-custom-exercises.glb'),export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_image_format='JPEG',export_jpeg_quality=85)
# Neutral studio previews, frontal three-quarter view.
scene.render.engine='CYCLES'; scene.cycles.samples=12; scene.render.resolution_x=480;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.world = bpy.data.worlds.new("Preview world")
scene.world.color=(.18,.18,.18)
bpy.ops.object.camera_add(location=(2.7,-4.3,2.1)); camera=bpy.context.object; camera.rotation_euler=(Vector((0,0,.95))-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.type='ORTHO';camera.data.ortho_scale=2.5;scene.camera=camera
for loc,power,size in [((2,-3,4),600,4),((-3,-1,2),400,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc); light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
for name,frames in [('ShoulderPress',[0,30,60]),('AlternatingLunges',[0,60,180])]:
 rig.animation_data.action=bpy.data.actions[name]
 for f in frames:
  scene.frame_set(f); scene.render.filepath=str(out/f'{name}-{f}.png');bpy.ops.render.render(write_still=True)
print('DONE')
