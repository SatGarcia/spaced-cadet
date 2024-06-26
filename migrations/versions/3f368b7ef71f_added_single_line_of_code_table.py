"""Added Single Line of Code Table

Revision ID: 3f368b7ef71f
Revises: 76c63ab379cb
Create Date: 2023-06-16 18:02:53.621433

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f368b7ef71f'
down_revision = '76c63ab379cb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('single_line_code_question',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('answer', sa.String(), nullable=False),
    sa.Column('add_body', sa.Boolean(), nullable=False),
    sa.Column('language', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['question.id'], name=op.f('fk_single_line_code_question_id_question')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_single_line_code_question'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('single_line_code_question')
    # ### end Alembic commands ###
