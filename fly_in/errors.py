"""Shared exception hierarchy for the Fly-in project."""

from __future__ import annotations


class FlyInError(Exception):
    """Base class for every domain-specific error raised by Fly-in."""
