import click
from flask import current_app
from flask.cli import with_appcontext

from app import db
from app.db_models import User, Question


@click.command('add-admin')
@click.argument('email')
@click.argument('first_name')
@click.argument('last_name')
@with_appcontext
def add_admin_user(email, first_name, last_name):
    """Adds a new admin user to the database. Their password will be
    randomized."""

    admin_user = User(email=email,
                        first_name=first_name,
                        last_name=last_name,
                        admin=True,
                        instructor=True)
    admin_user.set_password(User.generate_password(30))
    db.session.add(admin_user)
    db.session.commit()

    click.echo(f"Added new admin user: {first_name} {last_name} ({email}).")


def init_app(app):
    db.init_app(app)

    with app.app_context():
        db.create_all()

        for q in Question.query:
            print(repr(q))

    app.cli.add_command(add_admin_user)

