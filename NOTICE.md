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

The stock characters Holo and Dex are original designs by Amniscient. Their concept art was generated with MOSS-Image (Apache-2.0) through Amni-Gen and turned into rigged, textured models with `tools/character.sh`, which fits the CC0 Universal Base Characters bodies to the art using MediaPipe pose, face and segmentation models (Apache-2.0, downloaded at build time). They are released with the app under the AGPL-3.0.

Models you load yourself remain yours and are never uploaded.
