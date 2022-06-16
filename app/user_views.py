from flask import (
    Blueprint, render_template, url_for, redirect, flash, request, Markup,
    abort
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    RadioField,
)
from wtforms.validators import (
    DataRequired, InputRequired
)
from flask_login import current_user, login_required

import ast, markdown
from datetime import date, timedelta, datetime

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


def is_a_repeat(last_attempt):
    return (last_attempt is not None) and (last_attempt.time.date() == date.today())


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/rating', methods=['POST'])
@login_required
def difficulty(course_name, mission_id):
    """ Route to handle self-reported difficulty of a problem that the user
    got correct. """

    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = DifficultyForm(request.form)

    if form.validate_on_submit():
        # get the question and update it's interval and e_factor
        a = Attempt.query.filter_by(id=form.attempt_id.data).first()

        if not a:
            abort(400)
        elif a.user != current_user:
            abort(401)

        previous_attempt = Attempt.query.filter(Attempt.user_id == a.user_id,
                                                Attempt.question_id == a.question_id,
                                                Attempt.time < a.time)\
                                        .order_by(Attempt.time.desc()).first()

        repeated = is_a_repeat(previous_attempt)

        a.sm2_update(form.difficulty.data, repeat_attempt=repeated)
        db.session.commit()

        return redirect(url_for('.test',
                                course_name=course_name,
                                mission_id=mission_id))

    return render_template("difficulty.html",
                           page_title="Cadet Test: Rating",
                           form=form,
                           post_url=url_for('.difficulty',
                                            course_name=course_name,
                                            mission_id=mission_id))


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/review', methods=['POST'])
@login_required
def self_review(course_name, mission_id):
    """ User will self-verify whether the answer they submitted is the correct
    one or not. """

    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = SelfReviewForm(request.form)
    attempt = Attempt.query.filter_by(id=form.attempt_id.data).first()

    if not attempt:
        abort(400)
    elif attempt.user != current_user:
        abort(401)

    if form.validate_on_submit():
        # update the outcome of the attempt in the database

        if form.yes.data:
            # user reported they got it correct so show them difficulty rating form
            attempt.correct = True
            db.session.commit()
            difficulty_form = DifficultyForm(attempt_id=form.attempt_id.data)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form,
                                   post_url=url_for('.difficulty',
                                                    course_name=course_name,
                                                    mission_id=mission_id))

        else:
            # user reported they were wrong
            attempt.correct = False

            previous_attempt = Attempt.query.filter(Attempt.user_id == attempt.user_id,
                                                    Attempt.question_id == attempt.question_id,
                                                    Attempt.time < attempt.time)\
                                            .order_by(Attempt.time.desc()).first()

            repeated = is_a_repeat(previous_attempt)

            # they made an attempt but were wrong so set difficulty to 2
            attempt.sm2_update(2, repeat_attempt=repeated)
            db.session.commit()

            flash("Keep your chin up, cadet. We'll test you on that question again tomorrow.", "danger")
            return redirect(url_for('.test',
                                    course_name=course_name,
                                    mission_id=mission_id))

    prompt_html = markdown_to_html(attempt.question.prompt)
    answer_html = markdown_to_html(attempt.question.answer)

    return render_template("self_verify.html",
                           page_title="Cadet Test: Self Verification",
                           course_name=course_name,
                           form=form,
                           post_url="", # same as current route!
                           prompt=Markup(prompt_html),
                           response=attempt.response,
                           correct_answer=Markup(answer_html))


# TODO: move this to be a method in Question (or student?) class
def get_last_attempt(user_id, question_id):
    return Attempt.query.filter(Attempt.user_id == user_id,
                                Attempt.question_id == question_id)\
                        .order_by(Attempt.time.desc()).first()


def check_course_authorization(course_name):
    """ Checks that course with given name exists and that the current user is
    part of the course. Returns the Course object or aborts if either of those
    are not true. """
    course = Course.query.filter_by(name=course_name).first()

    if not course:
        abort(404)
    try:
        check_authorization(current_user, course=course)
    except AuthorizationError:
        abort(401)
    else:
        return course

def check_mission_inclusion(mission_id, course):
    """ Checks that an assessment (a.k.a. mission) with the given id exists
    and is part of the course. Returns the Assessment object or aborts if
    either of those checks fails. """

    mission = course.assessments.filter_by(id=mission_id).first()

    if not mission:
        abort(404)
    else:
        return mission

@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/multiple-selection', methods=['POST'])
@login_required
def test_multiple_selection(course_name, mission_id):
    # TODO: code duplication in this function
    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = MultipleSelectionForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()

    if not original_question:
        abort(400)

    form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in original_question.options]
    form.response.choices.append((-1, "I Don't Know"))

    # grab the last attempt (before creating a new attempt which will be
    # the new "last" attempt
    previous_attempt = get_last_attempt(current_user.id, original_question_id)

    # determine if this question is repeated from earlier today
    repeated = is_a_repeat(previous_attempt)

    if form.validate_on_submit():

        # add the attempt to the database
        attempt = SelectionAttempt(question_id=original_question_id,
                                   user_id=current_user.id)

        # Get the selected answer.
        answer_id = form.response.data # research this for multiple answers on wtforms
        selected_answer = AnswerOption.query.filter_by(id=answer_id).first()

        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval
            attempt.next_attempt = previous_attempt.next_attempt

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
                                   form=difficulty_form,
                                   post_url=url_for('.difficulty',
                                                    course_name=course_name,
                                                    mission_id=mission_id))

        else:
            attempt.correct = False

            if selected_answer:
                # they made an attempt but were wrong so set response quality to 2
                attempt.sm2_update(2, repeat_attempt=repeated)
            else:
                # no attempt ("I Don't Know"), so set response quality to 1
                attempt.sm2_update(1, repeat_attempt=repeated)

            db.session.commit()

            # show the user a page where they can view the correct answer
            prompt_html = markdown_to_html(original_question.prompt)

            correct_option = original_question.options.filter_by(correct=True).first()
            answer_html = markdown_to_html(correct_option.text)

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))


    prompt_html = markdown_to_html(original_question.prompt)

    return render_template("test_multiple_choice.html",
                           page_title="Cadet Test",
                           course_name=course_name,
                           fresh_question=(not repeated),
                           form=form,
                           post_url="", # same url as current so can leave this blank
                           prompt=Markup(prompt_html))



@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/multiple-choice', methods=['POST'])
@login_required
def test_multiple_choice(course_name, mission_id):

    # TODO: code duplication in this function
    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = MultipleChoiceForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()

    if not original_question:
        abort(400)

    form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in original_question.options]
    form.response.choices.append((-1, "I Don't Know"))

    # grab the last attempt (before creating a new attempt which will be
    # the new "last" attempt
    previous_attempt = get_last_attempt(current_user.id, original_question_id)

    # determine if this question is repeated from earlier today
    repeated = is_a_repeat(previous_attempt)

    if form.validate_on_submit():

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
            attempt.next_attempt = previous_attempt.next_attempt

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
                                   form=difficulty_form,
                                   post_url=url_for('.difficulty',
                                                    course_name=course_name,
                                                    mission_id=mission_id))

        else:
            attempt.correct = False

            if selected_answer:
                # they made an attempt but were wrong so set response quality to 2
                attempt.sm2_update(2, repeat_attempt=repeated)
            else:
                # no attempt ("I Don't Know"), so set response quality to 1
                attempt.sm2_update(1, repeat_attempt=repeated)

            db.session.commit()

            # show the user a page where they can view the correct answer
            prompt_html = markdown_to_html(original_question.prompt)

            correct_option = original_question.options.filter_by(correct=True).first()
            answer_html = markdown_to_html(correct_option.text)

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))


    prompt_html = markdown_to_html(original_question.prompt)

    return render_template("test_multiple_choice.html",
                           page_title="Cadet Test",
                           course_name=course_name,
                           fresh_question=(not repeated),
                           form=form,
                           post_url="", # same url as current so can leave this blank
                           prompt=Markup(prompt_html))


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/short-answer', methods=['POST'])
@login_required
def test_short_answer(course_name, mission_id):
    """ Checks answer given to a short answer question. """

    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = ShortAnswerForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()

    if not original_question:
        abort(400)

    prompt_html = markdown_to_html(original_question.prompt)
    answer_html = markdown_to_html(original_question.answer)

    previous_attempt = get_last_attempt(current_user.id, original_question_id)

    # determine if this question is repeated from earlier today
    repeated = is_a_repeat(previous_attempt)

    if form.validate_on_submit():

        # add the attempt to the database (leaving the outcome undefined for
        # now)
        attempt = TextAttempt(response=form.response.data,
                              question_id=original_question_id,
                              user_id=current_user.id)

        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval
            attempt.next_attempt = previous_attempt.next_attempt

        db.session.add(attempt)
        db.session.commit() # TRICKY: need to commit to get default e_factor and interval

        if form.no_answer.data:
            # No response from user ("I Don't Know"), which is response
            # quality 1 in SM-2
            attempt.sm2_update(1, repeat_attempt=repeated)
            db.session.commit()

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))

        review_form = SelfReviewForm(attempt_id=attempt.id)

        return render_template("self_verify.html",
                               page_title="Cadet Test: Self Verification",
                               course_name=course_name,
                               form=review_form,
                               post_url=url_for('.self_review',
                                                course_name=course_name,
                                                mission_id=mission_id),
                               prompt=Markup(prompt_html),
                               response=form.response.data,
                               correct_answer=Markup(answer_html))

    return render_template("test_short_answer.html",
                           page_title="Cadet Test",
                           post_url=url_for(".test_short_answer",
                                            course_name=course_name,
                                            mission_id=mission_id),
                           fresh_question=(not repeated),
                           form=form,
                           prompt=Markup(prompt_html))


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/auto-check', methods=['POST'])
@login_required
def test_auto_check(course_name, mission_id):
    """ Checks the correctness of an auto-check type of question. """

    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = AutoCheckForm(request.form)
    original_question_id = form.question_id.data
    original_question = Question.query.filter_by(id=original_question_id).first()

    if not original_question:
        abort(400)

    prompt_html = markdown_to_html(original_question.prompt)

    previous_attempt = get_last_attempt(current_user.id, original_question_id)

    # determine if this question is repeated from earlier today
    repeated = is_a_repeat(previous_attempt)

    if form.validate_on_submit():
        # add the attempt to the database (leaving the outcome undefined for
        # now)
        attempt = TextAttempt(response=form.response.data,
                              question_id=original_question_id,
                              user_id=current_user.id)

        # if there was a previous attempt, copy over e_factor and interval
        if previous_attempt:
            attempt.e_factor = previous_attempt.e_factor
            attempt.interval = previous_attempt.interval
            attempt.next_attempt = previous_attempt.next_attempt

        db.session.add(attempt)
        db.session.commit() # TRICKY: need to commit to get default e_factor and interval

        if form.no_answer.data:
            # No response from user ("I Don't Know"), which is response
            # quality 1 in SM-2
            attempt.correct = False
            attempt.sm2_update(1, repeat_attempt=repeated)
            db.session.commit()

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=original_question.answer)

        # check whether they got it correct or not
        user_response = attempt.response.strip()
        if user_response == original_question.answer:
            # The user was correct so send them to the form to rate the
            # quality of their response.
            attempt.correct = True
            db.session.commit()

            difficulty_form = DifficultyForm(attempt_id=attempt.id)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form,
                                   post_url=url_for('.difficulty',
                                                    course_name=course_name,
                                                    mission_id=mission_id))

        else:
            # User was wrong so show them the correct answer
            attempt.correct = False
            attempt.sm2_update(2, repeat_attempt=repeated)
            db.session.commit()

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=original_question.answer)


    return render_template("test_short_answer.html",
                           page_title="Cadet Test",
                           post_url=url_for(".test_auto_check",
                                            course_name=course_name,
                                            mission_id=mission_id),
                           fresh_question=(not repeated),
                           form=form,
                           prompt=Markup(prompt_html))


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/code-jumble', methods=['POST'])
@login_required
def test_code_jumble(course_name, mission_id):
    """ Checks the correctness of a code jumble type of question. """

    course = check_course_authorization(course_name)
    check_mission_inclusion(mission_id, course)

    form = CodeJumbleForm(request.form)

    question_id = form.question_id.data
    question = Question.query.filter_by(id=question_id).first()

    if not question:
        abort(400)

    # check for a previous attempt
    previous_attempt = get_last_attempt(current_user.id, question_id)

    # determine if this question is repeated from earlier today
    repeated = is_a_repeat(previous_attempt)

    if form.validate_on_submit():
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
            attempt.next_attempt = previous_attempt.next_attempt

        db.session.add(attempt)
        db.session.commit() # TRICKY: default values for e-factor/interval not set until commit

        if form.no_answer.data:
            # No response from user ("I Don't Know"), which is response
            # quality 1 in SM-2
            attempt.sm2_update(1, repeat_attempt=repeated)
            db.session.commit()

            prompt_html = markdown_to_html(question.prompt)
            answer_html = question.get_answer()

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))


        try:
            user_response = ast.literal_eval(response_str)
        except:
            # if we couldn't parse the response, we're in trouble
            abort(400)

        correct_response = question.get_correct_response()

        if correct_response == user_response:
            # if correct, send them off to the self rating form
            attempt.correct = True
            db.session.commit()
            difficulty_form = DifficultyForm(attempt_id=attempt.id)
            return render_template("difficulty.html",
                                   page_title="Cadet Test: Rating",
                                   form=difficulty_form,
                                   post_url=url_for('.difficulty',
                                                    course_name=course_name,
                                                    mission_id=mission_id))

        else:
            attempt.correct = False

            # they made an attempt but were wrong so set response quality to 2
            attempt.sm2_update(2, repeat_attempt=repeated)
            db.session.commit()

            # show the user a page where they can view the correct answer
            prompt_html = markdown_to_html(question.prompt)
            answer_html = question.get_answer()

            return render_template("review_correct_answer.html",
                                   page_title="Cadet Test: Review",
                                   continue_url=url_for('.test',
                                                        course_name=course_name,
                                                        mission_id=mission_id),
                                   prompt=Markup(prompt_html),
                                   answer=Markup(answer_html))


    prompt_html = markdown_to_html(question.prompt)
    code_blocks = [(b.id, Markup(b.html())) for b in question.blocks]

    return render_template("test_code_jumble.html",
                           page_title="Cadet Test",
                           fresh_question=(not repeated),
                           form=form,
                           post_url=url_for('.test_code_jumble',
                                            course_name=course_name,
                                            mission_id=mission_id),
                           prompt=Markup(prompt_html),
                           code_blocks=code_blocks)


@user_views.route('/c/<course_name>')
@login_required
def course_overview(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)
    try:
        check_authorization(current_user, course=course)
    except AuthorizationError:
        abort(401)

    return render_template("course_overview.html",
                           page_title=f"Cadet: {course_name}",
                           course=course)


@user_views.route('/c/<course_name>/missions')
@login_required
def missions_overview(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)
    try:
        check_authorization(current_user, course=course)
    except AuthorizationError:
        abort(401)

    return render_template("missions_overview.html",
                           page_title=f"Cadet: {course_name} Missions",
                           course=course)


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train')
@login_required
def test(course_name, mission_id):
    """ Presents a random question to the user. """

    course = Course.query.filter_by(name=course_name).first()
    assessment = Assessment.query.filter_by(id=mission_id).first()
    if (not course) or (not assessment):
        abort(404)
    try:
        check_authorization(current_user, course=course)
    except AuthorizationError:
        abort(401)

    # set the question bank based on whether there are fresh questions or not
    questions = assessment.fresh_questions(current_user).order_by(db.func.random())
    fresh_question = True

    if questions.count() == 0:
        fresh_question = False
        questions = assessment.repeat_questions(current_user).order_by(db.func.random())

    if questions.count() == 0:
        # No questions that need more reps today so display a "congrats" page
        # for the user.
        return render_template("completed.html",
                               page_title="Cadet: Complete",
                               course_name=course_name)

    question = questions.first()

    if question.type == QuestionType.SHORT_ANSWER:
        form = ShortAnswerForm(question_id=question.id)
        prompt_html = markdown_to_html(question.prompt)
        return render_template("test_short_answer.html",
                               page_title="Cadet Test",
                               fresh_question=fresh_question,
                               post_url=url_for(".test_short_answer",
                                                course_name=course_name,
                                                mission_id=mission_id),
                               form=form,
                               prompt=Markup(prompt_html))

    elif question.type == QuestionType.AUTO_CHECK:
        form = AutoCheckForm(question_id=question.id)
        prompt_html = markdown_to_html(question.prompt)
        return render_template("test_short_answer.html",
                               page_title="Cadet Test",
                               fresh_question=fresh_question,
                               post_url=url_for(".test_auto_check",
                                                course_name=course_name,
                                                mission_id=mission_id),
                               form=form,
                               prompt=Markup(prompt_html))

    elif question.type == QuestionType.MULTIPLE_CHOICE:
        form = MultipleChoiceForm(question_id=question.id)
        form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        form.response.choices.append((-1, "I Don't Know"))

        prompt_html = markdown_to_html(question.prompt)

        return render_template("test_multiple_choice.html",
                               page_title="Cadet Test",
                               course_name=course_name,
                               fresh_question=fresh_question,
                               form=form,
                               post_url=url_for('.test_multiple_choice',
                                                course_name=course_name,
                                                mission_id=mission_id),
                               prompt=Markup(prompt_html))

    # ADDED THIS
    elif question.type == QuestionType.MULTIPLE_SELECTION:
        form = MultipleSelectionForm(question_id=question.id)
        form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        form.response.choices.append((-1, "I Don't Know"))

        prompt_html = markdown_to_html(question.prompt)

        return render_template("test_multiple_choice.html",
                                page_title="Cadet Test",
                                course_name=course_name,
                                fresh_question=fresh_question,
                                form=form,
                                post_url=url_for('.test_multiple_choice',
                                                course_name=course_name,
                                                mission_id=mission_id),
                                prompt=Markup(prompt_html))

    elif question.type == QuestionType.CODE_JUMBLE:
        form = CodeJumbleForm(question_id=question.id, response="")
        prompt_html = markdown_to_html(question.prompt)
        code_blocks = [(b.id, Markup(b.html())) for b in question.blocks]

        return render_template("test_code_jumble.html",
                               page_title="Cadet Test",
                               fresh_question=fresh_question,
                               form=form,
                               post_url=url_for('.test_code_jumble',
                                                course_name=course_name,
                                                mission_id=mission_id),
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


class AutoCheckForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = StringField('answer', validators=[DataRequiredIf('submit')])
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")


class CodeJumbleForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = HiddenField("Ordered Code")
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")


class MultipleChoiceForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = RadioField('Select One', validators=[InputRequired()], coerce=int)
    submit = SubmitField("Submit")

class MultipleSelectionForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = RadioField('Select All That Apply', coerce=int, render_kw={"type": "checkbox"})
    submit = SubmitField("Submit")

from app.db_models import (
    Question, Attempt, enrollments, QuestionType, AnswerOption, TextAttempt,
    SelectionAttempt, JumbleBlock, Course, Objective, User, Assessment
)

from app.auth import check_authorization, AuthorizationError
