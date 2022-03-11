from flask import (
    Blueprint, render_template, url_for, redirect, flash, request, abort,
    Markup
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    FieldList, FormField, IntegerField, BooleanField
)
from wtforms.validators import (
    DataRequired, InputRequired, NumberRange, ValidationError
)
from flask_login import current_user, login_required

from app import db
from app.user_views import (
    ShortAnswerForm, markdown_to_html, CodeJumbleForm, AutoCheckForm,
    MultipleChoiceForm
)

instructor = Blueprint('instructor', __name__)

@instructor.route('/q/<int:question_id>/preview')
@login_required
def preview_question(question_id):
    question = Question.query.filter_by(id=question_id).first()

    if not question:
        abort(404)

    page_title = "Cadet: Question Preview"

    if question.type == QuestionType.SHORT_ANSWER:
        form = ShortAnswerForm(question_id=question.id)
        prompt_html = markdown_to_html(question.prompt)
        return render_template("test_short_answer.html",
                               page_title=page_title,
                               preview_mode=True,
                               form=form,
                               prompt=Markup(prompt_html))

    elif question.type == QuestionType.AUTO_CHECK:
        form = AutoCheckForm(question_id=question.id)
        prompt_html = markdown_to_html(question.prompt)
        return render_template("test_short_answer.html",
                               page_title=page_title,
                               preview_mode=True,
                               form=form,
                               prompt=Markup(prompt_html))


    elif question.type == QuestionType.CODE_JUMBLE:
        form = CodeJumbleForm(question_id=question.id, response="")
        prompt_html = markdown_to_html(question.prompt)
        code_blocks = [(b.id, Markup(b.html())) for b in question.blocks]

        return render_template("test_code_jumble.html",
                               page_title=page_title,
                               preview_mode=True,
                               form=form,
                               prompt=Markup(prompt_html),
                               code_blocks=code_blocks)

    elif question.type == QuestionType.MULTIPLE_CHOICE:
        form = MultipleChoiceForm(question_id=question.id)
        form.response.choices = [(option.id, Markup(markdown_to_html(option.text))) for option in question.options]
        form.response.choices.append((-1, "I Don't Know"))

        prompt_html = markdown_to_html(question.prompt)

        return render_template("test_multiple_choice.html",
                               page_title=page_title,
                               preview_mode=True,
                               form=form,
                               prompt=Markup(prompt_html))

    else:
        abort(500)


@instructor.route('/c/<course_name>/new-question', methods=['GET', 'POST'])
@login_required
def create_new_question(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)

    form = NewQuestionForm(course_id=course.id)

    if form.validate_on_submit():
        if form.type.data == "short-answer":
            sa_form = NewShortAnswerQuestionForm(course_id=course.id,
                                                 prompt=form.prompt.data)
            return render_template("create_new_short_answer.html",
                                   page_title="Cadet: Create New Quesion (Short Answer)",
                                   form=sa_form)

        elif form.type.data == "auto-check":
            ac_form = NewAutoCheckQuestionForm(course_id=course.id,
                                               prompt=form.prompt.data)
            return render_template("create_new_auto_check.html",
                                   page_title="Cadet: Create New Quesion (Short Answer)",
                                   form=ac_form)

        elif form.type.data == "multiple-choice":
            mc_form = NewMultipleChoiceQuestionForm(course_id=course.id,
                                                    prompt=form.prompt.data)
            return render_template("create_new_multiple_choice.html",
                                   page_title="Cadet: Create New Quesion (Multiple Choice)",
                                   form=mc_form)

        elif form.type.data == "code-jumble":
            cj_form = NewJumbleQuestionForm(course_id=course.id,
                                            prompt=form.prompt.data)
            return render_template("create_new_code_jumble.html",
                                   page_title="Cadet: Create New Quesion (Code Jumble)",
                                   form=cj_form)
        else:
            flash("Unsupported question type.", "warning")

    return render_template("create_new_question.html",
                           page_title="Cadet: Create New Quesion",
                           form=form)

@instructor.route('/new-question/short-answer', methods=['POST'])
@login_required
def create_short_answer():
    form = NewShortAnswerQuestionForm(request.form)

    if form.validate_on_submit():
        course = Course.query.filter_by(id=form.course_id.data).first()
        if not course:
            abort(400)

        new_q = ShortAnswerQuestion(prompt=form.prompt.data,
                                    answer=form.answer.data)

        course.questions.append(new_q)
        current_user.authored_questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_name=course.name))

    return render_template("create_new_short_answer.html",
                           page_title="Cadet: Create New Quesion (Short Answer)",
                           form=form)


@instructor.route('/new-question/auto-check', methods=['POST'])
@login_required
def create_auto_check():
    form = NewAutoCheckQuestionForm(request.form)

    if form.validate_on_submit():
        course = Course.query.filter_by(id=form.course_id.data).first()
        if not course:
            abort(400)

        new_q = AutoCheckQuestion(prompt=form.prompt.data,
                                  answer=form.answer.data,
                                  regex=form.regex.data)

        course.questions.append(new_q)
        current_user.authored_questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_name=course.name))

    return render_template("create_new_audo_check.html",
                           page_title="Cadet: Create New Quesion (Short Answer)",
                           form=form)


@instructor.route('/new-question/multiple-choice', methods=['POST'])
@login_required
def create_multiple_choice():
    form = NewMultipleChoiceQuestionForm(request.form)

    if form.validate_on_submit():
        course = Course.query.filter_by(id=form.course_id.data).first()
        if not course:
            abort(400)

        new_q = MultipleChoiceQuestion(prompt=form.prompt.data)
        db.session.add(new_q)

        for option in form.options:
            ao = AnswerOption(text=option.text.data,
                              correct=option.correct.data)
            new_q.options.append(ao)

        course.questions.append(new_q)
        current_user.authored_questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_name=course.name))

    return render_template("create_new_multiple_choice.html",
                           page_title="Cadet: Create New Quesion (Multiple Choice)",
                           form=form)


@instructor.route('/new-question/jumble', methods=['POST'])
@login_required
def create_code_jumble():
    form = NewJumbleQuestionForm(request.form)

    if form.validate_on_submit():
        course = Course.query.filter_by(id=form.course_id.data).first()
        if not course:
            abort(400)

        new_q = CodeJumbleQuestion(prompt=form.prompt.data,
                                   language=form.language.data)
        db.session.add(new_q)

        for block in form.code_blocks:
            jb = JumbleBlock(code=block.code.data,
                             correct_index=block.correct_index.data,
                             correct_indent=block.correct_indent.data)
            new_q.blocks.append(jb)

        course.questions.append(new_q)
        current_user.authored_questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_name=course.name))

    return render_template("create_new_code_jumble.html",
                           page_title="Cadet: Create New Quesion (Code Jumble)",
                           form=form)


@instructor.route('/course/<course_name>/questions')
@login_required
def manage_questions(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)

    all_questions = course.questions.all()
    return render_template("manage_questions.html",
                           page_title="Cadet: Manage Course Questions",
                           course=course,
                           questions=all_questions)


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


class NewQuestionForm(FlaskForm):
    course_id = HiddenField("Course ID")
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    type = SelectField("Question Type",
                           validators=[InputRequired()],
                           choices=[
                               ('short-answer', "Short Answer (Self-Graded)"),
                               ('auto-check', "Short Answer (Auto-Graded)"),
                               ('multiple-choice', "Multiple Choice"),
                               ('code-jumble', "Code Jumble"),
                           ])
    submit = SubmitField("Continue...")


class NewShortAnswerQuestionForm(FlaskForm):
    course_id = HiddenField("Course ID")
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    answer = TextAreaField("Question Answer", [DataRequired()])
    submit = SubmitField("Continue...")


class NewAutoCheckQuestionForm(FlaskForm):
    course_id = HiddenField("Course ID")
    prompt = StringField("Question Prompt", [DataRequired()])
    answer = StringField("Question Answer", [DataRequired()])
    regex = BooleanField("Regex")
    submit = SubmitField("Continue...")


class McOptionForm(FlaskForm):
    text = StringField('Text', [DataRequired()])
    correct = BooleanField("Correct")


class NewMultipleChoiceQuestionForm(FlaskForm):
    course_id = HiddenField("Course ID")
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    options = FieldList(FormField(McOptionForm), min_entries=2)
    submit = SubmitField("Submit")

    def validate_options(self, field):
        """ Checks that correct indices go from 0 up to N-1 """
        num_correct = len([1 for option in field if option.correct.data])
        if num_correct != 1:
            raise ValidationError("Exactly one option should be marked as correct.")


class JumbleBlockForm(FlaskForm):
    code = TextAreaField('Code', [DataRequired()])
    correct_index = IntegerField('Correct Location')
    correct_indent = IntegerField('Correct Indentation',
                                  [NumberRange(min=0, max=4), InputRequired()])

class NewJumbleQuestionForm(FlaskForm):
    course_id = HiddenField("Course ID")
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    language = SelectField("Language",
                           validators=[InputRequired()],
                           choices=[('python', "Python")])
    code_blocks = FieldList(FormField(JumbleBlockForm), min_entries=2)
    submit = SubmitField("Submit")

    def validate_code_blocks(self, field):
        """ Checks that correct indices go from 0 up to N-1 """
        blocks_in_answer = [block.correct_index.data
                            for block in field
                                if block.correct_index.data >= 0]

        blocks_in_answer.sort()
        for i in range(len(blocks_in_answer)):
            if i not in blocks_in_answer:
                raise ValidationError(f"Missing a Code Block with Correct Location {i}")


from app.db_models import (
    AnswerOption, CodeJumbleQuestion, JumbleBlock, Course,
    ShortAnswerQuestion, AutoCheckQuestion, MultipleChoiceQuestion, Question,
    QuestionType
)
