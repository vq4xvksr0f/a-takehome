"""HTTP layer: routers and request-scoped dependencies.

These modules translate HTTP <-> domain (parse requests, set status codes and
cookies, render responses) and delegate all business logic to services/. No
SQLAlchemy statements belong here.
"""
