"""Updates to support multiple selection questions

Revision ID: bdfee55cfa59
Revises: 9e36b0fe341b
Create Date: 2022-06-23 14:45:35.784815

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdfee55cfa59'
down_revision = '9e36b0fe341b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('multiple_selection_question',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['question.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('multiple_selection_question')
    # ### end Alembic commands ###
