from flask import (
    Blueprint, render_template, url_for, redirect, flash, request, abort,
    Markup, current_app
)

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, TextAreaField, HiddenField, SelectField,
    FieldList, FormField, IntegerField, BooleanField
)
from wtforms.fields import DateField
from wtforms.widgets import DateInput
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import (
    DataRequired, InputRequired, NumberRange, ValidationError, Length, Regexp
)

from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

import os, csv, secrets, string, re

from app import db
from app.user_views import (
    ShortAnswerForm, markdown_to_html, CodeJumbleForm, AutoCheckForm,
    MultipleChoiceForm
)

instructor = Blueprint('instructor', __name__)

@instructor.route('/courses/create', methods=["GET", "POST"])
@login_required
def create_course():
    form = NewCourseForm()

    if form.validate_on_submit():
        course = Course(name=form.name.data,
                        title=form.title.data,
                        description=form.description.data,
                        start_date=form.start_date.data,
                        end_date=form.end_date.data)

        course.users.append(current_user)
        db.session.commit()

        flash(f"Successfully created course {course.name}", "success")
        return redirect(url_for("user_views.root"))

    return render_template("create_course.html",
                           page_title="Cadet: Create Course",
                           form=form)


@instructor.route('/new-question/confirm', methods=["POST"])
@login_required
def confirm_new_question():
    form = ConfirmNewQuestionForm(request.form)

    question = Question.query.filter_by(id=form.question_id.data).first()
    if not question:
        abort(400) # TODO: more appropriate error code

    if form.validate_on_submit():
        course = Course.query.filter_by(id=form.course_id.data).first()
        if not course:
            abort(400) # TODO: more appropriate error code

        if form.yes.data:
            # user confirmed question, so enable it and add it to the course
            question.enabled = True
            question.public = form.public.data
            course.questions.append(question)
            db.session.commit()

            # TODO: include link to view the preview in this link
            flash("New question added!", "success")

        else:
            db.session.delete(question)
            db.session.commit()

            flash("New question NOT added!", "warning")

        return redirect(url_for(".create_new_question",
                                course_name=course.name))

    return render_template("confirm_question.html",
                           page_title="Confirm New Question",
                           question=question,
                           form=form)


def get_confirmation_page(course, question):
    # FIXME: public isn't showing up as checked by default
    form = ConfirmNewQuestionForm(question_id=question.id,
                                  course_id=course.id,
                                  public=True)

    return render_template("confirm_question.html",
                           page_title="Confirm New Question",
                           question=question,
                           form=form)


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


def add_students_from_roster(course, file_location, email_index,
                             last_name_index, first_name_index, add_drop=False):
    """
    Adds students in a given roster file (CSV format) to the specified course.

    This will add new Users to the database if the student hasn't been created
    before.
    """
    try:
        with open(file_location, newline='', encoding='utf-8-sig') as roster_data:
            roster_reader = csv.reader(roster_data)
            header = next(roster_reader)

            num_fields = len(header)
            if email_index >= num_fields \
                or last_name_index >= num_fields \
                or first_name_index >= num_fields:

                # Couldn't find at least one of the required columns
                flash("Could not locate one or more of: email, last name, first name",
                        "danger")
                return

            new_students = []  # students who are not currently enrolled
            duplicate_students = []  # students already enrolled
            students_in_file = []  # all students listed in given file

            initial_roster = course.users.filter_by(instructor=False).all()

            if not initial_roster:
                initial_roster = []

            for line in roster_reader:
                email = line[email_index]
                last_name = line[last_name_index]
                first_name = line[first_name_index]

                # look for an existing user with that email
                student_to_add = User.query.filter_by(email=email).first()

                if student_to_add:
                    # found the student already so no need to create a
                    # new User object
                    current_app.logger.debug(f"User with {email} already exists. Skipping creation!")
                else:
                    # Create new User and add to database
                    student_to_add = User(email=email,
                                          first_name=first_name,
                                          last_name=last_name,
                                          instructor=False,
                                          admin=False)

                    # generate a random 20-character password for the user
                    alphabet = string.ascii_letters + string.digits
                    password = ''.join(secrets.choice(alphabet) for _ in range(20))

                    student_to_add.set_password(password)
                    db.session.add(student_to_add)
                    db.session.commit()

                    current_app.logger.info(f"Created student user with email {email}")

                students_in_file.append(student_to_add)

                if student_to_add in course.users:
                    # student is already enrolled in this course so
                    # nothing more to do
                    duplicate_students.append(student_to_add.email)
                else:
                    # Add user to this course
                    new_students.append(student_to_add.email)
                    course.users.append(student_to_add)
                    db.session.commit()

                current_app.logger.debug(f"Skipped (Already enrolled): {duplicate_students}")
                current_app.logger.info(f"Enrolled: {new_students}")

                db.session.commit()

            if add_drop:
                # Find and remove students who were in the roster before but
                # weren't part of the roster file.
                students_to_remove = [s for s in initial_roster
                                            if s not in students_in_file]

                for student in students_to_remove:
                    # remove student from course
                    course.users.remove(student)
                    current_app.logger.info(f"Removed {student.email} from course {course.id}")

                db.session.commit()

                if len(students_to_remove) > 0:
                    flash(f"Removed {len(students_to_remove)} students from course.", "warning")

            if len(new_students) > 0:
                flash(f"Added {len(new_students)} new students to course.", "info")
            if len(duplicate_students) > 0:
                flash(f"Skipped {len(duplicate_students)} who were already enrolled.", "warning")

    except UnicodeError as e:
        current_app.logger.warning(f"Roster file has incorrect encoding.")
        flash(f"Roster file has incorrect encoding.", "danger")



@instructor.route('/c/<course_name>/upload-roster', methods=['POST'])
@login_required
def upload_roster(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)

    #roster_upload_form = RosterUploadForm(request.form)
    roster_upload_form = RosterUploadForm()

    if roster_upload_form.validate_on_submit():
        uploaded_file = roster_upload_form.roster_file.data

        # save uploaded file to temporary file
        filename = secure_filename(uploaded_file.filename)

        temp_dir = file_location = os.path.join(current_app.instance_path, 'tmp')
        os.makedirs(temp_dir, exist_ok=True)

        file_location = os.path.join(temp_dir, filename)
        uploaded_file.save(file_location)

        add_students_from_roster(course, file_location,
                                 roster_upload_form.email_index.data,
                                 roster_upload_form.last_name_index.data,
                                 roster_upload_form.first_name_index.data,
                                 add_drop=roster_upload_form.add_drop.data)

        os.remove(file_location)
        return redirect(url_for(f'.manage_roster', course_name=course_name))

    print(roster_upload_form.errors)

    return render_template("manage_roster.html",
                           page_title="Cadet: Manage Course Roster",
                           course=course,
                           students=course.users.all(),
                           roster_form=roster_upload_form)



@instructor.route('/c/<course_name>/add-question')
@login_required
def add_question(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)

    # query all (public questions + authored questions) - course questions
    all_questions = Question.query.filter_by(public=True).union(current_user.authored_questions).except_(course.questions).all()

    return render_template("browse_questions.html",
                           page_title="Cadet: Available Questions",
                           course=course,
                           questions=all_questions)

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

        current_user.authored_questions.append(new_q)

        db.session.commit()

        return get_confirmation_page(course, new_q)


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

        current_user.authored_questions.append(new_q)
        db.session.commit()

        return get_confirmation_page(course, new_q)

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

        current_user.authored_questions.append(new_q)
        db.session.commit()

        return get_confirmation_page(course, new_q)


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

        current_user.authored_questions.append(new_q)
        db.session.commit()

        return get_confirmation_page(course, new_q)


    return render_template("create_new_code_jumble.html",
                           page_title="Cadet: Create New Quesion (Code Jumble)",
                           form=form)


@instructor.route('/c/<course_name>/roster')
@login_required
def manage_roster(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)

    form = RosterUploadForm()

    return render_template("manage_roster.html",
                           page_title="Cadet: Manage Course Roster",
                           course=course,
                           students=course.users.all(),
                           roster_form=form)


@instructor.route('/c/<course_name>/questions')
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


class NewCourseForm(FlaskForm):
    name = StringField("Name", [DataRequired(), Length(min=5, max=64),
                                Regexp("^[a-z].*[a-z0-9]$",
                                       flags=re.IGNORECASE,
                                       message="Name must start with a letter and end with a letter or number"),
                                Regexp("^[\w-]+$",
                                       flags=re.IGNORECASE,
                                       message="Name may only contain letters, numbers, underscores (_) and hyphens (-)"),
                                Regexp("^([^-_][-_]?)+$",
                                       flags=re.IGNORECASE,
                                       message="Name may not have consecutive hyphens (-) or underscores (_)")])

    title = StringField("Title", [DataRequired(), Length(min=5, max=100)])
    description = TextAreaField("Description", [DataRequired()])
    start_date = DateField('Start Date', widget=DateInput(), validators=[DataRequired()])
    end_date = DateField('End Date', widget=DateInput(), validators=[DataRequired()])
    submit = SubmitField("Create Course")

    def validate_name(form, field):
        if Course.query.filter_by(name=field.data).count() != 0:
            raise ValidationError("A course with that name already exists")


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


class ConfirmNewQuestionForm(FlaskForm):
    course_id = HiddenField("Course ID")
    question_id = HiddenField("Question ID")
    public = BooleanField("Make Question Public")
    yes = SubmitField("Yes")
    no = SubmitField("No")


class RosterUploadForm(FlaskForm):
    roster_file = FileField('Class Roster',
                            validators=[FileRequired(),
                                        FileAllowed(['csv'], 'Roster file must be CSV format')])
    email_index = SelectField("Email", validators=[InputRequired()],
                              validate_choice=False, choices=[(-1, "")],
                              coerce=int)
    last_name_index = SelectField("Last Name", validators=[InputRequired()],
                                  validate_choice=False, choices=[(-1, "")],
                                  coerce=int)
    first_name_index = SelectField("First Name", validators=[InputRequired()],
                                   validate_choice=False, choices=[(-1, "")],
                                   coerce=int)
    add_drop = BooleanField('Enable Add/Drop')
    submit = SubmitField('Upload Roster')


from app.db_models import (
    AnswerOption, CodeJumbleQuestion, JumbleBlock, Course,
    ShortAnswerQuestion, AutoCheckQuestion, MultipleChoiceQuestion, Question,
    QuestionType, User
)
