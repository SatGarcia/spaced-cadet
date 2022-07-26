from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import enum, string, secrets
from math import ceil
from marshmallow import (
    Schema, fields, ValidationError, validates, pre_load
)

from app import db
from app.search import add_to_index, remove_from_index, query_index, clear_index

def markdown_field(attr_name):
    def markdown_or_html(obj, context):
        raw_md = getattr(obj, attr_name)

        html_context = context.get("html")
        if html_context == True:
            return markdown_to_html(raw_md)
        else:
            return raw_md

    return markdown_or_html


def deserialize_str(s):
    if type(s) != str:
        raise ValidationError("Value must be a string.")
    elif len(s) == 0:
        raise ValidationError("String must be non-zero length.")

    return s


class SearchableMixin(object):
    """ Mixin to support searching in our models. """
    @classmethod
    def search(cls, expression, page=0, per_page=10):
        """ Searches for a given expression in this Table, with support for
        pagination. """

        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0

        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))

        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        """ Create separate lists for objects that got added, updated, and
        deleted in this commit. """

        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }


    @classmethod
    def after_commit(cls, session):
        """ Update the search index based on what objects were added, updated,
        and deleted by this commit. """
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None


    @classmethod
    def reindex(cls, analyzer="english"):
        """ Updates all entries in this table, clearing out any index
        documents that aren't current in this table. """
        clear_index(cls.__tablename__, analyzer)
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class QuestionType(enum.Enum):
    GENERIC = "generic"
    SHORT_ANSWER = "short-answer"
    MULTIPLE_CHOICE = "multiple-choice"
    MULTIPLE_SELECTION = "multiple-selection"
    CODE_JUMBLE = "code-jumble"
    AUTO_CHECK = "auto-check"

class ResponseType(enum.Enum):
    GENERIC = 0
    TEXT = 1
    SELECTION = 2

class SourceType(enum.Enum):
    GENERIC = "generic"
    TEXTBOOK_SECTION = "textbook-section"
    CLASS_MEETING = "class-meeting"

# association table for users enrolled in a course
enrollments = db.Table(
    'enrollments',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'),
              primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'),
              primary_key=True)
)

# association table for topics in a course
course_topics = db.Table(
    'course_topics',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'),
              primary_key=True),
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'),
              primary_key=True)
)

# association table for topics associated with an assessment
assessment_topics = db.Table(
    'assessment_topics',
    db.Column('assessment_id', db.Integer, db.ForeignKey('assessment.id')),
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'))
)

# association table for objectives associated with an assessment
assessment_objectives = db.Table(
    'assessment_objectives',
    db.Column('assessment_id', db.Integer, db.ForeignKey('assessment.id')),
    db.Column('objective_id', db.Integer, db.ForeignKey('objective.id'))
)

# association table for questions associated with an assessment
assessment_questions = db.Table(
    'assessment_questions',
    db.Column('assessment_id', db.Integer, db.ForeignKey('assessment.id')),
    db.Column('question_id', db.Integer, db.ForeignKey('question.id'))
)

# association table for textbooks in a course
assigned_textbooks = db.Table(
    'assigned_textbooks',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'),
              primary_key=True),
    db.Column('textbook_id', db.Integer, db.ForeignKey('textbook.id'),
              primary_key=True)
)

# association table for objectives associated with a source
source_objectives = db.Table(
    'source_objectives',
    db.Column('source_id', db.Integer, db.ForeignKey('source.id')),
    db.Column('objective_id', db.Integer, db.ForeignKey('objective.id'))
)

# association table for sources associated with a topic
topic_sources = db.Table(
    'topic_sources',
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id')),
    db.Column('source_id', db.Integer, db.ForeignKey('source.id'))
)

# association table for answer options associated with an attempt
selected_answers = db.Table(
    'selected_answers',
    db.Column('attempt_id', db.Integer, db.ForeignKey('selection_attempt.id')),
    db.Column('option_id', db.Integer, db.ForeignKey('answer_option.id'))
)

class Topic(SearchableMixin, db.Model):
    __searchable__ = ['text']

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, unique=True, nullable=False)

    objectives = db.relationship('Objective',
                                 foreign_keys='Objective.topic_id',
                                 backref='topic', lazy='dynamic')

    sources = db.relationship('Source',
                                 secondary=topic_sources,
                                 primaryjoin=('topic_sources.c.topic_id == Topic.id'),
                                 secondaryjoin=('topic_sources.c.source_id == Source.id'),
                                 backref=db.backref('topics', lazy='dynamic', order_by='Topic.text'),
                                 lazy='dynamic')


class TopicSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)

    sources = fields.List(fields.Nested("SourceSchema",
                                          only=('id', 'title')),
                            dump_only=True)

    objectives = fields.List(fields.Nested("LearningObjectiveSchema",
                                           only=('id', 'description')),
                             dump_only=True)

    @validates("text")
    def unique_text(self, text):
        if Topic.query.filter_by(text=text).count() > 0:
            raise ValidationError("text must be unique")


class Question(SearchableMixin, db.Model):
    __searchable__ = ['prompt']

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(QuestionType), nullable=False)

    prompt = db.Column(db.String, nullable=False)
    explanation = db.Column(db.String)
    public = db.Column(db.Boolean, default=True, nullable=False)
    enabled = db.Column(db.Boolean, default=False, nullable=False)

    objective_id = db.Column(db.Integer, db.ForeignKey('objective.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    attempts = db.relationship('Attempt', backref='question', lazy='dynamic')

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.GENERIC,
        'polymorphic_on': type
    }

    def __repr__(self):
        return f"<Question {self.id}: ({self.type}) {self.prompt}>"


    def create(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        # FIXME: Do we need to manually delete options in MC questions?
        db.session.commit()

    def correct_attempts(self):
        return self.attempts.filter_by(correct=True).all()

    def incorrect_attempts(self):
        return self.attempts.filter_by(correct=False).all()

    def get_answer(self):
        raise NotImplementedError("Generic questions have no answer.")

    def get_latest_attempt(self, user):
        """ Returns the most recent attempt on a question by a particular user,
            if there is no attempt, method returns None """

        all_attempts = (self.attempts.filter(db.and_(Attempt.user_id == user.id))\
                                        .order_by(Attempt.time.desc()))
       
        return all_attempts.first()


class QuestionSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    type = fields.Method("get_type", required=True, deserialize="create_type")
    prompt = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD
    author = fields.Nested("UserSchema",
                           only=("first_name", "last_name", "email"),
                           dump_only=True)
    objective = fields.Nested("LearningObjectiveSchema",
                              only=('id', 'description'),
                              dump_only=True)
    public = fields.Boolean()
    enabled = fields.Boolean()

    def get_type(self, obj):
        return obj.type.value

    def create_type(self, value):
        try:
            return QuestionType(value)
        except ValueError as error:
            raise ValidationError("Invalid question type.") from error

    def update_obj(self, question, data):
        # check that they didn't try to change the type of the question
        if 'type' in data and data['type'] != question.type:
            raise ImmutableFieldError('type')

        for field in ['type', 'prompt', 'author', 'public', 'enabled']:
            if field in data:
                setattr(question, field, data[field])


class ShortAnswerQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    answer = db.Column(db.String, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.SHORT_ANSWER,
    }

    def get_answer(self):
        return markdown_to_html(self.answer)


class ShortAnswerQuestionSchema(QuestionSchema):
    answer = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD

    def make_obj(self, data):
        return ShortAnswerQuestion(**data)

    def update_obj(self, question, data):
        super().update_obj(question, data)

        for field in ['answer']:
            if field in data:
                setattr(question, field, data[field])


class AutoCheckQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    answer = db.Column(db.String, nullable=False)
    regex = db.Column(db.Boolean, default=False, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.AUTO_CHECK,
    }

    def get_answer(self):
        if self.regex:
            return f"<code>{self.answer}</code>"
        else:
            return markdown_to_html(self.answer)


class AutoCheckQuestionSchema(QuestionSchema):
    answer = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD
    regex = fields.Boolean(required=True)

    def make_obj(self, data):
        return AutoCheckQuestion(**data)

    def update_obj(self, question, data):
        super().update_obj(question, data)

        for field in ['answer', 'regex']:
            if field in data:
                setattr(question, field, data[field])


class MultipleChoiceQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    options = db.relationship('AnswerOption',
                              foreign_keys='AnswerOption.question_id',
                              backref='question', lazy='dynamic',
                              cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.MULTIPLE_CHOICE,
    }

    def get_answer(self):
        answer = self.options.filter_by(correct=True).one()
        return markdown_to_html(answer.text)


class MultipleChoiceQuestionSchema(QuestionSchema):
    options = fields.List(fields.Nested('AnswerOptionSchema'), required=True)

    def make_obj(self, data):
        answer_options = []

        for opt in data['options']:
            ao = AnswerOption(**opt)
            answer_options.append(ao)
            db.session.add(ao)

        del data['options']

        q = MultipleChoiceQuestion(**data)
        q.options = answer_options

        return q

    def update_obj(self, question, data):
        super().update_obj(question, data)

        if 'options' in data:
            answer_options = []
            for opt in data['options']:
                ao = AnswerOption(**opt)
                answer_options.append(ao)

            question.options = answer_options

class MultipleSelectionQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    options = db.relationship('AnswerOption',
                              foreign_keys='AnswerOption.question_id',
                              backref='selection_question', lazy='dynamic',
                              cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.MULTIPLE_SELECTION,
    }

    def get_answer(self):
        answers = self.options.filter_by(correct=True).all()

        if len(answers) == 0:
            return "None of the above"
        else:
            answer = ""
            for a in answers:
                answer+=markdown_to_html(a.text)
            return answer

class MultipleSelectionQuestionSchema(QuestionSchema):
    options = fields.List(fields.Nested('AnswerOptionSchema'), required=True)

    def make_obj(self, data):
        answer_options = []

        for opt in data['options']:
            ao = AnswerOption(**opt)
            answer_options.append(ao)
            db.session.add(ao)

        del data['options']

        q = MultipleSelectionQuestion(**data)
        q.options = answer_options

        return q

    def update_obj(self, question, data):
        super().update_obj(question, data)

        if 'options' in data:
            answer_options = []
            for opt in data['options']:
                ao = AnswerOption(**opt)
                answer_options.append(ao)

            question.options = answer_options


class AnswerOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))

    text = db.Column(db.String, nullable=False)
    correct = db.Column(db.Boolean, default=False, nullable=False)


class AnswerOptionSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD
    correct = fields.Boolean(required=True)


class CodeJumbleQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    language = db.Column(db.String(20))
    blocks = db.relationship('JumbleBlock',
                                foreign_keys='JumbleBlock.question_id',
                                backref='question', lazy='dynamic')

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.CODE_JUMBLE,
    }

    def get_correct_response(self):
        """ Returns a list of (id, indent) tuples in the order they should
        appear in the correct response. """
        correct_response = []

        for block in self.blocks.filter(JumbleBlock.correct_index >= 0).order_by(
                    JumbleBlock.correct_index):
            correct_response.append((block.id, block.correct_indent))

        return correct_response


    def get_answer(self):
        answer_html = "<ul class=\"list-unstyled jumble\">"
        for block in self.blocks.filter(JumbleBlock.correct_index >= 0)\
                                .order_by(JumbleBlock.correct_index):
            block_html = block.html()
            indent_amount = (block.correct_indent * 20) + 15
            answer_html += f"<li style=\"padding-left: {indent_amount}px;\">{block_html}</li>"

        answer_html += "</ul>"

        return answer_html


class CodeJumbleQuestionSchema(QuestionSchema):
    language = fields.Str(required=True)
    blocks = fields.List(fields.Nested('JumbleBlockSchema'), required=True)

    def make_obj(self, data):
        code_blocks = []

        for block in data['blocks']:
            jb = JumbleBlock(**block)
            code_blocks.append(jb)
            db.session.add(jb)

        del data['blocks']

        q = CodeJumbleQuestion(**data)
        q.blocks = code_blocks

        return q

    def update_obj(self, question, data):
        super().update_obj(question, data)

        for field in ['language']:
            if field in data:
                setattr(question, field, data[field])

        if 'blocks' in data:
            code_blocks = []

            for block in data['blocks']:
                jb = JumbleBlock(**block)
                code_blocks.append(jb)

            question.blocks = code_blocks


class JumbleBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))

    code = db.Column(db.String, nullable=False)
    correct_index = db.Column(db.Integer, nullable=False)
    correct_indent = db.Column(db.Integer, nullable=False)

    def html(self):
        """ Get HTML to display this block's code. """
        language_str = "" if not self.question.language else self.question.language
        code_str = f"```{language_str}\n{self.code}\n```\n"
        return markdown_to_html(code_str, code_linenums=False)


class JumbleBlockSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD
    correct_index = fields.Int(required=True, data_key='correct-index')
    correct_indent = fields.Int(required=True, data_key='correct-indent')


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(ResponseType), nullable=False)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    time = db.Column(db.DateTime, default=datetime.now)
    correct = db.Column(db.Boolean)

    # entries for SM-2 Algorithm
    next_attempt = db.Column(db.Date, default=datetime.today, nullable=False)
    e_factor = db.Column(db.Float, default=2.5, nullable=False)
    interval = db.Column(db.Integer, default=1, nullable=False)
    quality = db.Column(db.Integer, default=-1, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': ResponseType.GENERIC,
        'polymorphic_on': type
    }

    def __repr__(self):
        return f"<Attempt {self.id}: Question {self.question.id} by User {self.user.id} at {self.time}>"

    def sm2_update(self, quality, repeat_attempt=False):
        """ Updates this attempt's e_factor and interval based on the given
        quality and whether this is a repeat of the same question from earlier
        today. """

        self.quality = quality

        if not repeat_attempt:
            # If this is a repeated question for today, we don't want to
            # update the interval, e_factor, or next_attempt. This attempt is
            # just to make sure they know it well before moving on.
            if quality < 3:
                # The question wasn't answered incorrectly. Keep the same e_factor as
                # before and set the interval to 1 (i.e. like learning from new)
                self.interval = 1

            else:
                self.e_factor += 0.1 - ((5-quality) * (0.08 + ((5-quality) * 0.02)))

                # set a floor for the e_factor
                if self.e_factor < 1.3:
                    self.e_factor = 1.3

                # They got the correct answer, so interval increases
                self.interval = 6 if self.interval == 1 else ceil(self.interval *
                                                                  self.e_factor)

            # next attempt will be interval days from today
            self.next_attempt = date.today() + timedelta(days=self.interval)


class TextAttempt(Attempt):
    id = db.Column(db.Integer, db.ForeignKey('attempt.id'), primary_key=True)

    response = db.Column(db.String, nullable=False)  # TODO: make no reesponse an option

    __mapper_args__ = {
        'polymorphic_identity': ResponseType.TEXT,
    }


class SelectionAttempt(Attempt):
    id = db.Column(db.Integer, db.ForeignKey('attempt.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': ResponseType.SELECTION,
    }

    responses = db.relationship('AnswerOption',
                                 secondary=selected_answers,
                                 primaryjoin=('selected_answers.c.attempt_id == SelectionAttempt.id'),
                                 secondaryjoin=('selected_answers.c.option_id == AnswerOption.id'),
                                 backref=db.backref('attempts', lazy='dynamic'),
                                 lazy='dynamic')


class Course(SearchableMixin, db.Model):
    __searchable__ = ['name', 'title']

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    title = db.Column(db.String(100), index=True, nullable=False)
    description = db.Column(db.String, index=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    users = db.relationship('User',
                               secondary=enrollments,
                               primaryjoin=('enrollments.c.course_id == Course.id'),
                               secondaryjoin=('enrollments.c.user_id == User.id'),
                               backref=db.backref('courses', lazy='dynamic'),
                               lazy='dynamic')

    textbooks = db.relationship('Textbook',
                               secondary=assigned_textbooks,
                               primaryjoin=('assigned_textbooks.c.course_id == Course.id'),
                               secondaryjoin=('assigned_textbooks.c.textbook_id == Textbook.id'),
                               backref=db.backref('courses', lazy='dynamic'),
                               lazy='dynamic')

    meetings = db.relationship('ClassMeeting',
                                foreign_keys='ClassMeeting.course_id',
                                backref='course', lazy='dynamic')

    topics = db.relationship('Topic',
                             secondary=course_topics,
                             primaryjoin=('course_topics.c.course_id == Course.id'),
                             secondaryjoin=('course_topics.c.topic_id == Topic.id'),
                             backref=db.backref('courses', lazy='dynamic'),
                             lazy='dynamic')

    assessments = db.relationship('Assessment',
                                    foreign_keys='Assessment.course_id',
                                    backref='course', lazy='dynamic',
                                    order_by='Assessment.time')

    def __repr__(self):
        return f"<Course {self.id}: {self.name} ({self.title})>"

    def upcoming_assessments(self):
        return self.assessments.filter(Assessment.time >= datetime.now())

    def past_assessments(self):
        """Returns all ClassAssessments that occured before the current time"""
        return self.assessments.filter(Assessment.time < datetime.now())

    def upcoming_meetings(self): 
        """Returns all ClassMeetings that occur today or in the future"""

        return self.meetings.filter(ClassMeeting.date >= date.today())

    def previous_meetings(self):
        """Returns all ClassMeetings that occured before today"""
        return self.meetings.filter(ClassMeeting.date < date.today() )


class CourseSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    start_date = fields.Date(required=True, data_key="start-date")
    end_date = fields.Date(required=True, data_key="end-date")

    users = fields.List(fields.Nested('UserSchema', only=('id', 'email')),
                        dump_only=True)
    meetings = fields.List(fields.Nested('ClassMeetingSchema',
                                          only=('id', 'title')),
                           dump_only=True)
    topics = fields.List(fields.Nested("TopicSchema",
                                       only=('id', 'text')),
                         dump_only=True)
    textbooks = fields.List(fields.Nested("TextbookSchema",
                                          only=("id", "title", "edition")),
                            dump_only=True)
    assessments = fields.List(fields.Nested("AssessmentSchema",
                                            only=("id", "title")),
                              dump_only=True)

    @validates("name")
    def unique_name(self, course_name):
        if Course.query.filter_by(name=course_name).count() > 0:
            raise ValidationError("name must be unique")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    first_name = db.Column(db.String(64), index=True, nullable=False)
    last_name = db.Column(db.String(64), index=True, nullable=False)

    password_hash = db.Column(db.String, nullable=False)

    admin = db.Column(db.Boolean, default=False, nullable=False)
    instructor = db.Column(db.Boolean, default=False, nullable=False)

    attempts = db.relationship('Attempt', backref='user', lazy='dynamic')

    authored_questions = db.relationship('Question',
                                         foreign_keys='Question.author_id',
                                         backref='author', lazy='dynamic')

    authored_objectives = db.relationship('Objective',
                                          foreign_keys='Objective.author_id',
                                          backref='author', lazy='dynamic')

    authored_sources = db.relationship('Source',
                                       foreign_keys='Source.author_id',
                                       backref='author', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.id}: {self.last_name}, {self.first_name} ({self.email})>"

    # The following functions are used for login
    def get_id(self):
        return self.id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def generate_password(length):
        """ Generates a random password with ASCII letters and digits of the
        requested length. """

        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def get_current_courses(self):
        """ Returns all courses whose start date is before today and end date is
        after today """

        return self.courses.filter(Course.start_date <= date.today())\
            .filter(Course.end_date >= date.today())\
            .order_by(Course.start_date)\
            .all()

    def get_active_courses(self):
        """ Returns all courses whose end date is today or later """
        
        return self.courses.filter(Course.end_date >= date.today())\
            .order_by(Course.start_date)\
            .all()
    
    def get_past_courses(self):
        """ Returns all courses whose end date is earlier than today """
        
        return self.courses.filter(Course.end_date < date.today())\
            .order_by(Course.start_date)\
            .all()

    def latest_next_attempts(self):
        """ Returns the id and latest next attempt date for all questions that
        this user has attempted. """
        return db.session.query(
            Attempt.question_id,
            Attempt.next_attempt,
            db.func.max(Attempt.next_attempt).label('latest_next_attempt_time')
        ).group_by(Attempt.question_id).filter(Attempt.user_id == self.id)


class UserSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    email = fields.Str(required=True)
    password_hash = fields.Str(load_only=True, data_key="password")
    last_name = fields.Str(required=True, data_key="last-name")
    first_name = fields.Str(required=True, data_key="first-name")
    instructor = fields.Boolean()
    admin = fields.Boolean()

    @pre_load
    def process_password(self, data, **kwargs):
        """ Checks if a plaintext password is present, using it (or a random
        new password) to generate a password hash to store in the database. """

        plain_password = data.get("password")
        if plain_password:
            data["password"] = generate_password_hash(plain_password)
        else:
            data["password"] = generate_password_hash(secrets.token_hex(25))

        return data

    @validates("email")
    def unique_email(self, email_address):
        if User.query.filter(User.email == email_address).count() > 0:
            raise ValidationError("email must be unique")



class Objective(SearchableMixin, db.Model):
    __searchable__ = ['description']

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), index=True, unique=True)

    public = db.Column(db.Boolean, default=True, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))

    questions = db.relationship('Question',
                                foreign_keys='Question.objective_id',
                                backref='objective', lazy='dynamic')

    def __repr__(self):
        return f"<Objective {self.id}: {self.description}>"

    def get_e_factor_average(self,user,assessment=None):
        """ Returns the average e_factor given an objective, assessment, and user... will return 0 if no questions in objective"""
        e_factor_sum = 0.0
        question_count = 0

        if assessment == None:
            questions = self.questions
        else:
            questions = assessment.questions.filter(Question.objective_id == self.id)

        for question in questions:
            if question.get_latest_attempt(user) != None:
                e_factor_sum += question.get_latest_attempt(user).e_factor
                question_count += 1
               
        if question_count == 0:
            return 0
        else:
            average = e_factor_sum/question_count
            return float(f"{average:.3f}")
    
    def review_questions(self, user, assessment=None, e_factor_threshold=2.5):
        """ Returns a list of all of the questions in an objective that have an e_factor of below 2.5 """
        review_list = []

        if assessment == None:
            questions = self.questions.filter(Question.objective_id == self.id)
        else:
            questions = assessment.questions.filter(Question.objective_id == self.id)

        for question in questions:
            latest_attempt = question.get_latest_attempt(user)
            if (latest_attempt != None) and (latest_attempt.e_factor < e_factor_threshold) and (latest_attempt.next_attempt > date.today()):
                review_list.append(question)

        return review_list


class LearningObjectiveSchema(Schema):
    id = fields.Int(dump_only=True)
    description = fields.Function(markdown_field('description'),
                                  deserialize=deserialize_str, required=True)

    public = fields.Boolean()
    author = fields.Nested("UserSchema", only=('email',), dump_only=True)
    topic = fields.Nested(TopicSchema, only=('id', 'text'), dump_only=True)

    questions = fields.List(fields.Nested(QuestionSchema,
                                          only=('id', 'prompt')),
                            dump_only=True)

    @validates("description")
    def unique_description(self, description):
        # TODO: limit this check to objectives that are public or that are
        # created by the author
        if Objective.query.filter(Objective.description == description).count() > 0:
            raise ValidationError("description must be unique")


    def update_obj(self, objective, data):
        for field in ['description', 'public']:
            if field in data:
                setattr(objective, field, data[field])


class Source(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(SourceType), nullable=False)

    title = db.Column(db.String(100), index=True, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    objectives = db.relationship('Objective',
                                 secondary=source_objectives,
                                 primaryjoin=('source_objectives.c.source_id == Source.id'),
                                 secondaryjoin=('source_objectives.c.objective_id == Objective.id'),
                                 backref=db.backref('sources', lazy='dynamic'),
                                 lazy='dynamic')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.GENERIC,
        'polymorphic_on': type
    }

    def __repr__(self):
        return f"<Source {self.id}: {self.title}. Type: {self.type}>"


class SourceSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    type = fields.Method("get_type", required=True, deserialize="create_type")
    title = fields.Str(required=True)
    author = fields.Nested("UserSchema", only=('email',), dump_only=True)

    objectives = fields.List(fields.Nested(LearningObjectiveSchema),
                             dump_only=True)

    topics = fields.List(fields.Nested(TopicSchema,
                                       only=('id', 'text')),
                            dump_only=True)

    def get_type(self, obj):
        return obj.type.value

    def create_type(self, value):
        try:
            return SourceType(value)
        except ValueError as error:
            raise ValidationError("Invalid source type.") from error


class Textbook(SearchableMixin, db.Model):
    __searchable__ = ['title', 'authors']

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(100), index=True, nullable=False)
    edition = db.Column(db.Integer)

    # TODO: make authors a relationship to Person table
    authors = db.Column(db.String(100), index=True, nullable=False)

    publisher = db.Column(db.String(100), index=True)
    year = db.Column(db.Integer)
    isbn = db.Column(db.String, index=True)
    url = db.Column(db.String, index=True)

    sections = db.relationship('TextbookSection',
                                foreign_keys='TextbookSection.textbook_id',
                                backref='textbook', lazy='dynamic')

    def __repr__(self):
        return f"<Textbook {self.id}: '{self.title}' by {self.authors}>"


class TextbookSchema(Schema):
    id = fields.Int(dump_only=True)

    title = fields.Str(required=True)
    edition = fields.Int()

    authors = fields.Str(required=True)
    publisher = fields.Str()

    year = fields.Int()
    isbn = fields.Str()
    url = fields.Str()

    sections = fields.List(fields.Nested("TextbookSectionSchema",
                                         only=('id', 'number', 'title', 'topics')),
                           dump_only=True)


class TextbookSection(Source):
    id = db.Column(db.Integer, db.ForeignKey('source.id'), primary_key=True)

    number = db.Column(db.String(10))
    url = db.Column(db.String)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.TEXTBOOK_SECTION,
    }

    textbook_id = db.Column(db.Integer, db.ForeignKey('textbook.id'))


class TextbookSectionSchema(SourceSchema):
    number = fields.Str()
    url = fields.Str()
    textbook = fields.Nested("TextbookSchema",
                             only=("id", "title", "edition"))

    @pre_load
    def set_type(self, data, **kwargs):
        """ Sets source type to that of textbook-section so user doesn't have
        to specify it themselves. """

        data['type'] = "textbook-section"
        return data


class ClassMeeting(Source):
    id = db.Column(db.Integer, db.ForeignKey('source.id'), primary_key=True)

    date = db.Column(db.Date, default=datetime.today, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CLASS_MEETING,
    }

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))


class ClassMeetingSchema(SourceSchema):
    date = fields.Date()
    course = fields.Nested("CourseSchema",
                             only=("id", "name", "title"))

    @pre_load
    def set_type(self, data, **kwargs):
        """ Sets source type to that of class-meeting so user doesn't have
        to specify it themselves. """

        data['type'] = "class-meeting"
        return data


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), index=True, nullable=False)
    description = db.Column(db.String, index=True)
    time = db.Column(db.DateTime, default=datetime.now)

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))

    topics = db.relationship('Topic',
                             secondary=assessment_topics,
                             primaryjoin=('assessment_topics.c.assessment_id == Assessment.id'),
                             secondaryjoin=('assessment_topics.c.topic_id == Topic.id'),
                             backref=db.backref('assessments', lazy='dynamic'),
                             lazy='dynamic')

    objectives = db.relationship('Objective',
                                 secondary=assessment_objectives,
                                 primaryjoin=('assessment_objectives.c.assessment_id == Assessment.id'),
                                 secondaryjoin=('assessment_objectives.c.objective_id == Objective.id'),
                                 backref=db.backref('assessments', lazy='dynamic'),
                                 lazy='dynamic')

    questions = db.relationship('Question',
                                secondary=assessment_questions,
                                primaryjoin=('assessment_questions.c.assessment_id == Assessment.id'),
                                secondaryjoin=('assessment_questions.c.question_id == Question.id'),
                                backref=db.backref('assessments', lazy='dynamic'),
                                lazy='dynamic')

    def __repr__(self):
        return f"<Assessment {self.id}: {self.description} at {str(self.time)}>"


    def unattempted_questions(self, user):
        """ Returns all questions that don't have an attempt by the given user. """
        return self.questions.filter(~ Question.attempts.any(Attempt.user_id == user.id))

    def due_questions(self, user):
        """ Returns all assessment questions whose latest next_attempt for the
        given user is today."""

        latest_next_attempts = user.latest_next_attempts().subquery()

        return self.questions.join(
            latest_next_attempts, db.and_(Question.id == latest_next_attempts.c.question_id,
                                          latest_next_attempts.c.latest_next_attempt_time == date.today()))

    def overdue_questions(self, user):
        """ Returns all assessment questions whose latest next_attempt for the
        given user was before today."""
        latest_next_attempts = user.latest_next_attempts().subquery()

        return self.questions.join(
            latest_next_attempts, db.and_(Question.id == latest_next_attempts.c.question_id,
                                          latest_next_attempts.c.latest_next_attempt_time < date.today()))

    def waiting_questions(self, user):
        """ Returns all assessment questions whose latest next_attempt for the
        given user is after today (i.e. don't need any practice now)."""
        latest_next_attempts = user.latest_next_attempts().subquery()

        return self.questions.join(
            latest_next_attempts, db.and_(Question.id == latest_next_attempts.c.question_id,
                                          latest_next_attempts.c.latest_next_attempt_time > date.today()))

    def fresh_questions(self, user):
        """ Returns all "fresh" assessment questions, where fresh is defined as needing
        to be practiced by the user for the FIRST time today. """
        return self.unattempted_questions(user).union(self.due_questions(user)).union(self.overdue_questions(user))

    def repeat_questions(self, user):
        """ Returns all assessment questions that the user has already attempted today
        but that haven't gotten a quality score of 4 or above."""
        midnight_today = datetime.combine(date.today(), datetime.min.time())

        poor_attempts = Attempt.query.filter(db.and_(Attempt.user_id == user.id,
                                                     Attempt.time >= midnight_today))\
                                     .group_by(Attempt.question_id)\
                                     .having(db.func.max(Attempt.quality) < 4)\
                                     .subquery()

        return self.questions.join(poor_attempts)
    
    def breakdown_today(self, user):
        """ Returns a breakdown of all assessment questions whose latest attempt was 
        today and not repeated.  

        Will return these questions as a tuple of queries: ([incorrect],
                                                           [correct: easy to recall],
                                                           [correct: medium],
                                                           [correct: difficult]) 
        """

        midnight_today = datetime.combine(date.today(), datetime.min.time())

        incorrect_id = []
        correct_easy_id = []
        correct_mid_id = []
        correct_hard_id = []

        for q in self.questions:
            attempts_today = q.attempts.filter(db.and_(Attempt.user_id == user.id,

                                                Attempt.time >= midnight_today,            
                                                     Attempt.time < midnight_today +timedelta(days=1) ))\
                                            .order_by(Attempt.time)

            if (attempts_today.count() > 0) and (attempts_today.first().correct == True):

                if attempts_today.first().quality == 5:
                    correct_easy_id.append(q.id)
                elif attempts_today.first().quality == 4:
                    correct_mid_id.append(q.id)
                elif attempts_today.first().quality == 3:
                    correct_hard_id.append(q.id)
                    
            elif (attempts_today.count() > 1) and (attempts_today.first().correct == False):
                incorrect_id.append(q.id)
                         
        
        incorrect_questions = self.questions.filter(Question.id.in_(incorrect_id))
        correct_easy = self.questions.filter(Question.id.in_(correct_easy_id))
        correct_mid = self.questions.filter(Question.id.in_(correct_mid_id))
        correct_hard = self.questions.filter(Question.id.in_(correct_hard_id))

        return (incorrect_questions, correct_easy, correct_mid, correct_hard)


    def objectives_to_review(self, user, max_num_objectives=3, average_threshold=2.5):
        """ Returns the 3 learning objectives with the lowest average e_factors in the form of: 
        a list of 3 tuples that contain (learning objective, e_factor average)"""

        lo_review = [] # (lo,e_factor_average)
        for lo in self.objectives: 
            average = lo.get_e_factor_average(user, self)
            if average < average_threshold and average > 0.1:
                lo_review.append((lo,average))

        lo_review_sorted = sorted(lo_review, key=lambda i: i[-1]) # sorts elements by last item(e_factor_average) in increasing order
        
        if len(lo_review_sorted) <= max_num_objectives: 
            return lo_review_sorted
        else: 
            return lo_review_sorted[0:max_num_objectives]
                 

class AssessmentSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    description = fields.Str()
    time = fields.DateTime()

    topics = fields.List(fields.Nested("TopicSchema",
                                       only=('id', 'text')),
                            dump_only=True)

    objectives = fields.List(fields.Nested("LearningObjectiveSchema",
                                           only=('id', 'description', 'topic')),
                             dump_only=True)

    questions = fields.List(fields.Nested("QuestionSchema",
                                           only=('id', 'type', 'prompt')),
                             dump_only=True)


from app.user_views import markdown_to_html

