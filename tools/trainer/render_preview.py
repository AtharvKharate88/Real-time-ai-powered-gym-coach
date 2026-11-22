import bpy
from pathlib import Path
from mathutils import Vector
root=Path.cwd(); out=root/'artifacts/trainer'
bpy.ops.wm.open_mainfile(filepath=str(out/'trainer-custom-exercises.blend'))
scene=bpy.context.scene
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
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
