from flask import (
    Blueprint, render_template, url_for, redirect, flash, request, Markup,
    abort
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    RadioField
)
from wtforms.validators import DataRequired, InputRequired
from flask_login import current_user, login_required

import ast, markdown
from datetime import date, timedelta, datetime
from math import ceil

from app import db

user_views = Blueprint('user_views', __name__)

def markdown_to_html(markdown_text, code_linenums=True):
    """ Convert markdown text to html. """
    html = markdown.markdown(markdown_text,
                             extensions=['fenced_code',
                                         'codehilite',
                                         'pymdownx.arithmatex'],

                             extension_configs = {
                                 "pymdownx.arithmatex": {
                                     "generic": True
                                 },
                                 "codehilite": {
                                     "linenums": code_linenums
                                 }
                             })
    return html

@user_views.route('/')
def root():
    return render_template("home.html")

@user_views.route('/difficulty', methods=['POST'])
@login_required
def difficulty():
    """ Route to handle self-reported difficulty of a problem that the user
    got correct. """

    form = DifficultyForm(request.form)
    if form.validate_on_submit():
        # get the question and update it's interval and e_factor
        a = Attempt.query.filter_by(id=form.attempt_id.data).first()
        # TODO: check that query returned something (50X error otherwise)

        sm2_update(a, form.difficulty.data) # update sm2 based on reported difficulty
        db.session.commit()

    return redirect(url_for('.test'))


@user_views.route('/review', methods=['POST'])
@login_required
def self_review():
    """ User will self-verify whether the answer they submitted is the correct
    one or not. """
    form = SelfReviewForm(request.form)
    if form.validate_on_submit():
        # update the outcome of the attempt in the database
        attempt = Attempt.query.filter_by(id=form.attempt_id.data).first()

        if form.yes.data:
            # user reported they got it correct so show them difficulty rating form
            attempt.correct = True
            db.session.commit()
            difficulty_form = DifficultyForm(attempt_id=form.attempt_id.data)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form)

        else:
            # user reported they were wrong
            attempt.correct = False
            sm2_update(attempt, 2) # they made an attempt but were wrong so set difficulty to 2
            db.session.commit()

            flash("Keep your chin up, cadet. We'll test you on that question again tomorrow.", "danger")
            return redirect(url_for('.test'))

    attempt = Attempt.query.filter_by(id=form.attempt_id.data).first()
    prompt_html = markdown_to_html(attempt.question.prompt)
    answer_html = markdown_to_html(attempt.question.answer)

    return render_template("self_verify.html",
                           page_title="Cadet Test: Self Verification",
                           form=form,
                           prompt=Markup(prompt_html),
                           response=attempt.response,
                           correct_answer=Markup(answer_html))


def get_last_attempt(user_id, question_id):
    return Attempt.query.filter(Attempt.user_id == user_id,
                                Attempt.question_id == question_id).order_by(
                                    Attempt.time.desc()).first()

def sm2_update(attempt, quality):
    """ Updates the attempt's e_factor and interval based on the quality of
    their most recent answer. """

    print("Setting quality to", quality)
    attempt.quality = quality

    if quality < 3:
        # The question wasn't answered incorrectly. Keep the same e_factor as
        # before and set the interval to 1 (i.e. like learning from new)
        attempt.interval = 1

    else:
        attempt.e_factor += 0.1 - ((5-quality) * (0.08 + ((5-quality) * 0.02)))

        # set a floor for the e_factor
        if attempt.e_factor < 1.3:
            attempt.e_factor = 1.3

        # They got the correct answer, so interval increases
        attempt.interval = 6 if attempt.interval == 1 else ceil(attempt.interval * attempt.e_factor)

    # next attempt will be interval days from today
    attempt.next_attempt = date.today() + timedelta(days=attempt.interval)


@user_views.route('/test/multiple-choice', methods=['POST'])
@login_required
def test_multiple_choice():
    # FIXME: code duplication in this function

    form = MultipleChoiceForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()
    form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in original_question.options]
    form.response.choices.append((-1, "I Don't Know"))

    if form.validate_on_submit():
        # grab the last attempt (before creating a new attempt which will be
        # the new "last" attempt
        previous_attempt = get_last_attempt(current_user.id, original_question_id)

        # add the attempt to the database
        attempt = SelectionAttempt(question_id=original_question_id,
                                   user_id=current_user.id)

        # Get the selected answer.
        answer_id = form.response.data
        selected_answer = AnswerOption.query.filter_by(id=answer_id).first()

        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval

        if selected_answer:
            # no selected answer means they didn't have a response (i.e. "I
            # Don't Know" was their answer)
            attempt.response = selected_answer

        db.session.add(attempt)
        db.session.commit() # TRICKY: default values for e-factor/interval not set until commit

        if selected_answer and selected_answer.correct:
            # if correct, send them off to the self rating form
            attempt.correct = True
            db.session.commit()
            difficulty_form = DifficultyForm(attempt_id=attempt.id)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form)

        else:
            attempt.correct = False

            if selected_answer:
                sm2_update(attempt, 2)  # they made an attempt but were wrong so set response quality to 2
            else:
                sm2_update(attempt, 1)  # no attempt ("I Don't Know"), so set response quality to 1

            db.session.commit()

            # show the user a page where they can view the correct answer
            prompt_html = markdown_to_html(original_question.prompt)

            correct_option = original_question.options.filter_by(correct=True).first()
            answer_html = markdown_to_html(correct_option.text)

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))

    # FIXME: display multiple choice form again
    return "FAIL"

@user_views.route('/test/short-answer', methods=['POST'])
@login_required
def test_short_answer():
    form = ShortAnswerForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()

    prompt_html = markdown_to_html(original_question.prompt)
    answer_html = markdown_to_html(original_question.answer)

    if form.validate_on_submit():
        # check for a previous attempt
        previous_attempt = Attempt.query.filter(Attempt.user_id == current_user.id,
                                                Attempt.question_id == original_question_id).order_by(
                                                    Attempt.time.desc()).first()

        # add the attempt to the database (leaving the outcome undefined for
        # now)
        attempt = TextAttempt(response=form.response.data,
                              question_id=original_question_id,
                              user_id=current_user.id)

        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval

        db.session.add(attempt)
        db.session.commit() # TRICKY: need to commit to get default e_factor and interval

        if form.no_answer.data:
            # No response from user ("I Don't Know"), which is response
            # quality 1 in SM-2
            sm2_update(attempt, 1)
            db.session.commit()

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))

        # create the self review_form
        review_form = SelfReviewForm(attempt_id=attempt.id)


        return render_template("self_verify.html",
                               page_title="Cadet Test: Self Verification",
                               form=review_form,
                               prompt=Markup(prompt_html),
                               response=form.response.data,
                               correct_answer=Markup(answer_html))

    # FIXME: set fresh_question appropriately below
    return render_template("test_short_answer.html",
                           page_title="Cadet Test",
                           form=form,
                           prompt=Markup(prompt_html))


def get_answer_html(jumble_question):
    """ Returns HTML for the answer to the given jumble question. """

    answer_html = "<ul class=\"list-unstyled jumble\">"
    for block in jumble_question.blocks.filter(JumbleBlock.correct_index >= 0).order_by(
            JumbleBlock.correct_index):
        block_html = block.html()
        indent_amount = (block.correct_indent * 20) + 15
        answer_html += f"<li style=\"padding-left: {indent_amount}px;\">{block_html}</li>"

    answer_html += "</ul>"

    return answer_html

@user_views.route('/test/code-jumble', methods=['POST'])
@login_required
def test_code_jumble():
    form = CodeJumbleForm(request.form)
    question_id = form.question_id.data
    question = Question.query.filter_by(id=question_id).first()

    if form.validate_on_submit():
        # grab the last attempt (before creating a new attempt which will be
        # the new "last" attempt
        previous_attempt = get_last_attempt(current_user.id, question_id)

        # add the attempt to the database
        attempt = TextAttempt(question_id=question_id,
                              user_id=current_user.id)

        # Get the selected answer.
        response_str = form.response.data
        attempt.response = response_str


        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval

        # TODO: allow a "don't know" response

        db.session.add(attempt)
        db.session.commit() # TRICKY: default values for e-factor/interval not set until commit

        if form.no_answer.data:
            # No response from user ("I Don't Know"), which is response
            # quality 1 in SM-2
            sm2_update(attempt, 1)
            db.session.commit()

            prompt_html = markdown_to_html(question.prompt)
            answer_html = get_answer_html(question)

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))


        try:
            user_response = ast.literal_eval(response_str)
        except:
            # if we couldn't parse the response, we're in trouble
            abort(500)

        correct_response = question.get_correct_response()

        if correct_response == user_response:
            # if correct, send them off to the self rating form
            attempt.correct = True
            db.session.commit()
            difficulty_form = DifficultyForm(attempt_id=attempt.id)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form)

        else:
            attempt.correct = False

            sm2_update(attempt, 2)  # they made an attempt but were wrong so set response quality to 2
            db.session.commit()

            # show the user a page where they can view the correct answer
            prompt_html = markdown_to_html(question.prompt)

            answer_html = get_answer_html(question)

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))

    return "FAIL"

@user_views.route('/test')
@login_required
def test():
    """ Presents a random question to the user. """

    # get all the questions from section's that this user is enrolled in
    possible_questions = Question.query.join(
        enrollments, (enrollments.c.section_id == Question.section_id)).filter(
            enrollments.c.user_id == current_user.id)

    # find questions that haven't been attempted yet, as these will be part of
    # the pool of questions we can ask them
    unattempted_questions = possible_questions.filter(~ Question.attempts.any(Attempt.user_id == current_user.id))

    # Find questions whose next attempt is before today, as these will also be
    # part of the pool of questions to ask

    latest_next_attempts = db.session.query(
        Attempt.question_id, Attempt.next_attempt, db.func.max(Attempt.next_attempt).label('latest_next_attempt_time')
    ).group_by(Attempt.question_id).filter(Attempt.user_id == current_user.id).subquery()

    target_time = datetime.now()
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

    # question is "fresh" if it hasn't been attempted yet today
    fresh_question = True

    if not question:
        # There weren't any "new" questions (i.e. those the user hasn't
        # already attempted today). Look for questions that they attempted
        # today but whose quality was 3 or less.

        today = datetime.combine(date.today(), datetime.min.time())
        attempted_today = possible_questions.filter(Question.attempts.any(Attempt.time >= today))
        needs_reps = attempted_today.filter(~ Question.attempts.any(Attempt.quality > 3))

        """
        print("Questions That Need MORE Reps:")
        for q in needs_reps:
            print("\t", q)
        """

        question = needs_reps.order_by(db.func.random()).first()
        fresh_question = False

        if not question:
            # No questions that need more reps today so display a "congrats"
            # page for the user.
            return render_template("completed.html",
                                   page_title="Cadet: Complete")

    if question.type == QuestionType.SHORT_ANSWER:
        form = ShortAnswerForm(question_id=question.id)
        prompt_html = markdown_to_html(question.prompt)
        return render_template("test_short_answer.html",
                               page_title="Cadet Test",
                               fresh_question=fresh_question,
                               form=form,
                               prompt=Markup(prompt_html))

    elif question.type == QuestionType.MULTIPLE_CHOICE:
        form = MultipleChoiceForm(question_id=question.id)
        form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        form.response.choices.append((-1, "I Don't Know"))

        prompt_html = markdown_to_html(question.prompt)

        return render_template("test_multiple_choice.html",
                               page_title="Cadet Test",
                               fresh_question=fresh_question,
                               form=form,
                               prompt=Markup(prompt_html))

    elif question.type == QuestionType.CODE_JUMBLE:
        form = CodeJumbleForm(question_id=question.id, response="")
        prompt_html = markdown_to_html(question.prompt)
        code_blocks = [(b.id, Markup(b.html())) for b in question.blocks]

        return render_template("test_code_jumble.html",
                               page_title="Cadet Test",
                               fresh_question=fresh_question,
                               form=form,
                               prompt=Markup(prompt_html),
                               code_blocks=code_blocks)
    else:
        return "UNSUPPORTED QUESTION TYPE"


class DataRequiredIf(DataRequired):
    # a validator which makes a field required if another field is set and has
    # a truthy value

    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(DataRequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if bool(other_field.data):
            super(DataRequiredIf, self).__call__(form, field)


class DifficultyForm(FlaskForm):
    """ Form to report the difficulty they had in answering a question. """
    attempt_id = HiddenField("Attempt ID")
    difficulty = RadioField('Difficulty',
                             choices=[(5, "Easy: The info was easy to recall"),
                                      (4, 'Medium: I had to take a moment to recall something'),
                                      (3, 'Hard: I barely recalled the info I needed.')],
                             coerce=int)
    submit = SubmitField("Submit")


class SelfReviewForm(FlaskForm):
    attempt_id = HiddenField("Attempt ID")
    yes = SubmitField("Yes")
    no = SubmitField("No")


class ShortAnswerForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = TextAreaField('answer', validators=[DataRequiredIf('submit')])
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")

class CodeJumbleForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = HiddenField("Ordered Code")
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")


class MultipleChoiceForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = RadioField('answer', validators=[InputRequired()], coerce=int)
    submit = SubmitField("Submit")


from app.db_models import (
    Question, Attempt, enrollments, QuestionType, AnswerOption,
    TextAttempt, SelectionAttempt, JumbleBlock
)
