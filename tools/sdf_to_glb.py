# Blender headless script: convert the 7F Gazebo world (3 static model SDFs)
# into one GLB. Boxes come from walls_7f/doors_7f link poses+sizes; meshes and
# textures from floor_7f OBJs. Boxes are merged per material to keep draw
# calls low. Run: blender -b -P sdf_to_glb.py -- <out.glb>
import math
import os
import sys
import xml.etree.ElementTree as ET

import bpy

WORLD = "/home/neoplanetz/Documents/codes/7f_gazebo_handoff/world"
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/floor7f.glb"

# ---------- clean scene ----------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for x in list(block):
        block.remove(x)

_mats = {}


def box_material(diffuse, transparency):
    """One shared material per (rgba, transparency) so boxes can merge."""
    key = (tuple(round(v, 3) for v in diffuse), round(transparency, 2))
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"m_{len(_mats)}")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    r, g, b = diffuse[:3]
    alpha = 1.0 - transparency
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Alpha"].default_value = alpha
    if transparency > 0.0:
        m.blend_method = "BLEND"
    _mats[key] = m
    return m


def tex_material(name, png_path, roughness):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(png_path)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def parse_links(sdf_path):
    """Yield (name, pose6, size3, diffuse_rgba, transparency) per box link."""
    root = ET.parse(sdf_path).getroot()
    for link in root.iter("link"):
        pose = [float(v) for v in (link.findtext("pose") or "0 0 0 0 0 0").split()]
        vis = link.find("visual")
        if vis is None:
            continue
        box = vis.find("./geometry/box/size")
        if box is None:
            continue
        size = [float(v) for v in box.text.split()]
        tr = float(vis.findtext("transparency") or "0")
        dif = [float(v) for v in (vis.findtext("./material/diffuse") or "1 1 1 1").split()]
        yield link.get("name"), pose, size, dif, tr


def add_boxes(sdf_path, prefix):
    groups = {}
    for name, pose, size, dif, tr in parse_links(sdf_path):
        mat = box_material(dif, tr)
        bpy.ops.mesh.primitive_cube_add(size=1)
        ob = bpy.context.active_object
        ob.name = f"{prefix}_{name}"
        ob.scale = size
        ob.location = pose[:3]
        ob.rotation_mode = "XYZ"          # matches SDF fixed-axis RPY
        ob.rotation_euler = pose[3:6]
        ob.data.materials.append(mat)
        groups.setdefault(mat.name, []).append(ob)
    # merge per material: hundreds of boxes -> a handful of draw calls
    merged = []
    for mat_name, obs in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for ob in obs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = f"{prefix}_{mat_name}"
        merged.append(joined)
    return merged


def add_floor_meshes():
    """floor_7f: OBJ meshes (already world-coordinate, Z-up) + PNG albedos."""
    pkg = os.path.join(WORLD, "floor_7f")
    root = ET.parse(os.path.join(pkg, "model.sdf")).getroot()
    for link in root.iter("link"):
        vis = link.find("visual")
        if vis is None:
            continue
        uri = vis.findtext("./geometry/mesh/uri")
        if not uri:
            continue
        albedo = vis.findtext(".//albedo_map")
        rough = float(vis.findtext(".//roughness") or "0.8")
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=os.path.join(pkg, uri),
                              forward_axis="Y", up_axis="Z")
        for ob in set(bpy.data.objects) - before:
            ob.name = f"floor_{link.get('name')}"
            m = tex_material(f"tex_{link.get('name')}", os.path.join(pkg, albedo), rough)
            ob.data.materials.clear()
            ob.data.materials.append(m)


add_boxes(os.path.join(WORLD, "walls_7f", "model.sdf"), "walls")
add_boxes(os.path.join(WORLD, "doors_7f", "model.sdf"), "doors")
add_floor_meshes()

bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True,
                          export_apply=True)
print("GLB written:", OUT, os.path.getsize(OUT), "bytes")
print("objects:", len(bpy.data.objects), "materials:", len(bpy.data.materials))
