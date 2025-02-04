from .GF_translate import GFDeepTranslateNode, GFJsonTranslate

NODE_CLASS_MAPPINGS = {
    "GFDeepTranslate": GFDeepTranslateNode,
    "GFJsonTranslate": GFJsonTranslate
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GFDeepTranslate": "🐵 GF Deep Translate",
    "GFJsonTranslate": "🐵 GF JsonTranslate"
}