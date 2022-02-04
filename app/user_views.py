from flask import (
    Blueprint, render_template, url_for, redirect, flash, request
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField
)
from wtforms.validators import DataRequired
from sqlalchemy.sql.expression import func
from datetime import date, timedelta

from app import db

user_views = Blueprint('user_views', __name__)

@user_views.route('/')
def root():
    return render_template("home.html")

@user_views.route('/review', methods=['POST'])
def self_review():
    """ User will self-verify whether the answer they submitted is the correct
    one or not. """
    form = SelfReviewForm(request.form)
    if form.validate_on_submit():

        # update the outcome of the attempt in the database
        attempt = Attempt.query.filter_by(id=form.attempt_id.data).first()
        q = attempt.question

        if form.yes.data:
            flash("Nice work!", "success")
            attempt.correct = True

            q.next_attempt = date.today() + timedelta(days=1)
        else:
            flash("You'll get it next time!", "danger")
            attempt.correct = False

        db.session.commit()

        return redirect(url_for('.test'))

    # FIXME: should render the self_verify template again... but really should
    # never happen!
    return "BAD STUFF"

@user_views.route('/test', methods=['GET', 'POST'])
def test():
    """ Presents a random question to the user. """
    question = Question.query.filter(Question.next_attempt <= date.today()).order_by(func.random()).first()

    if not question:
        # No questions need to be tested so display a completed page.
        return render_template("completed.html", page_title="Cadet: Complete")

    form = AnswerForm(question_id=question.id)
    if form.validate_on_submit():


        original_question_id = form.question_id.data

        # add the attempt to the database (leaving the outcome undefined for
        # now)
        attempt = Attempt(response=form.answer.data,
                          question_id=original_question_id)
        db.session.add(attempt)
        db.session.commit()

        # create the self review_form
        review_form = SelfReviewForm(attempt_id=attempt.id)
        original_question = Question.query.filter_by(id=original_question_id).first()

        return render_template("self_verify.html",
                               page_title="Cadet Test: Self Verification",
                               form=review_form,
                               term=original_question.prompt,
                               answer=form.answer.data,
                               definition=original_question.answer)

    return render_template("question.html",
                           page_title="Cadet Test",
                           form=form,
                           term=question.prompt)

class SelfReviewForm(FlaskForm):
    #question_id = HiddenField("qid")
    attempt_id = HiddenField("Attempt ID")
    yes = SubmitField("Yes")
    no = SubmitField("No")

class AnswerForm(FlaskForm):
    question_id = HiddenField("qid")
    answer = TextAreaField('answer', validators=[DataRequired()])
    submit = SubmitField("Submit")

from app.db_models import Question, Attempt
