"""Data-access layer. Each package exposes a repository over one aggregate.

Repositories own all SQLAlchemy interaction for their aggregate so services
never touch the ORM directly. Swapping SQLite for PostgreSQL (design doc §14)
should require no changes above this layer.
"""
