# Regeneration pipeline

Converts a Gazebo world (three static model dirs) into the self-contained
web viewer in this repo.

Input layout: a `<world_dir>` containing `walls_7f/`, `doors_7f/` (box-link
models: `model.sdf` with `<link><pose>` + `<visual><geometry><box>`), and
`floor_7f/` (textured-OBJ floor model with `albedo_map` PNGs).

1. `blender -b -P sdf_to_glb.py -- <world_dir> floor7f.glb`
2. `npm i three esbuild` (once), then
   `esbuild app.js --bundle --minify --format=iife --outfile=bundle.min.js`
3. `python3 build_html.py` -> `floor7f_viewer.html` (standalone full page)
4. Copy `floor7f_viewer.html` -> `index.html` here (keep the favicon link),
   plus the new `floor7f.glb`, commit & push.
