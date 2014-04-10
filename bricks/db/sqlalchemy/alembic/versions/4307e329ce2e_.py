"""empty message

Revision ID: 4307e329ce2e
Revises: 5314cde0aa04
Create Date: 2014-04-01 14:39:58.054363

"""

# revision identifiers, used by Alembic.
revision = '4307e329ce2e'
down_revision = '5314cde0aa04'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('brickconfig', sa.Column('help_link', sa.String(length=255), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('brickconfig', 'help_link')
    ### end Alembic commands ###