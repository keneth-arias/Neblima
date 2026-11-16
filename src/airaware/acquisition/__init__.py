"""Adquisición explícita de bytes; independiente de normalización y publicación externa."""

from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.store import ingest_file

__all__ = ["AcquisitionError", "AcquisitionResult", "AcquisitionSpec", "ingest_file"]
