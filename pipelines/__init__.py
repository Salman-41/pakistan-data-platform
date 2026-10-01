"""Bounded-memory public-source ingestion and revision-aware observation warehouse."""
from .ingest import ingest_csv, Metadata

__all__ = ['ingest_csv', 'Metadata']
