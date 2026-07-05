#!/usr/bin/env python3
"""Assemble the self-contained 7F viewer:
  - viewer_artifact.html  (content fragment for the claude.ai Artifact)
  - floor7f_viewer.html   (standalone full document — share the file itself)
Everything inline: CSS, bundled three.js app, GLB as base64."""
import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, "..", "floor7f.glb")

glb_b64 = base64.b64encode(open(GLB, "rb").read()).decode()
bundle = open(os.path.join(HERE, "bundle.min.js")).read()

BODY = """<style>
  :root {
    --ground: #eef0f3;
    --panel: rgba(23, 28, 34, 0.9);
    --panel-line: rgba(255, 255, 255, 0.08);
    --ink: #e9edf2;
    --ink-dim: #9aa4b0;
    --accent: #3d8b6d;
    --walnut: #8b6a4f;
    --grass: #5d8f4a;
    --glass: #7fa8c9;
  }
  html, body { margin: 0; height: 100%; background: var(--ground); }
  #wrap {
    position: relative; width: 100%; height: 100dvh; overflow: hidden;
    font-family: "Pretendard Variable", Pretendard, "Apple SD Gothic Neo",
                 "Noto Sans KR", system-ui, sans-serif;
  }
  #stage { position: absolute; inset: 0; }
  #stage canvas { display: block; }

  #bar {
    position: absolute; top: 16px; left: 16px; right: 16px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; pointer-events: none;
  }
  .card {
    background: var(--panel); color: var(--ink);
    border: 1px solid var(--panel-line); border-radius: 10px;
    backdrop-filter: blur(6px); pointer-events: auto;
  }
  #title { padding: 10px 16px; }
  #title h1 { margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -0.01em; }
  #title p {
    margin: 2px 0 0; font-size: 11px; color: var(--ink-dim);
    text-transform: uppercase; letter-spacing: 0.08em;
  }
  #views { display: flex; gap: 4px; padding: 4px; }
  #views button {
    font: inherit; font-size: 12.5px; color: var(--ink);
    background: transparent; border: 0; border-radius: 7px;
    padding: 7px 12px; cursor: pointer;
  }
  #views button:hover { background: rgba(255, 255, 255, 0.09); }
  #views button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

  #legend {
    position: absolute; left: 16px; bottom: 16px;
    display: flex; gap: 6px; flex-wrap: wrap; max-width: calc(100% - 32px);
  }
  .chip {
    display: flex; align-items: center; gap: 7px;
    padding: 6px 11px; font-size: 12px;
  }
  .dot { width: 9px; height: 9px; border-radius: 50%; }

  #hint {
    position: absolute; right: 16px; bottom: 16px;
    padding: 6px 11px; font-size: 11.5px; color: var(--ink-dim);
  }

  #loading {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 14px;
    background: var(--ground); z-index: 5; color: #4a545f;
  }
  #loading .pulse {
    width: 34px; height: 34px; border-radius: 50%;
    border: 3px solid #c9cfd6; border-top-color: var(--accent);
    animation: spin 0.9s linear infinite;
  }
  #loading .msg { font-size: 13px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    #loading .pulse { animation: none; border-top-color: #c9cfd6; }
  }
  @media (max-width: 640px) {
    #title p { display: none; }
    #hint { display: none; }
  }
</style>

<div id="wrap">
  <div id="stage" aria-label="7F 3D 모델 뷰"></div>

  <div id="bar">
    <div id="title" class="card">
      <h1>판교 스타트업캠퍼스 1동 7F — 디지털 트윈</h1>
      <p>Gazebo world &middot; rev 4fe6291 &middot; 2026-07-05</p>
    </div>
    <div id="views" class="card" role="group" aria-label="시점 선택">
      <button id="btn-oblique" type="button">사선 보기</button>
      <button id="btn-top" type="button">위에서 보기</button>
    </div>
  </div>

  <div id="legend">
    <div class="chip card"><span class="dot" style="background: var(--grass)"></span>잔디 정원</div>
    <div class="chip card"><span class="dot" style="background: var(--walnut)"></span>월넛 라운지</div>
    <div class="chip card"><span class="dot" style="background: var(--glass)"></span>유리문 (반투명)</div>
  </div>

  <div id="hint" class="card">드래그 회전 &middot; 휠 줌 &middot; 우클릭 이동</div>

  <div id="loading">
    <div class="pulse" aria-hidden="true"></div>
    <div class="msg">7층 모델 불러오는 중… (약 2 MB)</div>
  </div>
</div>

<script>window.GLB_B64 = "__GLB__";</script>
<script>__BUNDLE__</script>
"""

# a literal "</script" inside the bundle would terminate the inline script tag;
# escaping it as "<\/script" is semantically identical inside JS strings/regex
# (base64 cannot contain "<", so the GLB payload needs no such treatment)
bundle = bundle.replace("</script", "<\\/script")
body = BODY.replace("__GLB__", glb_b64).replace("__BUNDLE__", bundle)

frag = "<title>7F 디지털 트윈 뷰어</title>\n" + body
open(os.path.join(HERE, "viewer_artifact.html"), "w").write(frag)

standalone = ("<!doctype html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
              "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
              "<title>판교 스타트업캠퍼스 7F — 디지털 트윈 뷰어</title>\n</head>\n<body>\n"
              + body + "\n</body>\n</html>\n")
open(os.path.join(HERE, "floor7f_viewer.html"), "w").write(standalone)

print("artifact fragment:", len(frag) // 1024, "KB | standalone:",
      len(standalone) // 1024, "KB")
