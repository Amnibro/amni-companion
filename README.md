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
- `art/` holds the stock character concepts and the two CC0 base bodies (`art/ubc/`). `tools/image3d.py` turns one concept image into a rigged, textured companion (see below).

```bash
tools/build.sh   # rebuild core/*.amni from Gold (if installed) and web/companion.wasm
tools/test.sh    # build and run the core tests natively, then rebuild the wasm
tools/stock.sh   # rebuild Holo and Dex with tools/character.sh
```

## Make your own companion from concept art

`tools/character.sh` turns one front-view, full-body concept image into a rigged and textured companion. Generate it with Amni-Gen, or any SDXL, Qwen or similar image model: a T-pose or wide A-pose on a plain background works best. A transparent cutout also works.

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
tools/character.sh nova nova_concept.png female 1.68   # id, image, female|male, height in meters
```

It takes about 20 seconds and needs no 3D generator. What happens:

1. **Read the picture.** MediaPipe finds the body pose, the face landmarks, and which pixels are hair, skin, face and clothes. A plain background is cut out automatically.
2. **Fit a real body.** A CC0 base body from Quaternius (full skeleton with finger bones, clean shoulders, elbows and hands) is posed and proportioned to the concept, then widened or slimmed slice by slice until its outline matches. Limbs stay round, and the posture stays upright.
3. **Fit the face.** The template face keeps its real depth (brow, nose, lips, chin) while its features move onto the concept's landmarks, so it holds up in profile and when the head turns.
4. **Add hair and skirts.** Hair becomes a sculpted volume grown from the concept's hair outline and the scalp. A skirt or dress becomes a pleated tube sized row by row from the outline. Both get their own bones, so arms and legs don't drag them.
5. **Paint it.** The concept is projected onto everything the front view shows. The back and sides are filled from the same part, never across parts, so no face on the back of the head and no skirt plaid on legs.

The analysis runs in headless Chromium through `tools/analyze.mjs`: set `PW` to a folder whose `node_modules` has `playwright-core`, and `CHROME` to a Chromium or headless-shell binary. The first run downloads two MediaPipe models (Apache-2.0) to `~/.cache/amni-companion/mediapipe`.

Limits: the back is inferred from the front, loose garments other than skirts and dresses (capes, big coats) follow the body, and hands, glasses and jewelry are painted rather than modeled.

## License

Amni-Companion is free software under the [GNU Affero General Public License v3.0](./LICENSE). If you run a modified version for others over a network, you must offer them its source. Third-party components keep their own licenses; see [NOTICE.md](./NOTICE.md).
