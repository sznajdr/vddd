# 01 — Detection (M2, pilot detector)

## Question
What detects `horse_sulky` boxes in broadcast wide-pan frames with no owner annotations (pilot), and what should production M2 fine-tune from?

## Findings

### Zero-shot / open-vocabulary detectors
- **Grounding DINO** is the accuracy leader among open-vocabulary detectors (≈ 52.5 AP COCO zero-shot for the original; later Pro variants reported 54–55 AP). ([Roboflow guide](https://blog.roboflow.com/best-object-detection-models/), [Forasoft 2026 guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr)) *(secondary sources; version numbering disagrees between them)*
- **OWLv2**: Apache-2.0, lower accuracy, simplest to fine-tune, short noun-phrase prompts. On an aerial zero-shot benchmark (LAE-80C, arXiv 2601.22164) OWLv2 beat the YOLO family badly, which shows benchmark choice dominates rankings. ([arXiv 2601.22164](https://arxiv.org/html/2601.22164v1))
- **YOLO-World**: real-time open-vocabulary (≈ 35 AP LVIS at 52 FPS on V100). ([GitHub](https://github.com/ailab-cvc/yolo-world))
- **RF-DETR**: closed-vocabulary, Apache-2.0, first real-time model past 60 mAP COCO per Roboflow; strong domain-transfer results on RF100-VL. Candidate for production fine-tuning. ([Roboflow](https://blog.roboflow.com/best-object-detection-models/))
- **SAM 3** (released 2025-11-19): concept prompts (text) → detection + segmentation + tracking in images and video; "near real-time for approximately five concurrent objects"; video prompts defined over short clips (~30 s). SAM 3.1 reported ~7× faster at 128 objects on one H100 with mixed text-prompt video accuracy. ([arXiv 2511.16719](https://arxiv.org/html/2511.16719v2), [Meta blog](https://ai.meta.com/blog/segment-anything-model-3/), [Roboflow](https://blog.roboflow.com/what-is-sam3/), [LearnOpenCV](https://learnopencv.com/sam-3-whats-new/)) *(vendor and review sources)*

### Pretraining data with relevant classes
- **Objects365** has `Horse` (class 78) and `Carriage` (class 215) among 365 classes, 638K images; Objects365 pretraining beat ImageNet pretraining on COCO by 5.6 mAP in the original paper. ([Ultralytics Objects365 page](https://docs.ultralytics.com/datasets/detect/objects365/), [Objects365 paper](https://aminer.org/pub/5e63725891e011ae97a699b0/objects-a-large-scale-high-quality-dataset-for-object-detection))
- No public dataset with a **sulky** class was found. No public horse-racing MOT/detection dataset with boxes was found. The one academic horse-racing MOT paper (Ng et al., *Information Sciences* 638, 2023, DOI 10.1016/j.ins.2023.118967) built its own 15-video set in MOT16 format and augmented it with ACGAN-generated frames of hard scenes (camera switches, blur); day and night test scenes. ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0020025523005364), [CityU](https://scholars.cityu.edu.hk/en/publications/multi-object-tracking-for-horse-racing/))
- Adjacent: SportsMOT (basketball/volleyball/football; fast variable motion, similar appearance) and SoccerNet-Tracking are the reference sports MOT benchmarks; neither has horses. ([SportsMOT](https://arxiv.org/pdf/2304.05170), [SoccerNet-Tracking](https://arxiv.org/pdf/2204.06918))

## Implications for the spec

1. **Pilot detector (RP-13):** Grounding DINO or OWLv2 with prompt ensemble {"horse", "horse pulling a sulky", "harness racing horse and driver"}; keep the union box of horse + sulky as `horse_sulky`. SAM 3 is an alternative if a GPU with enough memory is at hand, with the 5-object latency caveat.
2. **Production M2 stays as specified** (single class, fine-tuned on owner boxes, race-disjoint holdout). Pretrain from Objects365-initialised weights where the chosen family offers them. The absence of any public dataset confirms §6.1's ≥ 500 labelled frames are the minimum, not a nicety.
3. **Day/night strata (EC-05):** the 2023 horse-racing MOT paper's explicit day/night split corroborates treating night as a first-class stratum.
4. **Threshold namespace `m2_detect`:** `conf_min`, `nms_iou`, `box_expand_sulky` (pilot only), prompt list hash as part of `extractor_version` (non-numeric).
