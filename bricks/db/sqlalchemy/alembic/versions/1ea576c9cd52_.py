"""empty message

Revision ID: 1ea576c9cd52
Revises: f94247e916d
Create Date: 2014-03-25 12:21:46.390154

"""

# revision identifiers, used by Alembic.
revision = '1ea576c9cd52'
down_revision = 'f94247e916d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('brickconfig', sa.Column('minimum_requirement', sa.String(length=36), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('brickconfig', 'minimum_requirement')
    ### end Alembic commands ###
