from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import enum
from math import ceil

from app import db

from app.search import add_to_index, remove_from_index, query_index


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
    def reindex(cls):
        """ Updates all entries in this table. """
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class QuestionType(enum.Enum):
    GENERIC = "generic"
    SHORT_ANSWER = "short-answer"
    MULTIPLE_CHOICE = "multiple-choice"
    CODE_JUMBLE = "code-jumble"
    AUTO_CHECK = "auto-check"

class ResponseType(enum.Enum):
    GENERIC = 0
    TEXT = 1
    SELECTION = 2

class SourceType(enum.Enum):
    GENERIC = "generic"
    TEXTBOOK_SECTION = "textbook-section"

# association table for users enrolled in a course
enrollments = db.Table(
    'enrollments',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'),
              primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'),
              primary_key=True)
)

assigned_questions = db.Table(
    'assigned_questions',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'),
              primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('question.id'),
              primary_key=True)
)

# association table for objectives associated with an assessment
assigned_objectives = db.Table(
    'assigned_objectives',
    db.Column('assessment_id', db.Integer, db.ForeignKey('assessment.id')),
    db.Column('objective_id', db.Integer, db.ForeignKey('objective.id'))
)

# association table for objectives associated with a source
source_objectives = db.Table(
    'source_objectives',
    db.Column('source_id', db.Integer, db.ForeignKey('source.id')),
    db.Column('objective_id', db.Integer, db.ForeignKey('objective.id'))
)


class Question(SearchableMixin, db.Model):
    __searchable__ = ['prompt']

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(QuestionType), nullable=False)

    prompt = db.Column(db.String, nullable=False)
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


class ShortAnswerQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    answer = db.Column(db.String, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.SHORT_ANSWER,
    }

    def get_answer(self):
        return self.answer


class AutoCheckQuestion(Question):
    id = db.Column(db.Integer, db.ForeignKey('question.id'), primary_key=True)

    answer = db.Column(db.String, nullable=False)
    regex = db.Column(db.Boolean, default=False, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.AUTO_CHECK,
    }

    def get_answer(self):
        return self.answer


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
        answer = options.filter_by(correct=True).one()
        return answer.text


class AnswerOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))

    text = db.Column(db.String, nullable=False)
    correct = db.Column(db.Boolean, default=False, nullable=False)

    attempts = db.relationship('SelectionAttempt',
                                    foreign_keys='SelectionAttempt.option_id',
                                    backref='response', lazy='dynamic')


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
        return "STILL TRYING"


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

    def sm2_update(self, quality):
        """ Updates this attempt's e_factor and interval based on the given
        quality. """

        self.quality = quality

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
    option_id = db.Column(db.Integer, db.ForeignKey('answer_option.id'))

    __mapper_args__ = {
        'polymorphic_identity': ResponseType.SELECTION,
    }


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

    assessments = db.relationship('Assessment',
                                    foreign_keys='Assessment.course_id',
                                    backref='course', lazy='dynamic')

    questions = db.relationship('Question',
                               secondary=assigned_questions,
                               primaryjoin=('assigned_questions.c.course_id == Course.id'),
                               secondaryjoin=('assigned_questions.c.question_id == Question.id'),
                               backref=db.backref('courses', lazy='dynamic'),
                               lazy='dynamic')

    def __repr__(self):
        return f"<Course {self.id}: {self.name} ({self.title})>"


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

    authored_objections = db.relationship('Objective',
                                          foreign_keys='Objective.author_id',
                                          backref='author', lazy='dynamic')

    authored_sources = db.relationship('Source',
                                       foreign_keys='Source.author_id',
                                       backref='author', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.id}: {self.last_name}, {self.first_name} ({self.username})>"

    # The following functions are used for login
    def get_id(self):
        return self.id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_current_courses(self):
        return self.courses.filter(Course.start_date <= date.today())\
            .filter(Course.end_date >= date.today())\
            .all()

    def get_active_courses(self):
        return self.courses.filter(Course.end_date >= date.today())


class Objective(SearchableMixin, db.Model):
    __searchable__ = ['description']

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), index=True, unique=True)

    public = db.Column(db.Boolean, default=True, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    questions = db.relationship('Question',
                                foreign_keys='Question.objective_id',
                                backref='objective', lazy='dynamic')

    def __repr__(self):
        return f"<Objective {self.id}: {self.description}>"


class Source(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(SourceType), nullable=False)

    title = db.Column(db.String(100), index=True)

    public = db.Column(db.Boolean, default=True, nullable=False)
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
        r = f"<Source {self.id}: {self.title}"
        if self.authors:
            r += f" by {self.authors}"

        r += f". Type: {self.type}>"
        return r


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



class TextbookSection(Source):
    id = db.Column(db.Integer, db.ForeignKey('source.id'), primary_key=True)

    number = db.Column(db.String(10))
    url = db.Column(db.String)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.TEXTBOOK_SECTION,
    }

    textbook_id = db.Column(db.Integer, db.ForeignKey('textbook.id'))


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), index=True, nullable=False)
    time = db.Column(db.DateTime, default=datetime.now)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))

    objectives = db.relationship('Objective',
                                 secondary=assigned_objectives,
                                 primaryjoin=('assigned_objectives.c.assessment_id == Assessment.id'),
                                 secondaryjoin=('assigned_objectives.c.objective_id == Objective.id'),
                                 backref=db.backref('assessments', lazy='dynamic'),
                                 lazy='dynamic')

    def __repr__(self):
        return f"<Assessment {self.id}: {self.description} at {str(self.time)}>"



from app.user_views import markdown_to_html
