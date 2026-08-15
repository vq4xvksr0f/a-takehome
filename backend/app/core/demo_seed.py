"""Optional demo seed: populate realistic-looking leads for showcasing the app.

Enabled via SEED_DEMO_DATA=true. Idempotent — skipped entirely if any leads
already exist. Generates fake names/emails (Faker), a small valid PDF per lead
(so the resume Download link works in the demo), and activity history on the
leads that have been "reached out", attributed to the seeded admin.
"""

import io
import logging
import random
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..adapters.storage import ObjectStore
from ..models import Attorney, Lead, LeadActivity

logger = logging.getLogger(__name__)

# Deterministic so repeated demos look the same.
_fake = Faker()
Faker.seed(0)
random.seed(0)

# A minimal, valid single-page PDF with placeholder text. Small enough to seed
# quickly, real enough that the browser/PDF viewer opens it without error.
_PDF_TEMPLATE = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>endobj
4 0 obj<</Length 90>>stream
BT /F1 18 Tf 72 720 Td (Sample resume for __NAME__) Tj 0 -28 Td (Demo seed data) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
trailer<</Root 1 0 R>>
%%EOF
"""


def _sample_pdf(name: str) -> bytes:
    return _PDF_TEMPLATE.replace(b"__NAME__", name.encode("utf-8", "replace"))


def seed_demo_data(db: Session, object_store: ObjectStore) -> None:
    """Create demo leads if the table is empty. No-op otherwise."""
    if db.scalar(select(func.count()).select_from(Lead)):
        logger.info("Leads already exist; skipping demo seed")
        return

    admin = db.scalar(select(Attorney).limit(1))
    if admin is None:
        logger.info("No attorney found; skipping demo seed")
        return

    now = datetime.now(UTC)
    leads_created = 0
    for i in range(12):
        first = _fake.first_name()
        last = _fake.last_name()
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        object_key = f"resumes/demo/{i}-{first.lower()}-{last.lower()}.pdf"

        object_store.put(io.BytesIO(_sample_pdf(name)), object_key, "application/pdf")

        # Stagger creation over the past ~2 weeks, newest first.
        created = now - timedelta(days=random.randint(0, 13), hours=random.randint(0, 23))
        lead = Lead(
            first_name=first,
            last_name=last,
            email=email,
            state="PENDING",
            resume_object_key=object_key,
            resume_filename=f"{first.lower()}_{last.lower()}_resume.pdf",
            created_at=created.isoformat(),
            updated_at=created.isoformat(),
        )
        db.add(lead)
        db.flush()  # assign lead.id

        # About half have been reached out to; record the transition activity.
        if i % 2 == 0:
            reached = created + timedelta(days=random.randint(0, 3), hours=1)
            lead.state = "REACHED_OUT"
            lead.updated_at = reached.isoformat()
            db.add(
                LeadActivity(
                    lead_id=lead.id,
                    attorney_id=admin.id,
                    from_state="PENDING",
                    to_state="REACHED_OUT",
                    created_at=reached.isoformat(),
                )
            )
        leads_created += 1

    db.commit()
    logger.info("Seeded %d demo leads (attributed to %s)", leads_created, admin.email)
