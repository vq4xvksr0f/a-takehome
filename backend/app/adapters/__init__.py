"""External-service adapters: object storage and email.

Each module defines a narrow port (abstract interface) plus a concrete
implementation, so the rest of the app depends on the interface, not the
vendor. Swapping MinIO for S3 or Resend for another provider is confined here.
"""
