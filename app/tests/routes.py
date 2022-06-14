from flask import jsonify, request
from marshmallow import (
    ValidationError, Schema, fields
)
from faker import Faker
from datetime import date, datetime, timedelta

from app import db
from app.tests import tests
from app.db_models import (
    User, UserSchema, Course, CourseSchema, Assessment, Objective,
    LearningObjectiveSchema,
    ShortAnswerQuestion, ShortAnswerQuestionSchema
)

Faker.seed(0)
fake = Faker()

class LoadDataError(Exception):
    def __init__(self, message, response, status_code):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        # Now for your custom code...
        self.response = response
        self.status_code = status_code


def load_data(schema):
    json_data = request.get_json()
    if not json_data:
        raise LoadDataError("Missing data", jsonify(message="No input data provided"), 400)

    try:
        data = schema.load(json_data)
    except ValidationError as err:
        raise LoadDataError("Validation error", jsonify(err.messages), 422)

    return data


@tests.route('/reset_db')
def reset_db():
    db.drop_all()
    db.create_all()
    return jsonify(status="success")


@tests.route('/seed/user', methods=['POST'])
def seed_user():
    try:
        data = load_data(UserSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    new_user = User(**data)
    db.session.add(new_user)
    db.session.commit()

    return jsonify(UserSchema().dump(new_user))

@tests.route('/seed/course', methods=['POST'])
def seed_course():
    CourseInfoSchema = Schema.from_dict({
        'name': fields.Str(required=True),
        'instructor_email': fields.Str(required=True),
        'num_students': fields.Int(required=True),
        'num_past_assessments': fields.Int(required=True),
        'num_upcoming_assessments': fields.Int(required=True)
    })
    try:
        data = load_data(CourseInfoSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    instructor = User.query.filter_by(email=data['instructor_email']).first()
    if not instructor or not instructor.instructor:
        return jsonify(message="No instructor with that email"), 422

    new_course = Course(name=data['name'], title=fake.sentence(),
                        description=fake.paragraph(),
                        start_date=(date.today() - timedelta(days=data['num_past_assessments']+1)),
                        end_date=(date.today() + timedelta(days=data['num_upcoming_assessments']+1)))
    db.session.add(new_course)
    db.session.commit()

    new_course.users.append(instructor)

    # create the fake students
    for i in range(data['num_students']):
        student = User(email=fake.email(), first_name=fake.first_name(),
                       last_name=fake.last_name())
        student.set_password('testing')
        new_course.users.append(student)

    db.session.commit()

    # create the fake assessments
    assess_num = 1
    for i in range(data['num_past_assessments']):
        a = Assessment(title=f"Assessment {assess_num}",
                       time=(datetime.now()-timedelta(days=data['num_past_assessments']-i)))
        new_course.assessments.append(a)
        assess_num += 1

    for i in range(data['num_upcoming_assessments']):
        a = Assessment(title=f"Assessment {assess_num}",
                       time=(datetime.now()+timedelta(days=i)))
        new_course.assessments.append(a)
        assess_num += 1

    db.session.commit()

    return jsonify(CourseSchema().dump(new_course))

@tests.route('/seed/objective', methods=['POST'])
def seed_objective():
    AuthorIdSchema = Schema.from_dict({
        'author_id': fields.Int(required=True)
    })
    try:
        data = load_data(AuthorIdSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    author = User.query.filter_by(id=data['author_id']).first()
    if not author:
        return jsonify(message=f"No user with ID {data['author_id']}"), 422

    new_objective = Objective(description=fake.sentence(), author=author)
    db.session.add(new_objective)
    db.session.commit()

    return jsonify(LearningObjectiveSchema().dump(new_objective))


@tests.route('/seed/question/short-answer', methods=['POST'])
def seed_short_answer():
    """ Creates randomized short answer questions. """
    QuestionInfoSchema = Schema.from_dict({
        'author_id': fields.Int(required=True),
        'assessment_id': fields.Int(),
        'amount': fields.Int(required=True),  # the number of questions to create
    })

    try:
        data = load_data(QuestionInfoSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    author = User.query.filter_by(id=data['author_id']).first()
    if not author:
        return jsonify(message=f"No user with ID {data['author_id']}"), 422

    if 'assessment_id' in data:
        assessment = Assessment.query.filter_by(id=data['assessment_id']).first()
        if not assessment:
            return jsonify(message=f"No assessment with ID {data['assessment_id']}"), 422
    else:
        assessment = None

    new_questions = []

    for i in range(data['amount']):
        answer = fake.sentence(nb_words=3)
        prompt = f"Enter something similar to the following: {answer}"
        new_q = ShortAnswerQuestion(prompt=prompt, answer=answer, author=author,
                                    public=True, enabled=True)

        new_questions.append(new_q)
        db.session.add(new_q)

        if assessment:
            assessment.questions.append(new_q)

        db.session.commit()

    return jsonify(ShortAnswerQuestionSchema().dump(new_questions, many=True))
