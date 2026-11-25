"""Shared configuration for the Visual Emotion Recognition module.

Everything that train.py, evaluate.py and inference.py must agree on lives here:
label order, Arabic names, the mapping to the project's candidate emotions,
zero-shot prompts and default paths.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
HF_DATASET = "Woleek/EmoSet-118K"  # EmoSet-118K (Yang et al., ICCV 2023), HF mirror

# The 8 Mikels emotion categories as they appear in EmoSet's `emotion` column.
# We map rows by the *string* in the `emotion` column, never by the integer,
# so a different integer order in the mirror cannot silently corrupt labels.
TRAINED_CLASSES = [
    "amusement",
    "awe",
    "contentment",
    "excitement",
    "anger",
    "disgust",
    "fear",
    "sadness",
]
CLASS_TO_IDX = {c: i for i, c in enumerate(TRAINED_CLASSES)}

# Arabic display names for the trained classes.
ARABIC_NAMES = {
    "amusement": "المرح",
    "awe": "الرهبة والانبهار",
    "contentment": "السكينة والرضا",
    "excitement": "الحماس",
    "anger": "الغضب",
    "disgust": "الاشمئزاز",
    "fear": "الخوف",
    "sadness": "الحزن",
}

# Candidate emotions proposed by the team:
# السكينة، الحنين، الحزن، الفرح، الشوق، الرهبة، التأمل
# Mapping trained class -> project candidate (None = outside the candidate list,
# still reported with its own Arabic name because poetry covers it too).
PROJECT_EMOTION = {
    "amusement": "الفرح",
    "excitement": "الفرح",
    "contentment": "السكينة",
    "awe": "الرهبة",
    "sadness": "الحزن",
    "anger": None,
    "disgust": None,
    "fear": None,
}

# Candidates that EmoSet does NOT label. They are never trained and never
# evaluated as if they were. They are offered as *semantic* suggestions from
# CLIP zero-shot similarity and flagged "zero_shot_unvalidated".
DERIVED_EMOTIONS = {
    "nostalgia": {
        "ar": "الحنين",
        "phrases": ["nostalgia", "nostalgic memories of the past", "an old memory"],
    },
    "longing": {
        "ar": "الشوق",
        "phrases": ["longing for someone far away", "yearning", "missing a loved one"],
    },
    "contemplation": {
        "ar": "التأمل",
        "phrases": ["quiet contemplation", "peaceful reflection", "meditative stillness"],
    },
}
DERIVED_CLASSES = list(DERIVED_EMOTIONS.keys())

# Zero-shot prompt templates (averaged = prompt ensembling).
PROMPT_TEMPLATES = [
    "a photo that evokes {}.",
    "an image that makes people feel {}.",
    "a picture with a mood of {}.",
]
CLASS_PHRASES = {c: [c] for c in TRAINED_CLASSES}

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
# Shared with Person 1 (visual understanding). If Person 1 uses another CLIP
# checkpoint, pass --model_name to prepare_features.py and both modules can
# share one encoder / one embedding per image.
DEFAULT_CLIP = "openai/clip-vit-base-patch32"
# CLIP's learned logit scale (exp(logit_scale), clamped at 100 in OpenAI CLIP).
CLIP_LOGIT_SCALE = 100.0
CLIP_MEAN = [0.48145466, 0.4578275, 0.40821073]
CLIP_STD = [0.26862954, 0.26130258, 0.27577711]

# Classic ImageNet CNN backbone for comparison (Unit 7 Part 3: ResNet/MobileNet/VGG)
COMPARISON_CNN = "resnet50"

# Images are cached once, resized so the shorter side is this many pixels.
CACHE_SHORT_SIDE = 256

# Default sample sizes (class-balanced subsamples of the official splits)
# Sized so the whole pipeline fits in one Colab session before the Wednesday
# hand-in; raise them if time allows (results must then be re-generated).
DEFAULT_PER_CLASS = {"train": 1000, "val": 200, "test": 500}
# Stop scanning a split after this many rows even if some quota is not full
DEFAULT_MAX_SCAN = {"train": 94_481, "val": 5_906, "test": 17_715}

# Fine-tuning (Strategy 2 in Unit 7 Part 3: partial unfreezing, low LR)
FT_UNFREEZE_LAYERS = 2
FT_EPOCHS = 3
FT_BATCH = 64
FT_LR_BACKBONE = 1e-5
FT_LR_HEAD = 1e-4
FT_WEIGHT_DECAY = 0.05
FT_LABEL_SMOOTHING = 0.1

# ---------------------------------------------------------------------------
# Suggestion / uncertainty policy (tunable; evaluate.py reports how accuracy
# changes with the margin so these thresholds can be justified or adjusted)
# ---------------------------------------------------------------------------
SUGGESTION_CUM_PROB = 0.80   # take classes until cumulative prob reaches this
SUGGESTION_MAX = 3           # but never more than this many trained suggestions
SUGGESTION_MIN_PROB = 0.10   # and never a class below this probability
AMBIGUOUS_MARGIN = 0.15      # top1 - top2 below this => ambiguous image
AMBIGUOUS_ENTROPY = 0.75     # normalised entropy above this => ambiguous image
DERIVED_MIN_SCORE = 0.10     # minimum zero-shot share to show a derived emotion

DISCLAIMER_AR = (
    "هذه اقتراحات للجو العاطفي الذي قد توحي به الصورة، وليست حكمًا على "
    "الحالة النفسية للمستخدم. يمكن للمستخدم تأكيدها أو تعديلها."
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FEATURES_DIR = os.path.join(MODULE_DIR, "features")
DEFAULT_ARTIFACTS_DIR = os.path.join(MODULE_DIR, "artifacts")
DEFAULT_RESULTS_DIR = os.path.join(MODULE_DIR, "results")
DEFAULT_CACHE_DIR = os.path.join(MODULE_DIR, "cache")
HEAD_FILENAME = "emotion_head.npz"          # deployed (shared-encoder) head
HEADS_SUBDIR = "heads"                       # every feature-extraction candidate
FINETUNED_SUBDIR = "finetuned"
FT_STATE_FILENAME = "finetuned_state.pt"
FT_META_FILENAME = "finetuned_meta.json"
TRAIN_REPORT_FILENAME = "training_report.json"
TEXT_EMB_FILENAME = "text_embeddings.npz"
DATA_REPORT_FILENAME = "data_report.json"

# Names of the hand-crafted visual attributes stored per image (attributes.py)
ATTRIBUTE_KEYS = ["brightness", "contrast", "saturation", "colorfulness", "warmth"]
