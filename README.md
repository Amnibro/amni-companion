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

- **Stock companions.** Holo (bubbly, punk-pop, 5'2") and Dex (calm engineer, dry wit, 5'11"), built with the Amni-CAD character builder on bodies fitted to real measurements, plus a plain mannequin.
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
- `art/` holds the stock character concepts and specs (`holo.json`, `dex.json`) and the two CC0 base bodies (`art/ubc/`). `tools/image3d.py` turns one concept image into a rigged, textured companion (see below).

```bash
tools/build.sh   # rebuild core/*.amni from Gold (if installed) and web/companion.wasm
tools/test.sh    # build and run the core tests natively, then rebuild the wasm
tools/stock.sh   # rebuild Holo and Dex from art/*.json (needs AMNI_SCIENT, see below)
```

## Stock companions

Holo and Dex are specs, not hand-edited meshes. `art/holo.json` and `art/dex.json` set sex, height in inches, build, body preferences (`prefs`: chest, waist, hips, thighs, calves, legs, arms, shoulders, head), the face (`portrait`: a front portrait made from the concept art, with its MediaPipe landmarks, hair and skin mask, and the concept's skin tone), extra shape sliders (`face`: MakeHuman sliders such as `neck-scale-horiz`, plus `skull-flat` and `skull-wide`, which round the cranium without touching the face), skin, eyes, makeup, hair and wear. `tools/stock.sh` passes them to the Amni-CAD character builder (`tools/build-characters.py` in the Amni-Scient checkout named by `AMNI_SCIENT`, default `~/ai/Amni-Scient`), which:

1. Fits the face to the portrait: it solves MakeHuman face targets so the 478 landmarks line up while the skull stays put, and matches the profile line (forehead, nose, lips and chin) to the landmarks' estimated depth so the mouth and chin sit where a real face's do in profile. Then it projects the portrait onto the skin, with eyes, brows, lips and makeup, and blends its tone into the body. It adds CC0 MakeHuman teeth and tongue, and bakes soft occlusion into the eyeballs where the lids meet them, with an off-white sclera.
2. Solves the height exactly and fits the body to median measurements of fit adults from the ANSUR II survey: breadths, depths and girths (so bellies, hips and chests have real depth), shoulder width, arm length and head size. Legs stand parallel, feet under the hips (`stance` changes the spacing).
3. Dresses it in CC0 MakeHuman clothing, or generates clothing MakeHuman lacks: tank top, pleated tartan skirt, studded belt, striped socks, fingerless gloves, choker, chain, hoodie with hood, pocket and drawstrings, and glasses fitted to the face. Clothing drapes over the body, and covered skin (skin that lies under a garment triangle, behind the fabric) is removed so it can't poke through. Every garment edge is smoothed and finished like real clothing: the tank top gets bound edges, and the hoodie gets a rib collar, cuffs and waistband, with its hood lying in a U over the back. Generated fabrics carry cloth sheen (KHR_materials_sheen) and a tiled jersey-knit normal map scaled to real stitch size (KHR_texture_transform), the hoodie has folds at the elbows, cuffs and waistband, and women's busts are rounded so fabric over them reads as a soft dome rather than MakeHuman's cone.
4. Grows the hair as strand cards with the Amni-CAD human engine's groom (written in Helium through Gold): roots are scattered over the scalp, each strand is grown along the head's surface through a distance field of the skin and a thin hair cap, with flow toward the braid, gravity for loose locks, curl and collision, then turned into a hair card textured from a strand atlas the engine renders (16 card styles of individual strands with clumping, stray hairs, root-to-tip shading and depth). Styles are a short swept-back cut with faded sides, or hair pulled back into a three-strand braid (each lobe a ring of cards) with face-framing locks and a side-swept fringe. The hairline is read from the portrait and follows the temples and ears. A spec's `fur` block grows facial hair the same way: `beard` roots follow the portrait's beard (its dark lower-face pixels), facing the camera, in dense patches only, with mustache hairs pointing down and out; `brows` is optional, since the painted portrait brows read better at viewing distance.
5. Paints extra makeup if asked (eyeshadow, winged liner, lips, blush, brows), extends the beard along the jaw, adds soft facial shading, rigs the game-engine skeleton, and writes the `.glb` plus a review sheet in `.stock/review/`.
6. Bakes the head's own texture set with the Amni-CAD human engine (written in Helium through Gold): the head's UV islands get a 4096×2048 texture of their own (about 2.5× sharper than the body texture), the portrait is projected into it with its baked-in lighting removed, and it writes a normal map of creases and stubble plus a map of occlusion, roughness (oily T-zone, wet lips, matte brows and beard) and pore strength. `skinmaps` in the spec tunes it (`relief`, `delight`, `ao`, `rough`, `tzone`, `lips`, `brows`, `beard`, `pores`).

Change a value and rerun to adjust a character. The builder reads MakeHuman assets from `AMNI_MH` (default `~/.cache/amni-mh`) and downloads the ANSUR II tables on first use.

### Skin shading

Materials tagged `amni: skin` in their glTF extras get the app's skin shader: light scattering through the skin from a pre-integrated table (`web/models/skin_lut.png`, from Penner and Borshukov's pre-integrated skin shading with d'Eon and Luebke's six-Gaussian skin profile), red light taken from the smoother surface normal, two specular lobes, and a seamless pore tile (`web/models/pores.png`) scaled to about 8 mm of skin. Eyes tagged `amni: eye` get a wet cornea layer. Both images come from the human engine (`human lut`, `human pores`).

### Hair shading

Materials tagged `amni: hair` get the app's hair shader, a strand model after Marschner et al. 2003 with the real-time fits from Karis 2016: a white primary reflection shifted toward the root, a colored secondary reflection shifted toward the tip, and light passing through loose hair when it is backlit. The strand direction comes from the card's vertex tangents, a per-strand id in the engine's data map jitters the highlight, depth in the atlas and the card's distance from the scalp darken inner hair, and alpha to coverage with mip-scaled alpha keeps thin strands smooth and visible at a distance.

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
5. **Shoes.** If the concept's feet are covered, the base body's toes are shrink-wrapped into a toe box, so boots and sneakers don't read as bare feet.
6. **Paint it.** The concept is projected onto everything the front view shows. The back is rebuilt by rules, never by copying the front:
   - The back of the head is hair, continued strand by strand from the hair beside the face, with a natural parting.
   - Front-only details (necklaces, pendants, buckles, buttons, drawstrings, pockets, logos, cleavage shading) are found and painted out before anything is mirrored.
   - Tops and skirts continue their side fabric around the back, so plaids, stripes and belts wrap while the details don't. Straps and necklines keep their shape.
   - Skin on the back is smooth skin, and hair sides sample the strands rather than stretching the silhouette edge.
7. **Review it.** `tools/review.mjs` renders a contact sheet (front, three-quarter back, side, back, close-ups of the head, torso and shoes, plus walk, sit, dance and idle) to `.stock/review/<id>.png`. Look at it before you ship a character.

Have a back view too? Pass it and the back is painted from it instead (same pose, same framing, plain background):

```bash
tools/character.sh nova nova_front.png female 1.68 --back nova_back.png
```

`AMNI_SRC_DEBUG=1` paints every texel by where its color came from (green front, magenta back view, yellow rebuilt back, blue mirrored, red filled), which makes texture problems easy to find.

The analysis runs in headless Chromium through `tools/analyze.mjs`: set `PW` to a folder whose `node_modules` has `playwright-core`, and `CHROME` to a Chromium or headless-shell binary. The first run downloads two MediaPipe models (Apache-2.0) to `~/.cache/amni-companion/mediapipe`.

Limits: without a back view the back is a best guess (no hoods, back pockets or back prints), loose garments other than skirts and dresses (capes, big coats) follow the body, hands, glasses and jewelry are painted rather than modeled, and thick hair seen from the side is smoother than in the concept.

## License

Amni-Companion is free software under the [GNU Affero General Public License v3.0](./LICENSE). If you run a modified version for others over a network, you must offer them its source. Third-party components keep their own licenses; see [NOTICE.md](./NOTICE.md).
