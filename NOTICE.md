# Notices

Amni-Companion is copyright Amniscient and licensed under the AGPL-3.0 (see LICENSE).

It bundles these third-party components, each under its own license:

| Component | Path | License |
|---|---|---|
| three.js r170 | `web/vendor/three/` | MIT, see `web/vendor/three/LICENSE` |
| MediaPipe Tasks Vision and its models (pose landmarker, gesture recognizer, face landmarker) | `web/vendor/mediapipe/` | Apache-2.0 |
| EfficientDet-Lite0 object detector | `web/vendor/mediapipe/efficientdet_lite0.tflite` | Apache-2.0 |
| Universal Animation Library by Quaternius | `web/anim/` | CC0 1.0 |
| Universal Base Characters by Quaternius (base bodies for the character builder) | `art/ubc/` | CC0 1.0 |
| MakeHuman base mesh, morph targets, skins, eyes, eyebrows, eyelashes, hair and clothing (in Holo and Dex) | `web/models/holo.glb`, `web/models/dex.glb` | CC0 1.0 |
| MPFB 2 game-engine skeleton and skin weights (in Holo and Dex) | `web/models/holo.glb`, `web/models/dex.glb` | CC0 1.0 |

The stock characters Holo and Dex are original designs by Amniscient. Their concept art was generated with MOSS-Image (Apache-2.0) through Amni-Gen. The models are built from `art/holo.json` and `art/dex.json` by the Amni-CAD character builder (`tools/build-characters.py` in Amni-Scient), which assembles the CC0 MakeHuman and MPFB assets on a body fitted to median measurements of fit adults in the ANSUR II anthropometric survey (US Army, 2012, public data from the Penn State Open Design Lab) and adds generated clothing. They are released with the app under the AGPL-3.0.

Models you load yourself remain yours and are never uploaded.
