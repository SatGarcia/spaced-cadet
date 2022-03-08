from flask import (
    Blueprint, render_template, url_for, redirect, flash, request, Markup,
    abort
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    RadioField,
    FieldList, FormField, IntegerField, BooleanField
)
from wtforms.validators import (
    DataRequired, InputRequired, NumberRange, ValidationError
)
from flask_login import current_user, login_required

import ast, markdown
from datetime import date, timedelta, datetime
from math import ceil

from app import db

instructor = Blueprint('instructor', __name__)

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

@instructor.route('/course/<int:course_id>/new-question', methods=['GET', 'POST'])
@login_required
def create_new_question(course_id):
    s = Section.query.filter_by(id=course_id).first()
    if not s:
        abort(404)

    form = NewQuestionForm(section_id=course_id)

    if form.validate_on_submit():
        if form.type.data == "short-answer":
            sa_form = NewShortAnswerQuestionForm(section_id=course_id,
                                                 prompt=form.prompt.data)
            return render_template("create_new_short_answer.html",
                                   page_title="Cadet: Create New Quesion (Short Answer)",
                                   form=sa_form)

        elif form.type.data == "auto-check":
            ac_form = NewAutoCheckQuestionForm(section_id=course_id,
                                               prompt=form.prompt.data)
            return render_template("create_new_auto_check.html",
                                   page_title="Cadet: Create New Quesion (Short Answer)",
                                   form=ac_form)

        elif form.type.data == "multiple-choice":
            mc_form = NewMultipleChoiceQuestionForm(section_id=course_id,
                                                    prompt=form.prompt.data)
            return render_template("create_new_multiple_choice.html",
                                   page_title="Cadet: Create New Quesion (Multiple Choice)",
                                   form=mc_form)

        elif form.type.data == "code-jumble":
            cj_form = NewJumbleQuestionForm(section_id=course_id,
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
        section = Section.query.filter_by(id=form.section_id.data).first()
        if not section:
            abort(400)

        new_q = ShortAnswerQuestion(prompt=form.prompt.data,
                                    answer=form.answer.data)

        section.questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_id=form.section_id.data))

    return render_template("create_new_short_answer.html",
                           page_title="Cadet: Create New Quesion (Short Answer)",
                           form=form)


@instructor.route('/new-question/auto-check', methods=['POST'])
@login_required
def create_auto_check():
    form = NewAutoCheckQuestionForm(request.form)

    if form.validate_on_submit():
        section = Section.query.filter_by(id=form.section_id.data).first()
        if not section:
            abort(400)

        new_q = AutoCheckQuestion(prompt=form.prompt.data,
                                  answer=form.answer.data,
                                  regex=form.regex.data)

        section.questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_id=form.section_id.data))

    return render_template("create_new_audo_check.html",
                           page_title="Cadet: Create New Quesion (Short Answer)",
                           form=form)


@instructor.route('/new-question/multiple-choice', methods=['POST'])
@login_required
def create_multiple_choice():
    form = NewMultipleChoiceQuestionForm(request.form)

    if form.validate_on_submit():
        section = Section.query.filter_by(id=form.section_id.data).first()
        if not section:
            abort(400)

        new_q = MultipleChoiceQuestion(prompt=form.prompt.data)
        db.session.add(new_q)

        for option in form.options:
            ao = AnswerOption(text=option.text.data,
                              correct=option.correct.data)
            new_q.options.append(ao)

        section.questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_id=form.section_id.data))

    return render_template("create_new_multiple_choice.html",
                           page_title="Cadet: Create New Quesion (Multiple Choice)",
                           form=form)


@instructor.route('/new-question/jumble', methods=['POST'])
@login_required
def create_code_jumble():
    form = NewJumbleQuestionForm(request.form)

    if form.validate_on_submit():
        section = Section.query.filter_by(id=form.section_id.data).first()
        if not section:
            abort(400)

        new_q = CodeJumbleQuestion(prompt=form.prompt.data,
                                   language=form.language.data)
        db.session.add(new_q)

        for block in form.code_blocks:
            jb = JumbleBlock(code=block.code.data,
                             correct_index=block.correct_index.data,
                             correct_indent=block.correct_indent.data)
            new_q.blocks.append(jb)

        section.questions.append(new_q)

        # TODO: show preview of question before commiting
        db.session.commit()

        flash("New question added!", "success")
        return redirect(url_for(".create_new_question",
                                course_id=form.section_id.data))

    return render_template("create_new_code_jumble.html",
                           page_title="Cadet: Create New Quesion (Code Jumble)",
                           form=form)


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
    section_id = HiddenField("Section ID")
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
    section_id = HiddenField("Section ID")
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    answer = TextAreaField("Question Answer", [DataRequired()])
    submit = SubmitField("Continue...")


class NewAutoCheckQuestionForm(FlaskForm):
    section_id = HiddenField("Section ID")
    prompt = StringField("Question Prompt", [DataRequired()])
    answer = StringField("Question Answer", [DataRequired()])
    regex = BooleanField("Regex")
    submit = SubmitField("Continue...")


class McOptionForm(FlaskForm):
    text = StringField('Text', [DataRequired()])
    correct = BooleanField("Correct")


class NewMultipleChoiceQuestionForm(FlaskForm):
    section_id = HiddenField("Section ID")
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
    section_id = HiddenField("Section ID")
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
    AnswerOption, CodeJumbleQuestion, JumbleBlock, Section,
    ShortAnswerQuestion, AutoCheckQuestion, MultipleChoiceQuestion
)
