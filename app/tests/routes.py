from flask import jsonify, request
from marshmallow import (
    ValidationError, Schema, fields
)
from faker import Faker
from datetime import date, datetime, timedelta

from app import db
from app.tests import tests
from app.db_models import (
    User, UserSchema, Course, CourseSchema, Assessment
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
        student.set_password(fake.password())
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
