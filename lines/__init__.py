"""Transit Line Extractors Registry"""
from .base import BaseTransitExtractor
from .mrt_kajang import MrtKajangExtractor

EXTRACTORS = {
    "mrt-kajang": MrtKajangExtractor,
}

__all__ = ["BaseTransitExtractor", "MrtKajangExtractor", "EXTRACTORS"]
