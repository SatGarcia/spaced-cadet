from flask import (
    Blueprint, render_template, url_for, redirect, flash, request
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField
)
from wtforms.validators import DataRequired
from  sqlalchemy.sql.expression import func

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
        if form.yes.data:
            flash("Nice work!", "success")
        else:
            flash("You'll get it next time!", "danger")

        return redirect(url_for('.test'))

    # FIXME: should render the self_verify template again... but really should
    # never happen!
    return "BAD STUFF"

@user_views.route('/test', methods=['GET', 'POST'])
def test():
    """ Presents a random question to the user. """
    question = Question.query.order_by(func.random()).first()

    form = AnswerForm(question_id=question.id)
    if form.validate_on_submit():

        original_question_id = form.question_id.data
        review_form = SelfReviewForm(question_id=original_question_id)
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
    question_id = HiddenField("qid")
    yes = SubmitField("Yes")
    no = SubmitField("No")

class AnswerForm(FlaskForm):
    question_id = HiddenField("qid")
    answer = TextAreaField('answer', validators=[DataRequired()])
    submit = SubmitField("Submit")

from app.db_models import Question
