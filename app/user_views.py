from flask import (
    Blueprint, render_template, url_for, redirect, flash, request
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    RadioField
)
from wtforms.validators import DataRequired, InputRequired
from datetime import date, timedelta, datetime

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
        a = Attempt.query.filter_by(id=form.attempt_id.data).first()
        # TODO: check that query returned something (50X error otherwise)
        quality = form.difficulty.data

        a.e_factor += 0.1 - ((5-quality) * (0.08 + ((5-quality) * 0.02)))
        a.interval = 6 if a.interval == 1 else int(a.interval * a.e_factor)

        # next attempt will be interval days from today
        a.next_attempt = date.today() + timedelta(days=a.interval)

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
            db.session.commit()
            difficulty_form = DifficultyForm(attempt_id=form.attempt_id.data)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form)

        # they missed it so reset interval to 1 and update the e_factor
        flash("No worries. We'll test you on this question again tomorrow.", "danger")
        attempt.correct = False

        quality = 2  # they made an attempt but were wrong so set difficulty to 2
        attempt.e_factor += 0.1 - ((5-quality) * (0.08 + ((5-quality) * 0.02)))

        # missed question should be repeated again tomorrow
        attempt.interval = 1
        attempt.next_attempt = date.today() + timedelta(days=attempt.interval)

        db.session.commit()

        return redirect(url_for('.test'))

    # FIXME: should render the self_verify template again... but really should
    # never happen!
    return "BAD STUFF"


@user_views.route('/test/multiple-choice', methods=['POST'])
def test_multiple_choice():
    curr_user = Student.query.filter_by(username='sat').first()

    form = MultipleChoiceForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()
    form.response.choices = [(option.id, option.text) for option in original_question.options]

    if form.validate_on_submit():
        # get the selected answer and check if it was correct
        answer_id = form.response.data
        selected_answer = AnswerOption.query.filter_by(id=answer_id).first()
        if selected_answer.correct:
            flash("CORRECT! Nice work!", "success")
        else:
            flash("INCORRECT. No worries. We'll test you on this question again tomorrow.", "danger")

        return redirect(url_for('.test'))

    return "FAIL"

@user_views.route('/test/definition', methods=['POST'])
def test_definition():
    curr_user = Student.query.filter_by(username='sat').first()

    form = DefinitionForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()

    if form.validate_on_submit():
        # check for a previous attempt
        previous_attempt = Attempt.query.filter(Attempt.student_id == curr_user.id,
                                                Attempt.question_id == original_question_id).order_by(
                                                    Attempt.time.desc()).first()

        # add the attempt to the database (leaving the outcome undefined for
        # now)
        attempt = Attempt(response=form.answer.data,
                          question_id=original_question_id,
                          student_id=curr_user.id)

        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval

        db.session.add(attempt)
        db.session.commit()

        # create the self review_form
        review_form = SelfReviewForm(attempt_id=attempt.id)

        return render_template("self_verify.html",
                               page_title="Cadet Test: Self Verification",
                               form=review_form,
                               term=original_question.prompt,
                               answer=form.answer.data,
                               definition=original_question.answer)

    return render_template("test_definition.html",
                           page_title="Cadet Test",
                           form=form,
                           term=original_question.prompt)

@user_views.route('/test', methods=['GET', 'POST'])
def test():
    """ Presents a random question to the user. """
    curr_user = Student.query.filter_by(username='sat').first()

    # get all the questions from section's that this student is enrolled in
    possible_questions = Question.query.join(
        enrollments, (enrollments.c.section_id == Question.section_id)).filter(
            enrollments.c.student_id == curr_user.id)

    # find questions that haven't been attempted yet, as these will be part of
    # the pool of questions we can ask them
    unattempted_questions = possible_questions.filter(~ Question.attempts.any(Attempt.student_id == curr_user.id))

    # Find questions whose next attempt is before today, as these will also be
    # part of the pool of questions to ask
    latest_next_attempts = db.session.query(
        Attempt.question_id, Attempt.next_attempt, db.func.max(Attempt.next_attempt).label('latest_next_attempt_time')
    ).group_by(Attempt.question_id).subquery()

    #target_time = date.today() + timedelta(days=2)
    target_time = datetime.utcnow()
    ready_questions = Question.query.join(
        latest_next_attempts, db.and_(Question.id == latest_next_attempts.c.question_id,
                                      latest_next_attempts.c.latest_next_attempt_time <= target_time)
    ).union(unattempted_questions)

    """
    print("Ready Questions:")
    for q in ready_questions:
        print("\t", q)
    """

    # randomly pick one of the ready questions
    question = ready_questions.order_by(db.func.random()).first()

    if not question:
        # No questions need to be tested so display a completed page.
        return render_template("completed.html", page_title="Cadet: Complete")

    if question.type == QuestionType.DEFINITION:
        form = DefinitionForm(question_id=question.id)
        return render_template("test_definition.html",
                               page_title="Cadet Test",
                               form=form,
                               term=question.prompt)

    elif question.type == QuestionType.MULTIPLE_CHOICE:
        form = MultipleChoiceForm(question_id=question.id)
        form.response.choices = [(option.id, option.text) for option in question.options]

        return render_template("test_multiple_choice.html",
                               page_title="Cadet Test",
                               form=form,
                               prompt=question.prompt)
    else:
        return "UNSUPPORTED QUESTION TYPE"


class DifficultyForm(FlaskForm):
    """ Form to report the difficulty they had in answering a question. """
    attempt_id = HiddenField("Attempt ID")
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

class DefinitionForm(FlaskForm):
    question_id = HiddenField("Question ID")
    answer = TextAreaField('answer', validators=[DataRequired()])
    submit = SubmitField("Submit")

class MultipleChoiceForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = RadioField('answer', validators=[InputRequired()], coerce=int)
    submit = SubmitField("Submit")

from app.db_models import (
    Question, Attempt, Student, enrollments, QuestionType, AnswerOption
)
