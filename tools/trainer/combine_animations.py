import bpy,re
from pathlib import Path
root=Path.cwd(); bpy.ops.wm.open_mainfile(filepath=str(root/'artifacts/trainer/trainer-custom-exercises.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); prefix=rig.data.bones[0].name.split(':')[0]
for filename,name in [('Breathing Idle.fbx','Idle'),('Air Squat.fbx','Squats'),('Push Up.fbx','PushUps'),('Bicep Curl.fbx','BicepsCurl')]:
 before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=str(root/'frontend/public/models'/filename)); added=set(bpy.data.objects)-before; source=next(o for o in added if o.type=='ARMATURE')
 # The supplied clips must have identical rest skeletons before transferring channels.
 for bone in source.data.bones:
  target=rig.data.bones.get(prefix+':'+bone.name.split(':')[-1]); assert target is not None, bone.name
  assert (target.head_local-bone.head_local).length<.1, 'Incompatible rig '+name
 action=source.animation_data.action; action.name=name; action.use_fake_user=True
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves: fc.data_path=re.sub(r'mixamorig\d*:',prefix+':',fc.data_path)
 for obj in added: bpy.data.objects.remove(obj,do_unlink=True)
rig.animation_data.action=bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
# Only the original optimized character is exported, with all compatible actions.
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
 if obj.type in ('MESH','ARMATURE'): obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(root/'frontend/public/models/trainer/trainer.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_image_format='JPEG',export_jpeg_quality=85)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'artifacts/trainer/trainer-all-exercises.blend'))
print('COMBINED_OK')
