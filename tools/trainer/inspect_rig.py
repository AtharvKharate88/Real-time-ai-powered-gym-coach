import bpy,json
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(Path('frontend/public/models/Breathing Idle.fbx').resolve()))
for o in bpy.data.objects:
 if o.type=='ARMATURE':
  print('RIG',o.name,'scale',list(o.scale))
  for b in o.data.bones: print('BONE',b.name,'head',list(b.head_local),'tail',list(b.tail_local))
print('MESHES',[(o.name,len(o.data.vertices)) for o in bpy.data.objects if o.type=='MESH'])
print('ACTIONS',[(a.name,list(a.frame_range)) for a in bpy.data.actions])
bpy.ops.wm.save_as_mainfile(filepath=str(Path('artifacts/trainer/source-inspection.blend').resolve()))
