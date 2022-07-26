from flask import (
    Blueprint, render_template, url_for, redirect, flash, request, Markup,
    abort
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    RadioField, FieldList, SelectMultipleField
)
from wtforms.widgets import (ListWidget, CheckboxInput)
from wtforms.validators import (
    DataRequired, InputRequired, ValidationError
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


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/rating',
                  methods=['GET', 'POST'])
@login_required
def difficulty(course_name, mission_id):
    """ Route to handle self-reported difficulty of a problem that the user
    got correct. """

    course = check_course_authorization(course_name)
    mission = check_mission_inclusion(mission_id, course)

    attempt_id = request.args.get("attempt")
    if not attempt_id:
        abort(404)

    # TODO: check that attempt is for a question in this mission

    form = DifficultyForm()

    if form.validate_on_submit():
        # get the question and update it's interval and e_factor
        a = Attempt.query.filter_by(id=int(attempt_id)).first()

        if not a:
            abort(404)
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
                           form=form)


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/self-grade',
                  methods=['GET', 'POST'])
@login_required
def self_review(course_name, mission_id):
    """ Route for the student to self-grade their answer. """

    course = check_course_authorization(course_name)
    mission = check_mission_inclusion(mission_id, course)

    attempt_id = request.args.get("attempt")
    if not attempt_id:
        abort(404)

    # TODO: check that attempt is part of the given mission

    form = SelfReviewForm()
    attempt = Attempt.query.filter_by(id=int(attempt_id)).first()

    if not attempt:
        abort(404)
    elif attempt.user != current_user:
        abort(401)

    if form.validate_on_submit():
        # update the outcome of the attempt in the database

        if form.yes.data:
            # user reported they got it correct so show them difficulty rating form
            attempt.correct = True
            db.session.commit()

            return redirect(url_for('.difficulty',
                                    course_name=course_name, mission_id=mission_id,
                                    attempt=attempt_id))


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
        
@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/review/lo/<int:lo_id>/3?') #3?n=2
@login_required
def review_questions(course_name, mission_id, lo_id, sequence_num, user):
    course = check_course_authorization(course_name)
    mission = check_mission_inclusion(mission_id, course)

    review_questions = review_questions(user.id, mission, 2.5) #remember to pass through the user in template

    question = review_questions[sequence_num]
    prompt_html = markdown_to_html(question.prompt)
    answer_html = question.get_answer()


    return render_template("review_correct_answer.html",
                           page_title="Cadet Review Center: Review Questions",
                           continue_url=url_for('.test',
                                                course_name=course_name,
                                                mission_id=mission_id),
                           prompt=Markup(prompt_html),
                           answer=Markup(answer_html),
                           review = True)


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train/review')
@login_required
def review_answer(course_name, mission_id):
    course = check_course_authorization(course_name)
    mission = check_mission_inclusion(mission_id, course)

    attempt_id = request.args.get("attempt")
    if not attempt_id:
        # TODO: redirect here instead of 404?
        abort(404)

    # TODO: check that attempt is part of the given mission

    attempt = Attempt.query.filter_by(id=int(attempt_id)).first()
    if not attempt:
        abort(404)

    question = attempt.question

    prompt_html = markdown_to_html(question.prompt)
    answer_html = question.get_answer()

    response_html = ""

    if question.type == QuestionType.MULTIPLE_SELECTION:
        for option in attempt.responses:
            response_html += markdown_to_html(option.text) + "\n"
    elif question.type == QuestionType.CODE_JUMBLE:
        response_html = "<ul class=\"list-unstyled jumble\">"
        user_response = ast.literal_eval(attempt.response)
        for block in user_response:
            jumble_block = JumbleBlock.query.filter(JumbleBlock.id == int(block[0]),
                                                    JumbleBlock.question_id == int(question.id)).first()
            language_str = "" if not question.language else question.language
            code_str = f"```{language_str}\n{jumble_block.code}\n```\n"
            block_html = markdown_to_html(code_str, code_linenums=False)
            indent_amount = (block[1]* 20) + 15
            response_html += f"<li style=\"padding-left: {indent_amount}px;\">{block_html}</li>"
        response_html += "</ul>"
    elif question.type == QuestionType.MULTIPLE_CHOICE:
        selected_answer = attempt.responses.first()
        response_html = markdown_to_html(selected_answer)
    else: #question.type = auto-check
        selected_answer = attempt.response.strip()
        response_html = markdown_to_html(selected_answer)

    return render_template("review_correct_answer.html",
                           page_title="Cadet Test: Review Correct Answer",
                           continue_url=url_for('.test',
                                                course_name=course_name,
                                                mission_id=mission_id),
                           prompt=Markup(prompt_html),
                           response = Markup(response_html),
                           answer=Markup(answer_html),
                           review = False)



def create_new_text_attempt(question, user, response, previous_attempt):
    """ Creates a new attempt and adds it to the database. If there was a
    previous attempt for the question, copy over the relevent data to the new
    attempt. """
    attempt = TextAttempt(question_id=question.id,
                          user_id=user.id,
                          response=response)

    # if there was a previous attempt, copy over e_factor and interval
    if previous_attempt:
        attempt.e_factor = previous_attempt.e_factor
        attempt.interval = previous_attempt.interval
        attempt.next_attempt = previous_attempt.next_attempt

    db.session.add(attempt)
    db.session.commit()

    return attempt

def create_new_selection_attempt(question, user, responses, previous_attempt):
    """ Creates a new selection attempt and adds it to the database. If there
    was a previous attempt for the question, copy over the relevent data to
    the new attempt. """
    attempt = SelectionAttempt(question_id=question.id,
                               user_id=user.id)

    for r in responses:
        attempt.responses.append(r)

    # if there was a previous attempt, copy over e_factor and interval
    if previous_attempt:
        attempt.e_factor = previous_attempt.e_factor
        attempt.interval = previous_attempt.interval
        attempt.next_attempt = previous_attempt.next_attempt

    db.session.add(attempt)
    db.session.commit()

    return attempt


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


def get_next_question(assessment):
    """ Finds the next question to present to the student. Returns the
    question (or None if there is no more questions to train for) and whether
    the question is 'fresh' or a repeat. """

    # set the question bank based on whether there are fresh questions or not
    fresh_questions = assessment.fresh_questions(current_user).order_by(db.func.random())

    if fresh_questions.count() != 0:
        return fresh_questions.first(), True

    repeat_questions = assessment.repeat_questions(current_user).order_by(db.func.random())

    if repeat_questions.count() != 0:
        return repeat_questions.first(), False
    else:
        return None, None


def get_form(question, use_existing):
    kwargs = {}
    if not use_existing:
        kwargs['question_id'] = question.id

    if question.type == QuestionType.SHORT_ANSWER:
        return ShortAnswerForm(**kwargs)

    elif question.type == QuestionType.AUTO_CHECK:
        return AutoCheckForm(**kwargs)

    elif question.type == QuestionType.MULTIPLE_CHOICE:
        form = MultipleChoiceForm(**kwargs)
        form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        return form

    elif question.type == QuestionType.MULTIPLE_SELECTION:
        form = MultipleSelectionForm(**kwargs)
        form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        return form

    elif question.type == QuestionType.CODE_JUMBLE:
        return CodeJumbleForm(response="", **kwargs)

    else:
        # TODO: log error
        abort(400)


def render_question(question, is_fresh, form, mission):
    prompt_html = markdown_to_html(question.prompt)

    extra_kw_args = {}

    if question.type == QuestionType.SHORT_ANSWER:
        #form = ShortAnswerForm(question_id=question.id)
        template_filename = "test_short_answer.html"

    elif question.type == QuestionType.AUTO_CHECK:
        #form = AutoCheckForm(question_id=question.id)
        template_filename = "test_short_answer.html"

    elif question.type == QuestionType.MULTIPLE_CHOICE:
        #form = MultipleChoiceForm(question_id=question.id)
        #form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        template_filename = "test_multiple_choice.html"

    elif question.type == QuestionType.MULTIPLE_SELECTION:
        #form = MultipleSelectionForm(question_id=question.id)
        #form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        template_filename = "test_multiple_choice.html"

    elif question.type == QuestionType.CODE_JUMBLE:
        #form = CodeJumbleForm(question_id=question.id, response="")
        template_filename = "test_code_jumble.html"
        extra_kw_args['code_blocks'] = [(b.id, Markup(b.html())) for b in question.blocks]

    else:
        # TODO: log error
        abort(400)
        
    return render_template(template_filename,
                           page_title="Cadet: Mission Training",
                           fresh_question=is_fresh,
                           post_url="",
                           form=form,
                           prompt=Markup(prompt_html),
                           mission = mission,
                           **extra_kw_args)


@user_views.route('/c/<course_name>/mission/<int:mission_id>/train',
                  methods=['GET', 'POST'])
@login_required
def test(course_name, mission_id):
    """ Presents a random question to the user. """

    course = check_course_authorization(course_name)
    mission = check_mission_inclusion(mission_id, course)

    if request.method == 'GET':
        question, fresh_question = get_next_question(mission)

        if question is None:
            # Training is done (for today) so display a congrats/completed page
            topics_to_review=mission.objectives_to_review(current_user)
            new_list_of_topics = [ topic[0] for topic in topics_to_review ]
            return render_template("completed.html",
                                   page_title="Cadet: Complete",
                                   course_name=course_name,
                                   mission = mission,
                                   breakdown_today=mission.breakdown_today(current_user),
                                   topics_to_review=new_list_of_topics)
        else:
            form = get_form(question, False)

    else:
        try:
            question_id = int(request.form['question_id'])
        except:
            abort(400)

        question = Question.query.filter_by(id=question_id).first()

        previous_attempt = get_last_attempt(current_user.id, question_id)
        repeated = is_a_repeat(previous_attempt)
        fresh_question = not repeated

        form = get_form(question, True)

        if form.validate_on_submit():
            attempt = form.create_attempt(question, current_user,
                                          previous_attempt)

            if form.no_answer.data:
                # User indicated they didn't know the answer, which we will
                # consider a quality 1 response in SM-2
                attempt.correct = False
                attempt.sm2_update(1, repeat_attempt=repeated)
                db.session.commit()

                return redirect(url_for('.review_answer',
                                        course_name=course_name,
                                        mission_id=mission_id,
                                        selected_answer=Markup("<i>No answer given</i>"),
                                        attempt=attempt.id))

            # if this is a self-graded question, send them to the review page
            if question.type == QuestionType.SHORT_ANSWER:
                return redirect(url_for('.self_review',
                                        course_name=course_name, mission_id=mission_id,
                                        attempt=attempt.id))

            # Other question types can be graded automatically 
            if question.type == QuestionType.AUTO_CHECK:
                user_response = attempt.response.strip()
                attempt.correct = attempt.response.strip() == question.answer

            elif question.type == QuestionType.MULTIPLE_CHOICE:
                attempt.correct = attempt.responses.filter_by(correct=True).count() == 1
                #AnswerOption.query.filter_by(id=form.response.data).first().correct
                user_response = attempt.responses

            elif question.type == QuestionType.MULTIPLE_SELECTION:
                correct_answers = question.options.filter_by(correct=True).order_by(AnswerOption.id).all()
                user_response = attempt.responses.order_by(AnswerOption.id).all()
                attempt.correct = user_response == correct_answers

            elif question.type == QuestionType.CODE_JUMBLE:
                try:
                    user_response = ast.literal_eval(attempt.response)
                except:
                    # if we couldn't parse the response, we're in trouble
                    abort(400)

                correct_response = question.get_correct_response()
                attempt.correct = correct_response == user_response

            else:
                abort(400)

            if attempt.correct:
                db.session.commit()
                return redirect(url_for('.difficulty',
                                        course_name=course_name,
                                        mission_id=mission_id,
                                        attempt=attempt.id))

            else:
                # they made an attempt but were wrong so set response quality to 2
                attempt.sm2_update(2, repeat_attempt=repeated)
                db.session.commit()

                return redirect(url_for('.review_answer',
                                        course_name=course_name,
                                        mission_id=mission_id,
                                        attempt=attempt.id))

    return render_question(question, fresh_question, form, mission)


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
    difficulty = RadioField('Difficulty',
                             choices=[(5, "Easy: The info was easy to recall"),
                                      (4, 'Medium: I had to take a moment to recall something'),
                                      (3, 'Hard: I barely recalled the info I needed.')],
                             coerce=int)
    submit = SubmitField("Submit")


class SelfReviewForm(FlaskForm):
    yes = SubmitField("Yes")
    no = SubmitField("No")


class TextResponseForm(FlaskForm):
    question_id = HiddenField("Question ID")
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")

    def create_attempt(self, question, user, previous_attempt):
        attempt = create_new_text_attempt(question, user,
                                          self.response.data,
                                          previous_attempt)

        return attempt

class ShortAnswerForm(TextResponseForm):
    response = TextAreaField('answer', validators=[DataRequiredIf('submit')])

class AutoCheckForm(TextResponseForm):
    response = StringField('answer', validators=[DataRequiredIf('submit')])

class CodeJumbleForm(TextResponseForm):
    response = HiddenField("Ordered Code")

class MultipleChoiceForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = RadioField('Select One', coerce=int, validate_choice=False)
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")

    def validate_response(form, field):
        """ Validate that user selected something if they clicked submit
        rather than no_answer. """
        if form.submit.data and (not field.data):
            raise ValidationError("Select one of the given options or click \"I Don't Know\"")

    def create_attempt(self, question, user, previous_attempt):
        if self.response.data:
            selected_response = AnswerOption.query.filter_by(id=self.response.data).all()
        else:
            selected_response = []

        attempt = create_new_selection_attempt(question, user,
                                               selected_response,
                                               previous_attempt)

        return attempt

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class MultipleSelectionForm(FlaskForm):
    question_id = HiddenField("Question ID")
    response = MultiCheckboxField('Select All That Apply', coerce=int)
    no_answer = SubmitField("I Don't Know")
    submit = SubmitField("Submit")

    def create_attempt(self, question, user, previous_attempt):
        if self.response.data:
            selected_response = AnswerOption.query.filter(AnswerOption.id.in_(self.response.data)).all()
        else:
            selected_response = []

        attempt = create_new_selection_attempt(question, user,
                                               selected_response,
                                               previous_attempt)

        return attempt

from app.db_models import (
    Question, Attempt, enrollments, QuestionType, AnswerOption, TextAttempt,
    SelectionAttempt, JumbleBlock, Course, Objective, User, Assessment
)

from app.auth import check_authorization, AuthorizationError