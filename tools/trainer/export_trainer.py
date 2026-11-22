import bpy
from pathlib import Path
root=Path.cwd();bpy.ops.wm.open_mainfile(filepath=str(root/'artifacts/trainer/trainer-all-exercises.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for a in bpy.data.actions: print('ACTION',a.name, a.frame_range[:],[(s.identifier,s.target_id_type) for s in a.slots])
# Export NLA tracks with explicit slot binding for every action.
rig.animation_data.action=None
for track in list(rig.animation_data.nla_tracks): rig.animation_data.nla_tracks.remove(track)
for action in bpy.data.actions:
 t=rig.animation_data.nla_tracks.new();t.name=action.name
 strip=t.strips.new(action.name,0,action);strip.action_slot=action.slots[0]
 t.mute=True
bpy.ops.export_scene.gltf(filepath=str(root/'frontend/public/models/trainer/trainer.glb'),export_format='GLB',export_animations=True,export_animation_mode='NLA_TRACKS',export_image_format='JPEG',export_jpeg_quality=85)
