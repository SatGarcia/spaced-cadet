from flask import (
    Blueprint, render_template, url_for, redirect, flash, request
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField
)
from wtforms.validators import DataRequired
from sqlalchemy.sql.expression import func
from datetime import date, timedelta

from app import db

user_views = Blueprint('user_views', __name__)

@user_views.route('/')
def root():
    return render_template("home.html")

@user_views.route('/difficulty', methods=['POST'])
def difficulty():
    """ Route to handle self-reported difficulty of a problem that the user
    got correct. """

    form = DifficultyForm(request.form)
    if form.validate_on_submit():
        # get the question and update it's interval and e_factor
        q = Question.query.filter_by(id=form.question_id.data).first()
        quality = form.difficulty.data

        q.e_factor += 0.1 - ((5-quality) * (0.08 + ((5-quality) * 0.02)))
        q.interval = 6 if q.interval == 1 else int(q.interval * q.e_factor)

        # next attempt will be interval days from today
        q.next_attempt = date.today() + timedelta(days=q.interval)

        db.session.commit()

    flash("Nice work!", "success")
    return redirect(url_for('.test'))


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
            attempt.correct = True
            difficulty_form = DifficultyForm(question_id=q.id)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form)

        # they missed it so reset interval to 1 and update the e_factor
        flash("No worries. We'll test you on this question again tomorrow.", "danger")
        attempt.correct = False

        quality = 2  # they made an attempt but were wrong so set difficulty to 2
        q.e_factor += 0.1 - ((5-quality) * (0.08 + ((5-quality) * 0.02)))

        q.interval = 1
        q.next_attempt = date.today() + timedelta(days=q.interval)

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

class DifficultyForm(FlaskForm):
    """ Form to report the difficulty they had in answering a question. """
    question_id = HiddenField("Question ID")
    difficulty = SelectField('Difficulty',
                             choices=[(5, "Easy: The info was easy to recall"),
                                      (4, 'Medium: I had to take a moment to recall something'),
                                      (3, 'Hard: I barely recalled the info I needed.')],
                             coerce=int)
    submit = SubmitField("Submit")

class SelfReviewForm(FlaskForm):
    attempt_id = HiddenField("Attempt ID")
    yes = SubmitField("Yes")
    no = SubmitField("No")

class AnswerForm(FlaskForm):
    question_id = HiddenField("Question ID")
    answer = TextAreaField('answer', validators=[DataRequired()])
    submit = SubmitField("Submit")

from app.db_models import Question, Attempt
