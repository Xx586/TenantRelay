"""create SaaS support schema

Revision ID: 0001_saas_schema
"""
from alembic import op
from scenarios.saas.models import Base

revision = "0001_saas_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
