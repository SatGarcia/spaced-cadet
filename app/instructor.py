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

import os, csv, re

from app import db
from app.user_views import (
    ShortAnswerForm, markdown_to_html, CodeJumbleForm, AutoCheckForm,
    MultipleChoiceForm
)
from app.auth import AuthorizationError, check_authorization

instructor = Blueprint('instructor', __name__)

@instructor.route('/courses/create', methods=["GET", "POST"])
@login_required
def create_course():
    try:
        check_authorization(current_user, instructor=True)
    except AuthorizationError:
        abort(401)

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


@instructor.route('/q/<int:question_id>/review')
@login_required
def review_new_question(question_id):
    question = Question.query.filter_by(id=question_id).first()

    if not question:
        abort(404)
    elif (question.author != current_user) and (not current_user.admin):
        # Only allow a question's creator (and admins) to review a question
        abort(401)

    return render_template("review_question.html",
                           page_title="Cadet: Review Question",
                           question=question)



@instructor.route('/q/<int:question_id>/preview')
@login_required
def preview_question(question_id):
    question = Question.query.filter_by(id=question_id).first()

    if not question:
        abort(404)
    elif (not question.public)\
        and (question.author != current_user)\
        and (not current_user.admin):
        # Only allow user to preview public questions or ones they have
        # created. Admins can view all questions though.
        abort(401)

    page_title = "Cadet: Question Preview"
    prompt_html = markdown_to_html(question.prompt)

    # TODO: reduce code duplication in calling render_template with nearly the
    # same arguments for all cases in this chained condition
    if question.type == QuestionType.SHORT_ANSWER:
        form = ShortAnswerForm(question_id=question.id)
        return render_template("test_short_answer.html",
                               page_title=page_title,
                               preview_mode=True,
                               form=form,
                               prompt=Markup(prompt_html))

    elif question.type == QuestionType.AUTO_CHECK:
        form = AutoCheckForm(question_id=question.id)
        return render_template("test_short_answer.html",
                               page_title=page_title,
                               preview_mode=True,
                               form=form,
                               prompt=Markup(prompt_html))


    elif question.type == QuestionType.CODE_JUMBLE:
        form = CodeJumbleForm(question_id=question.id, response="")
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

                    student_to_add.set_password(User.generate_password(20))
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

    try:
        check_authorization(current_user, course=course, instructor=True)
    except AuthorizationError:
        abort(401)

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

    try:
        check_authorization(current_user, course=course, instructor=True)
    except AuthorizationError:
        abort(401)

    # query all (public questions + authored questions) - course questions
    all_questions = Question.query.filter_by(public=True).union(current_user.authored_questions).except_(course.questions).all()

    return render_template("browse_questions.html",
                           page_title="Cadet: Available Questions",
                           course=course,
                           questions=all_questions)


@instructor.route('/q/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    question = Question.query.filter_by(id=question_id).first()

    if not question:
        abort(404)
    elif not (current_user.admin or question.author == current_user):
        # only admins and the question's author can edit this question
        abort(401)

    form_data = request.form if request.method == 'POST' else None

    if question.type == QuestionType.SHORT_ANSWER:
        form = NewShortAnswerQuestionForm(formdata=form_data, obj=question)
        template = "create_new_short_answer.html"
    elif question.type == QuestionType.AUTO_CHECK:
        form = NewAutoCheckQuestionForm(formdata=form_data, obj=question)
        template = "create_new_auto_check.html"
    elif question.type == QuestionType.MULTIPLE_CHOICE:
        form = NewMultipleChoiceQuestionForm(formdata=form_data, obj=question)
        template = "create_new_multiple_choice.html"
    elif question.type == QuestionType.CODE_JUMBLE:
        form = NewJumbleQuestionForm(formdata=form_data, obj=question)
        template = "create_new_code_jumble.html"
    else:
        abort(400)

    if form.validate_on_submit():
        form.populate_obj(question)

        db.session.commit()

        # TODO: change this to redirect to user's "my question's" page (once
        # that is created)
        return redirect(url_for("user_views.root"))


    return render_template(template,
                           page_title="Cadet: Edit Quesion",
                           edit_mode=True,
                           form=form)


@instructor.route('/new-question/<question_type>', methods=['GET', 'POST'])
@login_required
def create_new_question(question_type):
    try:
        check_authorization(current_user, instructor=True)
    except AuthorizationError:
        abort(401)

    if question_type == 'short-answer':
        form = NewShortAnswerQuestionForm(request.form)
        template = "create_new_short_answer.html"
        new_q = ShortAnswerQuestion()
    elif question_type == 'auto-check':
        form = NewAutoCheckQuestionForm(request.form)
        template = "create_new_auto_check.html"
        new_q = AutoCheckQuestion()
    elif question_type == 'multiple-choice':
        form = NewMultipleChoiceQuestionForm(request.form)
        template = "create_new_multiple_choice.html"
        new_q = MultipleChoiceQuestion()
    elif question_type == 'code-jumble':
        form = NewJumbleQuestionForm(request.form)
        template = "create_new_code_jumble.html"
        new_q = CodeJumbleQuestion()
    else:
        abort(400)

    if form.validate_on_submit():
        form.populate_obj(new_q)

        current_user.authored_questions.append(new_q)
        db.session.commit()

        return redirect(url_for(".review_new_question", question_id=new_q.id))


    return render_template(template,
                           page_title="Cadet: Create New Quesion",
                           form=form)


@instructor.route('/c/<course_name>/roster')
@login_required
def manage_roster(course_name):
    course = Course.query.filter_by(name=course_name).first()
    if not course:
        abort(404)

    try:
        check_authorization(current_user, course=course, instructor=True)
    except AuthorizationError:
        abort(401)

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

    try:
        check_authorization(current_user, course=course, instructor=True)
    except AuthorizationError:
        abort(401)

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


class NewShortAnswerQuestionForm(FlaskForm):
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    answer = TextAreaField("Question Answer", [DataRequired()])
    submit = SubmitField("Continue...")


class NewAutoCheckQuestionForm(FlaskForm):
    prompt = TextAreaField("Question Prompt", [DataRequired()])
    answer = StringField("Question Answer", [DataRequired()])
    regex = BooleanField("Regex")
    submit = SubmitField("Continue...")


class McOptionForm(FlaskForm):
    text = StringField('Text', [DataRequired()])
    correct = BooleanField("Correct")


class NewMultipleChoiceQuestionForm(FlaskForm):
    from app.db_models import AnswerOption

    prompt = TextAreaField("Question Prompt", [DataRequired()])
    options = FieldList(FormField(McOptionForm, default=AnswerOption), min_entries=2)
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
    from app.db_models import JumbleBlock

    prompt = TextAreaField("Question Prompt", [DataRequired()])
    language = SelectField("Language",
                           validators=[InputRequired()],
                           choices=[('python', "Python")])
    blocks = FieldList(FormField(JumbleBlockForm, default=JumbleBlock), min_entries=2)
    submit = SubmitField("Submit")

    def validate_blocks(self, field):
        """ Checks that correct indices go from 0 up to N-1 """
        blocks_in_answer = [block.correct_index.data
                            for block in field
                                if block.correct_index.data >= 0]

        blocks_in_answer.sort()
        for i in range(len(blocks_in_answer)):
            if i not in blocks_in_answer:
                raise ValidationError(f"Missing a Code Block with Correct Location {i}")


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
