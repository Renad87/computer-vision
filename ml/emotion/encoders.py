"""Pre-trained backbones (PyTorch). Imported lazily so that numpy-only parts
of the module (head, metrics, attributes) work without torch installed.

* ClipImageEncoder  – CLIP vision tower + projection (shared with Person 1)
* ClipTextEncoder   – CLIP text tower, only used once to build zero-shot prompts
* ResNetEncoder     – ImageNet ResNet50 penultimate layer (comparison backbone)
All image embeddings returned as float32 numpy, CLIP ones L2-normalised.
"""
from __future__ import annotations

import numpy as np


def get_device(device=None):
    import torch
    if device:
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class ClipImageEncoder:
    def __init__(self, model_name: str, device=None, model=None):
        import torch
        from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection

        self.device = get_device(device)
        self.model_name = model_name
        self.processor = CLIPImageProcessor.from_pretrained(model_name)
        self.model = model if model is not None else CLIPVisionModelWithProjection.from_pretrained(model_name)
        self.model.to(self.device).eval()
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.dim = self.model.config.projection_dim

    def encode(self, images) -> np.ndarray:
        import torch
        inputs = self.processor(images=list(images), return_tensors="pt")
        pix = inputs["pixel_values"].to(self.device)
        with torch.no_grad(), torch.autocast(self.device.type, dtype=self.dtype,
                                             enabled=self.device.type == "cuda"):
            emb = self.model(pixel_values=pix).image_embeds
        emb = torch.nn.functional.normalize(emb.float(), dim=-1)
        return emb.cpu().numpy().astype(np.float32)


class ClipTextEncoder:
    def __init__(self, model_name: str, device=None):
        from transformers import CLIPTextModelWithProjection, CLIPTokenizer

        self.device = get_device(device)
        self.tokenizer = CLIPTokenizer.from_pretrained(model_name)
        self.model = CLIPTextModelWithProjection.from_pretrained(model_name).to(self.device).eval()

    def encode(self, texts) -> np.ndarray:
        import torch
        tok = self.tokenizer(list(texts), padding=True, return_tensors="pt").to(self.device)
        with torch.no_grad():
            emb = self.model(**tok).text_embeds
        emb = torch.nn.functional.normalize(emb.float(), dim=-1)
        return emb.cpu().numpy().astype(np.float32)

    def concept_embeddings(self, phrases_by_concept: dict, templates: list) -> np.ndarray:
        """Prompt ensembling: mean of normalised template embeddings, renormalised."""
        out = []
        for concept, phrases in phrases_by_concept.items():
            texts = [t.format(p) for p in phrases for t in templates]
            e = self.encode(texts).mean(axis=0)
            out.append(e / np.linalg.norm(e))
        return np.stack(out).astype(np.float32)


class ResNetEncoder:
    """ImageNet-pretrained ResNet50 with the classifier removed (2048-d)."""

    def __init__(self, device=None):
        import torch
        from torchvision.models import ResNet50_Weights, resnet50

        self.device = get_device(device)
        weights = ResNet50_Weights.IMAGENET1K_V2
        self.model = resnet50(weights=weights)
        self.model.fc = torch.nn.Identity()
        self.model.to(self.device).eval()
        self.transform = weights.transforms()
        self.dim = 2048

    def encode(self, images) -> np.ndarray:
        import torch
        batch = torch.stack([self.transform(im) for im in images]).to(self.device)
        with torch.no_grad(), torch.autocast(self.device.type, dtype=torch.float16,
                                             enabled=self.device.type == "cuda"):
            emb = self.model(batch)
        return emb.float().cpu().numpy().astype(np.float32)
