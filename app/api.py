from flask import request, jsonify
from flask_restful import Resource, Api
from marshmallow import (
    Schema, fields, ValidationError, validates, pre_load, EXCLUDE
)
from flask_jwt_extended import (
    jwt_required, create_access_token, set_access_cookies, unset_jwt_cookies
)
from marshmallow.decorators import post_load
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime
from enum import Enum
import secrets

from app import db

class AuthenticationSchema(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True)

class QuestionSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    type = fields.Method("get_type", required=True, deserialize="create_type")
    prompt = fields.Str(required=True)
    author = fields.Nested("UserSchema",
                           only=("first_name", "last_name", "email"),
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


class ShortAnswerQuestionSchema(QuestionSchema):
    answer = fields.Str(required=True)

    @post_load
    def make_sa_question(self, data, **kwargs):
        return ShortAnswerQuestion(**data)


class AnswerOptionSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)
    correct = fields.Boolean(required=True)


class MultipleChoiceQuestionSchema(QuestionSchema):
    options = fields.List(fields.Nested(AnswerOptionSchema), required=True)

    @post_load
    def make_mc_question(self, data, **kwargs):
        answer_options = []
        for opt in data['options']:
            ao = AnswerOption(**opt)
            answer_options.append(ao)
            db.session.add(ao)

        del data['options']
        q = MultipleChoiceQuestion(**data)
        q.options = answer_options

        return q


class JumbleBlockSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(required=True)
    correct_index = fields.Int(required=True, data_key='correct-index')
    correct_indent = fields.Int(required=True, data_key='correct-indent')


class CodeJumbleQuestionSchema(QuestionSchema):
    language = fields.Str(required=True)
    blocks = fields.List(fields.Nested(JumbleBlockSchema))

    @post_load
    def make_cj_question(self, data, **kwargs):
        code_blocks = []
        for block in data['blocks']:
            jb = JumbleBlock(**block)
            code_blocks.append(jb)
            db.session.add(jb)

        del data['blocks']
        q = CodeJumbleQuestion(**data)
        q.blocks = code_blocks

        return q


class LearningObjectiveSchema(Schema):
    id = fields.Int(dump_only=True)
    description = fields.Str(required=True)

    public = fields.Boolean()
    author = fields.Nested("UserSchema", dump_only=True)

    questions = fields.List(fields.Nested(QuestionSchema), dump_only=True)


class SourceSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    type = fields.Method("get_type", required=True, deserialize="create_type")
    title = fields.Str()
    public = fields.Boolean()
    author = fields.Nested("UserSchema", dump_only=True)

    objectives = fields.List(fields.Nested(LearningObjectiveSchema),
                             dump_only=True)

    def get_type(self, obj):
        return obj.type.value

    def create_type(self, value):
        try:
            return SourceType(value)
        except ValueError as error:
            raise ValidationError("Invalid source type.") from error


class TextbookSectionSchema(SourceSchema):
    number = fields.Str()
    title = fields.Str(required=True)
    url = fields.Str()
    textbook = fields.Nested("TextbookSchema",
                             only=("id", "title"))

    @pre_load
    def set_type(self, data, **kwargs):
        """ Sets source type to that of textbook-section so user doesn't have
        to specify it themselves. """

        data['type'] = "textbook-section"
        return data


class TextbookSchema(Schema):
    id = fields.Int(dump_only=True)

    title = fields.Str(required=True)
    edition = fields.Int()

    authors = fields.Str(required=True)
    publisher = fields.Str()

    year = fields.Int()
    isbn = fields.Str()
    url = fields.Str()

    sections = fields.List(fields.Nested(TextbookSectionSchema),
                           dump_only=True)


class AssessmentSchema(Schema):
    id = fields.Int(dump_only=True)
    pass


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



class CourseSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    start_date = fields.Date(required=True, data_key="start-date")
    end_date = fields.Date(required=True, data_key="end-date")
    users = fields.List(fields.Nested(UserSchema), dump_only=True)

    @validates("name")
    def unique_name(self, course_name):
        if Course.query.filter_by(name=course_name).count() > 0:
            raise ValidationError("name must be unique")



user_schema = UserSchema()
users_schema = UserSchema(many=True)
course_schema = CourseSchema()
question_schema = QuestionSchema(unknown=EXCLUDE)
sa_question_schema = ShortAnswerQuestionSchema()
mc_question_schema = MultipleChoiceQuestionSchema()
cj_question_schema = CodeJumbleQuestionSchema()
textbook_schema = TextbookSchema()
textbook_section_schema = TextbookSectionSchema()


def init_app(flask_app):
    rf_api = Api(flask_app)
    rf_api.add_resource(LoginApi, '/api/login')
    rf_api.add_resource(LogoutApi, '/api/logout')

    rf_api.add_resource(UserApi, '/api/user/<int:user_id>')
    rf_api.add_resource(UsersApi, '/api/users')

    rf_api.add_resource(CourseApi, '/api/course/<int:course_id>')
    rf_api.add_resource(CoursesApi, '/api/courses')

    rf_api.add_resource(RosterApi,
                        '/api/course/<int:course_id>/students')
    rf_api.add_resource(EnrolledStudentApi,
                        '/api/course/<int:course_id>/student/<int:student_id>',
                        endpoint="enrolled_student")
    rf_api.add_resource(CourseQuestionsApi,
                        '/api/course/<int:course_id>/questions',
                        endpoint='course_questions')
    rf_api.add_resource(CourseQuestionApi,
                        '/api/course/<int:course_id>/question/<int:question_id>',
                        endpoint='course_question')

    rf_api.add_resource(TextbookApi, '/api/textbook/<int:textbook_id>')
    rf_api.add_resource(TextbooksApi, '/api/textbooks')

    rf_api.add_resource(QuestionApi, '/api/question/<int:question_id>')
    rf_api.add_resource(QuestionsApi, '/api/questions')

    rf_api.add_resource(TextbookSectionsApi, '/api/textbook/<int:textbook_id>/sections')


class TextbookApi(Resource):
    @jwt_required()
    def get(self, textbook_id):
        t = Textbook.query.filter_by(id=textbook_id).one_or_none()
        if t:
            return textbook_schema.dump(t)
        else:
            return {"message": f"No textbook found with id {textbook_id}"}, 404


class TextbooksApi(Resource):
    @jwt_required()
    def get(self):
        textbooks = Textbook.query.all()
        result = textbook_schema.dump(textbooks, many=True)
        return {'textbooks': result}

    @jwt_required()
    def post(self):
        return create_and_commit(Textbook, textbook_schema, request.get_json())


class TextbookSectionsApi(Resource):
    @jwt_required()
    def get(self, textbook_id):
        t = Textbook.query.filter_by(id=textbook_id).one_or_none()

        if not t:
            return {"message": f"No textbook found with id {textbook_id}"}, 404

        result = textbook_section_schema.dump(t.sections, many=True)
        return {'textbook_sections': result}

    @jwt_required()
    def post(self, textbook_id):
        t = Textbook.query.filter_by(id=textbook_id).one_or_none()

        if not t:
            return {"message": f"No textbook found with id {textbook_id}"}, 404

        return create_and_commit(TextbookSection, textbook_section_schema,
                                 request.get_json(), add_to=t.sections)


class UserApi(Resource):
    @jwt_required()
    def get(self, user_id):
        u = User.query.filter_by(id=user_id).one_or_none()
        if u:
            return user_schema.dump(u)
        else:
            return {"message": f"No user found with id {user_id}"}, 404

    @jwt_required()
    def delete(self, user_id):
        u = User.query.filter_by(id=user_id).one_or_none()
        if u:
            db.session.delete(u)
            db.session.commit()
            return {"deleted": user_schema.dump(u)}
        else:
            return {"message": f"No user found with id {user_id}"}, 404


class UsersApi(Resource):
    @jwt_required()
    def get(self):
        users = User.query.all()
        result = users_schema.dump(users)
        return {'users': result}

    @jwt_required()
    def post(self):
        return create_and_commit(User, user_schema, request.get_json())


class CourseApi(Resource):
    @jwt_required()
    def get(self, course_id):
        c = Course.query.filter_by(id=course_id).one_or_none()
        if c:
            return course_schema.dump(c)
        else:
            return {'message': f"Course {course_id} not found."}, 404


def create_and_commit(obj_type, schema, json_data, add_to=None):
    """ Uses the given JSON data and schema to create an object of the given
    type. """
    if not json_data:
        return {"message": "No input data provided"}, 400

    # validate and de-serialize (i.e. load) the data
    try:
        data = schema.load(json_data)
    except ValidationError as err:
        return err.messages, 422

    # create the object and add it to the database
    obj = obj_type(**data)
    db.session.add(obj)

    # add it to the collection specified by add_to, if that param was given
    if add_to:
        add_to.append(obj)

    db.session.commit()

    result = schema.dump(obj)
    return {obj_type.__name__.lower(): result}

class CoursesApi(Resource):
    @jwt_required()
    def get(self):
        courses = Course.query.all()
        schema = CourseSchema(many=True, exclude=('users',))
        result = schema.dump(courses)
        return {'courses': result}

    @jwt_required()
    def post(self):
        return create_and_commit(Course, course_schema, request.get_json())


class LoginApi(Resource):
    def post(self):
        json_data = request.get_json()

        try:
            data = AuthenticationSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422


        user = User.query.filter_by(email=data['email']).first()
        if (not user) or (not user.check_password(data['password'])):
            return {'message': 'Authentication failed'}, 401

        response = jsonify({'logged_in': data['email']})
        access_token = create_access_token(identity=user)
        set_access_cookies(response, access_token)
        return response


class LogoutApi(Resource):
    def post(self):
        response = jsonify({"message": "logout successful"})
        unset_jwt_cookies(response)
        return response


class QuestionApi(Resource):
    def dump_by_type(question):
        if question.type == QuestionType.SHORT_ANSWER:
            return sa_question_schema.dump(question)
        elif question.type == QuestionType.MULTIPLE_CHOICE:
            return mc_question_schema.dump(question)
        elif question.type == QuestionType.CODE_JUMBLE:
            return cj_question_schema.dump(question)
        else:
            return question_schema.dump(question)


    @jwt_required()
    def get(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()
        if q:
            return {"question": QuestionApi.dump_by_type(q)}
        else:
            return {'message': f"Question {question_id} not found."}, 404

    @jwt_required()
    def delete(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()

        if q:
            deleted_q = QuestionApi.dump_by_type(q)
            db.session.delete(q)
            db.session.commit()

            # TODO: ensure all attempts get deleted as well

            return {"deleted": deleted_q}

        else:
            return {'message': f"Question {question_id} not found."}, 404

class CourseQuestionApi(Resource):
    @jwt_required()
    def delete(self, course_id, question_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        q = course.questions.filter_by(id=question_id).one_or_none()
        if not q:
            return {'message': f"Question {question_id} not found in Course {course_id}."}, 404
        deleted_q = QuestionApi.dump_by_type(q)
        course.questions.remove(q)
        db.session.commit()

        return {"removed": deleted_q}

class IdListSchema(Schema):
    ids = fields.List(fields.Int(), required=True)


class RosterApi(Resource):
    @jwt_required()
    def get(self, course_id):
        c = Course.query.filter_by(id=course_id).one_or_none()
        if c:
            result = users_schema.dump(c.users)
            return {"roster": result}
        else:
            return {'message': f"Course {course_id} not found."}, 404

    @jwt_required()
    def post(self, course_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        # validate and load the list of student IDs
        try:
            data = IdListSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422

        already_enrolled = []
        newly_enrolled = []
        invalid_ids = []

        for user_id in data['ids']:
            user = User.query.filter_by(id=user_id).one_or_none()

            if user:
                if user in course.users:
                    already_enrolled.append(user)
                else:
                    newly_enrolled.append(user)
                    course.users.append(user)

            else:
                invalid_ids.append(user_id)

        db.session.commit()

        return {
            "newly-enrolled": UserSchema(many=True, only=("id", "email",
                                                          "first_name",
                                                          "last_name")).dump(
                                                              newly_enrolled),
            "already-enrolled": UserSchema(many=True, only=("id", "email",
                                                            "first_name",
                                                            "last_name")).dump(
                                                                already_enrolled),
            "invalid-ids": invalid_ids}


class EnrolledStudentApi(Resource):
    @jwt_required()
    def delete(self, course_id, student_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        s = course.users.filter_by(id=student_id).one_or_none()
        if not s:
            return {'message': f"User {student_id} not enrolled in Course {course_id}."}, 404

        removed_student = UserSchema(only=("email", "last_name", "first_name")).dump(s)
        course.users.remove(s)
        db.session.commit()

        return {"removed": removed_student}


class CourseQuestionsApi(Resource):
    @jwt_required()
    def get(self, course_id):
        c = Course.query.filter_by(id=course_id).one_or_none()
        if c:
            result = QuestionSchema(only=("id",)).dump(c.questions, many=True)
            return {"question_ids": [q['id'] for q in result]}
        else:
            return {'message': f"Course {course_id} not found."}, 404

    @jwt_required()
    def post(self, course_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        # validate and load the list of question IDs
        try:
            data = IdListSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422

        good_ones = []
        bad_ones = []

        for q_id in data['ids']:
            q = Question.query.filter_by(id=q_id).one_or_none()

            if q:
                if q in course.questions:
                    bad_ones.append({q_id: "Course already has this question."})
                else:
                    good_ones.append(q)

            else:
                bad_ones.append({q_id: "No question with this ID."})

        if bad_ones:
            return {"errors": bad_ones}, 400

        for q in good_ones:
            course.questions.append(q)

        db.session.commit()

        return {"questions": QuestionSchema().dump(good_ones, many=True)}


class QuestionsApi(Resource):
    @jwt_required()
    def get(self):
        questions = Question.query.all()
        result = question_schema.dump(questions, many=True)
        return {'questions': result}

    @jwt_required()
    def post(self):
        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        # check that basic question fields exists
        errors = question_schema.validate(json_data)
        if errors:
            return errors, 422

        # based on the type of question, pick the schema to load with
        if json_data['type'] == 'short-answer':
            schema = sa_question_schema
        elif json_data['type'] == 'multiple-choice':
            schema = mc_question_schema
        elif json_data['type'] == 'code-jumble':
            schema = cj_question_schema

        try:
            obj = schema.load(json_data)
        except ValidationError as err:
            return err.messages, 422

        db.session.add(obj)

        # FIXME: set author to be current_user when API login is implemented
        author = User.query.filter_by(id=1).first()
        author.authored_questions.append(obj)

        db.session.commit()

        return {"question": schema.dump(obj)}


from app.db_models import (
    QuestionType, AnswerOption, Course, ShortAnswerQuestion,
    MultipleChoiceQuestion, User, Question, JumbleBlock, CodeJumbleQuestion,
    Textbook, TextbookSection, SourceType
)
