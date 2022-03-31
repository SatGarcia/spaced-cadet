from flask import (
    Blueprint, render_template, abort, current_app, request, redirect, url_for,
    flash, Markup
)

from flask_login import current_user, login_user, logout_user, LoginManager

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, PasswordField, EmailField
)
from wtforms.validators import InputRequired, Email, EqualTo, Length, Regexp

from flask_jwt_extended import JWTManager, create_access_token, decode_token
from jwt.exceptions import DecodeError, ExpiredSignatureError

from datetime import timedelta

#from cas import CASClient

from app import db
from app.email import send_email

auth = Blueprint('auth', __name__)

login_manager = LoginManager()
jwt = JWTManager()


def init_app(app):
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = None

    jwt.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    current_app.logger.debug(f"loading user: {user_id}")

    try:
        user = User.query.filter_by(id=int(user_id)).one()
        return user

    except:
        current_app.logger.error(f"Couldn't load user with id {user_id}")
        return None


def post_login_redirect(next_url):
    """ Sends user to next_url (if specified) or to the home page. """
    if next_url is None:
        return redirect(url_for('user_views.root'))
    else:
        return redirect(next_url)

@auth.route('/login', methods = ['POST', 'GET'])
def login():
    next_url = request.args.get('next')

    if current_user.is_authenticated:
        flash(f"You are already signed in as {current_user.email}", "warning")
        post_login_redirect(next_url)

    else:
        form = LoginForm()

        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).one_or_none()

            if user and user.check_password(form.password.data):
                login_user(user)
                flash(f"Successfully signed in as {user.email}", "success")
                return post_login_redirect(next_url)

            else:
                flash(f"Could not sign in.", "danger")

        return render_template("login.html",
                               page_title="Cadet: Sign In",
                               form=form)


@auth.route('/logout')
def logout():
    if current_user.is_authenticated:
        current_app.logger.info(f"logout: {current_user.email}")
        logout_user()
        flash("You've successfully logged out!", "success")

    else:
        flash("You must be signed in before you can log out!", "warning")

    return redirect(url_for('user_views.root'))


@auth.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            reset_token = create_access_token(str(user.id),
                                              expires_delta=timedelta(minutes=15))

            url = url_for(".reset_password", token=reset_token, _external=True)

            send_email('Reset Your SpacedCadet Password',
                       sender='cadet.noreply@hopper.sandiego.edu',
                       recipients=[user.email],
                       text_body=render_template('reset_password_email.txt',
                                                 user=user,
                                                 url=url),
                       html_body=render_template('reset_password_email.html',
                                                 user=user,
                                                 url=url))

        flash(f"An email will be sent to {form.email.data} with instructions on how to reset your password. You will have 15 minutes to complete the reset.",
              "info")

        return redirect(url_for("user_views.root"))

    return render_template("forgot_password.html",
                           page_title="Cadet: Forgot Password",
                           form=form)

@auth.route('/reset', methods=['GET', 'POST'])
def reset_password():
    reset_token = request.args.get('token')
    if not reset_token:
        abort(400)

    try:
        user_id = decode_token(reset_token)['sub']
        user = User.query.filter_by(id=user_id).first()
        if not user:
            abort(400)

    except DecodeError:
        flash("Password reset failed. Check that you used the correct link.", "danger")
        return redirect(url_for("user_views.root"))
    except ExpiredSignatureError:
        flash(Markup(f"Password reset failed: Time expired. <a href='{url_for('.forgot_password')}'>Try again</a>."), "danger")
        return redirect(url_for("user_views.root"))
    except Exception as err:
        flash("Password reset failed.", "danger")
        app.logger.info(f"Password reset unknown failure type: {type(err)} ({err})")
        return redirect(url_for("user_views.root"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()

        current_app.logger.info(f"Password reset for {user.email}.")
        flash("Password reset succeeded. Log in with your new password now.",
              "success")
        return redirect(url_for("auth.login"))


    return render_template("reset_password.html",
                           page_title="Cadet: Reset Password",
                           form=form)


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField("Submit")


class ForgotPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    submit = SubmitField("Submit")


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password',
                             validators=[InputRequired(),
                                         Length(min=10, max=50),
                                         EqualTo('confirm',
                                                 message='Passwords must match'),
                                         Regexp("^[a-zA-Z0-9!@#$%^&*()\-_]+$",
                                                message="Password may contain only letters (a-z), digits (0-9) and special characters: !@#$%^&*()-_"),
                                         Regexp(".*\d.*",
                                                message="Password must have at least one digit (0-9)."),
                                         Regexp(".*[!@#$%^&*()\-_].*",
                                                message="Password must have at least one special character: !@#$%^&*()-_")
                                         ])
    confirm = PasswordField('Repeat Password', validators=[InputRequired()])

    submit = SubmitField("Reset Password")


from app.db_models import (
    Question, Attempt, User, enrollments, QuestionType, AnswerOption,
    TextAttempt, SelectionAttempt
)
