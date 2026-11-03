# Notices

Amni-Companion is copyright Amniscient and licensed under the AGPL-3.0 (see LICENSE).

It bundles these third-party components, each under its own license:

| Component | Path | License |
|---|---|---|
| three.js r170 | `web/vendor/three/` | MIT, see `web/vendor/three/LICENSE` |
| MediaPipe Tasks Vision and its models (pose landmarker, gesture recognizer, face landmarker) | `web/vendor/mediapipe/` | Apache-2.0 |
| EfficientDet-Lite0 object detector | `web/vendor/mediapipe/efficientdet_lite0.tflite` | Apache-2.0 |
| Universal Animation Library by Quaternius | `web/anim/` | CC0 1.0 |
| Body and face templates derived from Universal Base Characters by Quaternius | `art/proportions_*.json`, `art/face_*.npz` | CC0 1.0 |

The stock characters Holo and Dex are original designs by Amniscient. Their concept art was generated with MOSS-Image (Apache-2.0) through Amni-Gen, meshed with TRELLIS (MIT), based on an Amni-CAD rig, and proportioned, rigged and textured from the concept art with `tools/character.sh`. They are released with the app under the AGPL-3.0.

Models you load yourself remain yours and are never uploaded.
