"""Infrastructure services: external I/O with no domain knowledge.

Modules here talk to the outside world (network APIs, the filesystem) so the
domain layer stays pure. They must not import FastAPI, SQLAlchemy models, or
anything from ``app.domain``.
"""
