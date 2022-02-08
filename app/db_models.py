#from flask_login import UserMixin
from datetime import datetime

from app import db

# association table for students enrolled in a section
enrollments = db.Table(
    'enrollments',
    db.Column('section_id', db.Integer, db.ForeignKey('section.id'),
              primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'),
              primary_key=True)
)

# association table for sources associated with a section
source_materials = db.Table(
    'source_materials',
    db.Column('section_id', db.Integer, db.ForeignKey('section.id')),
    db.Column('source_id', db.Integer, db.ForeignKey('source.id'))
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

# association table for questions associated with a learning objective
associated_questions = db.Table(
    'associated_questions',
    db.Column('objective_id', db.Integer, db.ForeignKey('objective.id')),
    db.Column('question_id', db.Integer, db.ForeignKey('question.id'))
)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)

    # entries for SM-2 Algorithm
    next_attempt = db.Column(db.Date, default=datetime.today, nullable=False)
    e_factor = db.Column(db.Float, default=2.5, nullable=False)
    interval = db.Column(db.Integer, default=1, nullable=False)

    students = db.relationship('Attempt', backref='question', lazy='dynamic')

    def __repr__(self):
        return f"<Question {self.id}: {self.prompt}>"


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'),
                            primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'),
                           primary_key=True)

    #question = db.relationship('Question', backref='students', lazy='dynamic')
    #student = db.relationship('Student', backref='questions', lazy='dynamic')

    time = db.Column(db.DateTime, default=datetime.utcnow)
    response = db.Column(db.String, nullable=False)
    correct = db.Column(db.Boolean)

    def __repr__(self):
        return f"<Attempt {self.id}: Question {self.question.id} by Student {self.student.id} at {self.time}>"


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(64), index=True)
    number = db.Column(db.Integer, index=True)

    students = db.relationship('Student',
                               secondary=enrollments,
                               primaryjoin=('enrollments.c.section_id == Section.id'),
                               secondaryjoin=('enrollments.c.student_id == Student.id'),
                               backref=db.backref('sections', lazy='dynamic'),
                               lazy='dynamic')

    sources = db.relationship('Source',
                               secondary=source_materials,
                               primaryjoin=('source_materials.c.section_id == Section.id'),
                               secondaryjoin=('source_materials.c.source_id == Source.id'),
                               backref=db.backref('sections', lazy='dynamic'),
                               lazy='dynamic')

    assessments = db.relationship('Assessment',
                                    foreign_keys='Assessment.section_id',
                                    backref='assessment', lazy='dynamic')

    def __repr__(self):
        return f"<Section {self.id}: {self.course} - Section #{self.section_num}>"


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    first_name = db.Column(db.String(64), index=True, nullable=False)
    last_name = db.Column(db.String(64), index=True, nullable=False)

    questions = db.relationship('Attempt', backref='student', lazy='dynamic')

    def __repr__(self):
        return f"<Student {self.id}: {self.last_name}, {self.first_name} ({self.username})>"


class Objective(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), index=True, unique=True)

    questions = db.relationship('Question',
                                 secondary=associated_questions,
                                 primaryjoin=('associated_questions.c.objective_id == Objective.id'),
                                 secondaryjoin=('associated_questions.c.question_id == Question.id'),
                                 backref=db.backref('objectives', lazy='dynamic'),
                                 lazy='dynamic')

    def __repr__(self):
        return f"<Objective {self.id}: {self.description}>"


class Source(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), index=True, nullable=False)
    url = db.Column(db.String(100), index=True, unique=True)

    objectives = db.relationship('Objective',
                                 secondary=source_objectives,
                                 primaryjoin=('source_objectives.c.source_id == Source.id'),
                                 secondaryjoin=('source_objectives.c.objective_id == Objective.id'),
                                 backref=db.backref('sources', lazy='dynamic'),
                                 lazy='dynamic')

    def __repr__(self):
        return f"<Source {self.id}: {self.description}>"


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), index=True, nullable=False)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'))

    objectives = db.relationship('Objective',
                                 secondary=assigned_objectives,
                                 primaryjoin=('assigned_objectives.c.assessment_id == Assessment.id'),
                                 secondaryjoin=('assigned_objectives.c.objective_id == Objective.id'),
                                 backref=db.backref('assessments', lazy='dynamic'),
                                 lazy='dynamic')

    def __repr__(self):
        return f"<Assessment {self.id}: {self.description} at {str(self.time)}>"

