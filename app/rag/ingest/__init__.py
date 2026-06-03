"""Ingestion pipeline: refresh the corpus from live IL sources.

`make ingest` runs this. The app ships with an OFFLINE SEED snapshot in
data/corpus/, so ingestion is only needed to refresh content from the web.
"""
