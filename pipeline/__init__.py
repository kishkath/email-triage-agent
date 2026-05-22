"""Triage pipeline: classification, digest handling, and the one-shot runner."""

from .classifier import classify_email

__all__ = ["classify_email"]
