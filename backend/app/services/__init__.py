"""Service layer: business logic, orchestration, and domain rules.

Services sit between the HTTP layer (api/) and the data/adapter layers
(repositories/, storage, email_client). They contain no FastAPI or SQLAlchemy
imports — only domain objects and injected ports — which keeps them trivially
unit-testable.
"""
