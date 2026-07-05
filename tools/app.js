// 7F digital-twin web viewer: loads the GLB embedded as base64 (window.GLB_B64),
// renders with three.js, orbit navigation + two view presets.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const GROUND = 0xeef0f3;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const app = document.getElementById("stage");
const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
// log depth: the floor overlays sit 1.5-2.5 mm above the terrazzo; a linear
// buffer with near=0.1 z-fights them beyond ~40 m viewing distance.
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = false;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(GROUND);

const camera = new THREE.PerspectiveCamera(50, 1, 0.8, 1200);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = !reduced;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI / 2 - 0.02;   // never dip below the floor
controls.minDistance = 3;

const hemi = new THREE.HemisphereLight(0xffffff, 0xb8bcc4, 1.05);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.castShadow = false;
scene.add(sun);

let bounds = null;

function frame(view) {
  if (!bounds) return;
  const c = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const span = Math.max(size.x, size.z);
  if (view === "top") {
    camera.position.set(c.x, c.y + span * 1.15, c.z + 0.001);
  } else {
    camera.position.set(c.x - span * 0.18, c.y + span * 0.62, c.z + span * 0.6);
  }
  controls.target.copy(c);
  controls.update();
}

function b64ToBuf(b64) {
  const bin = atob(b64);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return buf.buffer;
}

new GLTFLoader().parse(b64ToBuf(window.GLB_B64), "", (gltf) => {
  const root = gltf.scene;
  root.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      if (o.material && o.material.transparent) o.castShadow = false; // glass
    }
  });
  scene.add(root);
  bounds = new THREE.Box3().setFromObject(root);
  const c = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const span = Math.max(size.x, size.z);
  sun.position.set(c.x - span * 0.35, c.y + span * 0.9, c.z + span * 0.25);
  sun.target.position.copy(c);
  scene.add(sun.target);
  const s = sun.shadow;
  s.mapSize.set(4096, 4096);
  s.camera.left = s.camera.bottom = -span * 0.75;
  s.camera.right = s.camera.top = span * 0.75;
  s.camera.far = span * 3;
  s.bias = -0.0001;
  s.normalBias = 0.05;      // kills the acne diamond on the flat grass bed
  frame("oblique");
  document.getElementById("loading").remove();
}, (err) => {
  document.querySelector("#loading .msg").textContent =
    "모델을 불러오지 못했습니다 — 브라우저를 새로고침해 주세요.";
  console.error(err);
});

function resize() {
  const w = app.clientWidth, h = app.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

document.getElementById("btn-oblique").addEventListener("click", () => frame("oblique"));
document.getElementById("btn-top").addEventListener("click", () => frame("top"));

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});

window.__v = { camera, controls, renderer };  // scripted-view hook for QA
