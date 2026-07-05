# Blender headless script: convert a Gazebo world's static model SDFs
# (walls_7f / doors_7f box links + floor_7f textured OBJ meshes) into one GLB.
# Boxes are merged per material to keep draw calls low.
#
# Run: blender -b -P sdf_to_glb.py -- <world_dir> <out.glb>
#   <world_dir> must contain walls_7f/, doors_7f/, floor_7f/ model dirs.
#
# Codex review round (2026-07-05): multi-visual links, visual-level <pose>
# composition, field validation with SDF context, and CLI-provided world dir
# (no hardcoded workstation path).
import os
import sys
import xml.etree.ElementTree as ET

import bpy
from mathutils import Euler, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) != 2:
    raise SystemExit("usage: blender -b -P sdf_to_glb.py -- <world_dir> <out.glb>")
WORLD, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])

# ---------- clean scene ----------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for x in list(block):
        block.remove(x)

_mats = {}


def _floats(text, n, ctx):
    """Parse exactly n floats, failing with the SDF location on bad input."""
    vals = [float(v) for v in (text or "").split()]
    if len(vals) != n:
        raise ValueError(f"{ctx}: expected {n} floats, got {text!r}")
    return vals


def _pose6(text, ctx):
    return _floats(text or "0 0 0 0 0 0", 6, ctx)


def _pose_matrix(p6):
    """SDF pose (fixed-axis RPY == Blender euler XYZ) as a 4x4."""
    return (Matrix.Translation(p6[:3])
            @ Euler(p6[3:6], "XYZ").to_matrix().to_4x4())


def box_material(diffuse, transparency):
    """One shared material per (rgba, transparency) so boxes can merge."""
    key = (tuple(round(v, 3) for v in diffuse), round(transparency, 2))
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"m_{len(_mats)}")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    r, g, b = diffuse[:3]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Alpha"].default_value = 1.0 - transparency
    if transparency > 0.0:
        m.blend_method = "BLEND"
    _mats[key] = m
    return m


def tex_material(name, png_path, roughness, ctx):
    if not os.path.isfile(png_path):
        raise ValueError(f"{ctx}: albedo_map not found: {png_path}")
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


def iter_visuals(sdf_path):
    """Yield (link_name, visual_name, world_matrix, visual_el) for EVERY visual
    (a link may carry several; visual <pose> composes onto the link pose)."""
    root = ET.parse(sdf_path).getroot()
    base = os.path.basename(sdf_path)
    for link in root.iter("link"):
        lname = link.get("name") or "?"
        lp = _pose6(link.findtext("pose"), f"{base}:{lname}/pose")
        visuals = link.findall("visual")
        for i, vis in enumerate(visuals):
            vname = vis.get("name") or f"v{i}"
            ctx = f"{base}:{lname}/{vname}"
            vpose_text = vis.findtext("pose")
            if vpose_text is None:
                # common case: visual at the link frame -> exact link pose values
                yield lname, (vname if len(visuals) > 1 else ""), lp, None, vis, ctx
            else:
                vp = _pose6(vpose_text, f"{ctx}/pose")
                wmat = _pose_matrix(lp) @ _pose_matrix(vp)
                yield lname, (vname if len(visuals) > 1 else ""), None, wmat, vis, ctx


def add_boxes(sdf_path, prefix):
    groups = {}
    skipped = []
    for lname, vsuffix, p6, wmat, vis, ctx in iter_visuals(sdf_path):
        box = vis.find("./geometry/box/size")
        if box is None:
            skipped.append(ctx)
            continue
        size = _floats(box.text, 3, f"{ctx}/box/size")
        tr = float(vis.findtext("transparency") or "0")
        dif = _floats(vis.findtext("./material/diffuse") or "1 1 1 1", 4,
                      f"{ctx}/material/diffuse")
        mat = box_material(dif, tr)
        bpy.ops.mesh.primitive_cube_add(size=1)
        ob = bpy.context.active_object
        ob.name = f"{prefix}_{lname}{('_' + vsuffix) if vsuffix else ''}"
        if p6 is not None:
            ob.location = p6[:3]
            ob.rotation_mode = "XYZ"          # matches SDF fixed-axis RPY
            ob.rotation_euler = p6[3:6]
        else:
            ob.matrix_world = wmat            # composed link @ visual pose
        ob.scale = size
        ob.data.materials.append(mat)
        groups.setdefault(mat.name, []).append(ob)
    if skipped:
        print(f"WARNING {prefix}: {len(skipped)} non-box visual(s) skipped:",
              ", ".join(skipped))
    # merge per material: hundreds of boxes -> a handful of draw calls
    for mat_name, obs in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for ob in obs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.object.join()
        bpy.context.active_object.name = f"{prefix}_{mat_name}"


def add_floor_meshes(pkg):
    """floor model: OBJ meshes (world-coordinate, Z-up) + PNG albedo textures."""
    sdf_path = os.path.join(pkg, "model.sdf")
    for lname, vsuffix, p6, wmat, vis, ctx in iter_visuals(sdf_path):
        uri = vis.findtext("./geometry/mesh/uri")
        if not uri:
            continue
        albedo = vis.findtext(".//albedo_map")
        if not albedo:
            raise ValueError(f"{ctx}: mesh visual without albedo_map")
        rough = float(vis.findtext(".//roughness") or "0.8")
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=os.path.join(pkg, uri),
                              forward_axis="Y", up_axis="Z")
        identity = p6 is not None and all(abs(v) < 1e-12 for v in p6)
        for ob in set(bpy.data.objects) - before:
            ob.name = f"floor_{lname}{('_' + vsuffix) if vsuffix else ''}"
            if not identity:
                m4 = _pose_matrix(p6) if p6 is not None else wmat
                ob.matrix_world = m4 @ ob.matrix_world
            m = tex_material(f"tex_{lname}{('_' + vsuffix) if vsuffix else ''}",
                             os.path.join(pkg, albedo), rough, ctx)
            ob.data.materials.clear()
            ob.data.materials.append(m)


add_boxes(os.path.join(WORLD, "walls_7f", "model.sdf"), "walls")
add_boxes(os.path.join(WORLD, "doors_7f", "model.sdf"), "doors")
add_floor_meshes(os.path.join(WORLD, "floor_7f"))

bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True,
                          export_apply=True)
print("GLB written:", OUT, os.path.getsize(OUT), "bytes")
print("objects:", len(bpy.data.objects), "materials:", len(bpy.data.materials))
