# Regeneration pipeline (run on the workstation with the private world repo)

1. `blender -b -P sdf_to_glb.py -- /path/out/floor7f.glb`
   (reads the three model SDFs under the private repo's `world/`)
2. `npm i three esbuild` (once), then
   `esbuild app.js --bundle --minify --format=iife --outfile=bundle.min.js`
3. `python3 build_html.py` -> `floor7f_viewer.html` (standalone) + artifact fragment
4. Copy `floor7f_viewer.html` -> `index.html` here, plus the new `floor7f.glb`, commit & push.
