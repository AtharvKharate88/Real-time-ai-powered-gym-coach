import bpy
from pathlib import Path
root=Path.cwd();bpy.ops.wm.open_mainfile(filepath=str(root/'artifacts/trainer/trainer-all-exercises.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for t in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(t)
a=bpy.data.actions['Idle'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(1)
for img in bpy.data.images:
 if img.type=='IMAGE' and img.size[0]>1024:
  w,h=img.size[:];s=1024/max(w,h);img.scale(max(1,int(w*s)),max(1,int(h*s)))
bpy.ops.export_scene.gltf(filepath=str(root/'frontend/public/models/trainer/trainer.glb'),export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_image_format='JPEG',export_jpeg_quality=72,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,export_draco_position_quantization=14)
