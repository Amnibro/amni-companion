# Amni-Companion

**A 3D AI companion that lives in your browser.** Bring your own model and your own AI key, talk to it by voice or text, and see it standing over your camera or in your room with body tracking and gesture recognition. Everything runs on your device.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](./LICENSE)

| | |
|---|---|
| **Try it** | https://amni-scient.com/companion/ |
| **About** | https://amni-scient.com/amni-companion.html |
| **Install** | Open the app, then use your browser's *Install app* or *Add to Home Screen* (works offline afterward) |
| **License** | AGPL-3.0 |

## Features

- **Stock companions.** Holo (bubbly, punk-pop) and Dex (calm engineer, dry wit), modeled with Amni-CAD, plus a plain mannequin.
- **Bring your own model.** Drop in any rigged humanoid `.glb` or `.vrm`: Mixamo, VRoid (VRM 0.x and 1.0, including node constraints), Ready Player Me, Unreal, Blender Rigify and Amni-CAD rigs. The skeleton is matched automatically, and the built-in animation library is retargeted onto it. Models stay in your browser (IndexedDB).
- **Bring your own brain.** Claude, OpenAI, Grok, Gemini, OpenRouter, Ollama, LM Studio or any OpenAI-compatible endpoint, called directly from your browser with your own key. A small offline brain works with no key and no network.
- **It moves when it talks.** Replies can carry tags like `[[emote:wave]]`, `[[anim:dance]]`, `[[walk:user]]`, `[[look:left]]` and `[[face:smile]]`, so the companion waves, dances, walks over, looks around and changes expression.
- **Camera AR with body tracking.** The companion stands over your camera feed and can mirror your body like a reflection.
- **It notices you.** On-device recognition of waves, claps, hands up, pointing, crossed arms, T-poses, approaching and backing away; hand signs (thumbs up and down, peace, love, fist, open palm, pointing up); smiles, surprise, frowns, winks, nods and head shakes; and everyday objects you hold up. It reacts out loud if you let it.
- **Room AR.** On WebXR-capable phones and headsets, place the companion on your floor and have it walk to you.
- **Voice.** Speech recognition and synthesis through the browser, with on-device recognition where the browser supports it.
- **Private by design.** No accounts, no servers, no analytics. Settings, keys, models and conversation history live only in your browser, and **Erase everything** wipes them.

## Run it locally

The app is static files. Serve the `web/` folder over HTTP:

```bash
tools/serve.sh            # http://127.0.0.1:7437
```

Camera, microphone and WebXR need a secure context: `localhost` works, and other hosts need HTTPS.

## Bring your own model

Your model needs a humanoid skeleton (hips, spine, neck, head, arms and legs). Bone names are matched by meaning, not by an exact list, so `mixamorig:LeftArm`, `J_Bip_L_UpperArm`, `DEF-upper_arm.L`, `upperarm_l` and `Left arm` all work. The Models panel shows how many of the 22 body parts it found. Blend shapes named like `mouthOpen`, `aa`, `blink`, `smile` or `surprised` (VRM and ARKit names included) drive talking, blinking and expressions.

## AI brains

Open **AI brain**, pick a service and paste your key. The key is stored in this browser and sent only to that service.

| Service | Notes |
|---|---|
| Claude | Defaults to `claude-opus-5-5` with low effort; browser access is enabled with Anthropic's direct-browser-access header |
| OpenAI, Grok, Gemini, OpenRouter | If a service blocks browser requests, use OpenRouter with the same model |
| Ollama | Start Ollama with `OLLAMA_ORIGINS` set to the app's origin |
| LM Studio | Turn on CORS in the server settings |
| Other | Any OpenAI-compatible `/chat/completions` endpoint |

When the camera is on and you ask what it sees, the connected brain gets a single snapshot. Nothing else leaves your device.

## How it is built

- `core/` is the companion's core, written in **Gold** (plain English specs) and compiled to checked **Helium**, then to WebAssembly (`web/companion.wasm`). It does the skeleton matching, motion retargeting, the pose solver behind look-at and emotes, body-tracking filtering and solving, gesture and expression recognition, reply-tag parsing and the offline brain.
- `web/` is the shell: three.js rendering, MediaPipe Tasks vision models (pose, hands and gestures, face, objects), Web Speech, WebXR, and the panels.
- `art/` holds the stock character concepts and the body and face templates. `tools/reskin.py` rigs a humanoid GLB: it fills the mesh into voxels, centers the limb joints in the limbs, and weights each vertex by geodesic distance through the body, so hair and skirts don't follow the arms and legs.

```bash
tools/build.sh   # rebuild core/*.amni from Gold (if installed) and web/companion.wasm
tools/test.sh    # build and run the core tests natively, then rebuild the wasm
tools/stock.sh   # rebuild Holo and Dex with tools/character.sh
```

## Make your own companion from concept art

`tools/character.sh` turns a front-view concept image, plus a TRELLIS mesh generated from it, into a rigged and textured companion in one command:

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
FACE=1 HAIR=1 tools/character.sh nova nova_trellis.glb nova_concept.png female 1.68
```

Each step is also a `tools/reskin.py` command you can run on its own:

1. **Base mesh and skeleton.** 70,000 triangles with an auto-rig from Mosaic and Amni-CAD, or pass `RIG=` a rigged GLB of the same mesh.
2. **Proportions** (`--graft`). Rigs the mesh, then scales each bone toward the CC0 Universal Base Characters template, so the head, torso, arms and legs land in human ratios.
3. **Face depth** (`--face`, on with `FACE=1`). Finds the face with MediaPipe and gives it the template's depth (eye sockets, nose, cheekbones, chin) while keeping every vertex's front-view position, so painted features stay where they are.
4. **Hair clearance** (`--hairback`, on with `HAIR=1`). Moves long hair behind the shoulders and frees it from the arm bones, so arms don't pass through it.
5. **Texture** (`--rebake`). Builds a new overlap-free UV atlas, projects the concept art onto everything visible from the front (warped to fit with optical flow), and fills the sides and back with the TRELLIS colors matched to the concept.

The face step renders landmarks in headless Chromium through `tools/marks.mjs`: set `PW` to a folder whose `node_modules` has `playwright-core`, and `CHROME` to a Chromium or headless-shell binary.

## License

Amni-Companion is free software under the [GNU Affero General Public License v3.0](./LICENSE). If you run a modified version for others over a network, you must offer them its source. Third-party components keep their own licenses; see [NOTICE.md](./NOTICE.md).
