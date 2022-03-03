from flask import request
from flask_restful import Resource, Api
from marshmallow import (
    Schema, fields, ValidationError, validates, pre_load, EXCLUDE
)
from marshmallow.decorators import post_load
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime
from enum import Enum
import secrets

from app import db

class QuestionSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    type = fields.Method("get_type", required=True, deserialize="create_type")
    prompt = fields.Str(required=True)

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


class ObjectiveSchema(Schema):
    id = fields.Int(dump_only=True)
    pass


class SourceSchema(Schema):
    id = fields.Int(dump_only=True)
    pass


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



class SectionSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    course = fields.Str(required=True)
    number = fields.Int(required=True)
    users = fields.List(fields.Nested(UserSchema), dump_only=True)


user_schema = UserSchema()
users_schema = UserSchema(many=True)
section_schema = SectionSchema()
question_schema = QuestionSchema(unknown=EXCLUDE)
sa_question_schema = ShortAnswerQuestionSchema()
mc_question_schema = MultipleChoiceQuestionSchema()
cj_question_schema = CodeJumbleQuestionSchema()


def init_app(flask_app):
    rf_api = Api(flask_app)
    rf_api.add_resource(UserApi, '/api/user/<int:user_id>')
    rf_api.add_resource(UsersApi, '/api/users')
    rf_api.add_resource(SectionApi, '/api/section/<int:section_id>')
    rf_api.add_resource(SectionQuestionsApi,
                        '/api/section/<int:section_id>/questions')
    rf_api.add_resource(QuestionApi, '/api/question/<int:question_id>')
    rf_api.add_resource(QuestionsApi, '/api/questions')
    rf_api.add_resource(SectionsApi, '/api/sections')


class UserApi(Resource):
    def get(self, user_id):
        u = User.query.filter_by(id=user_id).one_or_none()
        if u:
            return user_schema.dump(u)
        else:
            {}, 404


class UsersApi(Resource):
    def get(self):
        users = User.query.all()
        result = users_schema.dump(users)
        return {'users': result}

    def post(self):
        return create_and_commit(User, user_schema, request.get_json())


class SectionApi(Resource):
    def get(self, section_id):
        s = Section.query.filter_by(id=section_id).one_or_none()
        if s:
            return section_schema.dump(s)
        else:
            return {'message': f"Section {section_id} not found."}, 404


def create_and_commit(obj_type, schema, json_data):
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
    db.session.commit()

    result = schema.dump(obj)
    return {obj_type.__name__.lower(): result}

class SectionsApi(Resource):
    def get(self):
        sections = Section.query.all()
        schema = SectionSchema(many=True, exclude=('users',))
        result = schema.dump(sections)
        return {'sections': result}

    def post(self):
        return create_and_commit(Section, section_schema, request.get_json())


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


    def get(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()
        if q:
            return {"question": QuestionApi.dump_by_type(q)}
        else:
            return {'message': f"Question {question_id} not found."}, 404


class QuestionListSchema(Schema):
    question_ids = fields.List(fields.Int(), required=True)


class SectionQuestionsApi(Resource):
    def get(self, section_id):
        s = Section.query.filter_by(id=section_id).one_or_none()
        if s:
            result = QuestionSchema(only=("id",)).dump(s.questions, many=True)
            return {"question_ids": [q['id'] for q in result]}
        else:
            return {'message': f"Section {section_id} not found."}, 404

    def post(self, section_id):
        s = Section.query.filter_by(id=section_id).one_or_none()
        if not s:
            return {'message': f"Section {section_id} not found."}, 404

        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        # validate and load the list of questions
        try:
            data = QuestionListSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422

        good_ones = []
        bad_ones = []

        for q_id in data['question_ids']:
            # FIXME: check if question is already in the section
            q = Question.query.filter_by(id=q_id).one_or_none()

            if q:
                if q in s.questions:
                    bad_ones.append({q_id: "Section already has this question."})
                else:
                    good_ones.append(q)

            else:
                bad_ones.append({q_id: "No question with this ID."})

        if bad_ones:
            return {"errors": bad_ones}, 400

        for q in good_ones:
            s.questions.append(q)

        db.session.commit()

        return {"questions": QuestionSchema().dump(good_ones, many=True)}


class QuestionsApi(Resource):
    def get(self):
        questions = Question.query.all()
        result = question_schema.dump(questions, many=True)
        return {'questions': result}

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
        db.session.commit()

        print(type(obj))
        print(obj)
        return {"question": schema.dump(obj)}


from app.db_models import (
    QuestionType, AnswerOption, Section, ShortAnswerQuestion,
    MultipleChoiceQuestion, User, Question, JumbleBlock, CodeJumbleQuestion
)
