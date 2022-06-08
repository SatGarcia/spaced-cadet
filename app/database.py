import click
from flask import current_app
from flask.cli import with_appcontext

from app import db
from app.db_models import User, Question


@click.command('add-user')
@click.option('--admin', is_flag=True, default=False)
@click.option('--instructor', is_flag=True, default=False)
@click.argument('email')
@click.argument('first_name')
@click.argument('last_name')
@with_appcontext
def add_admin_user(admin, instructor, email, first_name, last_name):
    """Adds a new user to the database. Their password will be
    randomized so they must reset their password via the website."""

    new_user = User(email=email,
                        first_name=first_name,
                        last_name=last_name,
                        admin=admin,
                        instructor=instructor)
    new_user.set_password(User.generate_password(30))
    db.session.add(new_user)
    db.session.commit()

    click.echo(f"Added new user: {first_name} {last_name} ({email}).")
    click.echo(f"\tAdmin: {admin}")
    click.echo(f"\tInstructor: {instructor}")


def init_app(app):
    db.init_app(app)
    app.cli.add_command(add_admin_user)

