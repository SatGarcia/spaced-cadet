from flask import (
    Blueprint, url_for, redirect, request, abort, jsonify
)
from flask_restful import Resource, Api
from marshmallow import Schema, fields, ValidationError, pre_load
from marshmallow.decorators import post_load
from datetime import date, timedelta, datetime
from enum import Enum

from app import db

api = Blueprint('api', __name__)

class QuestionSchema(Schema):
    from app.db_models import Question
    model_class = Question

    id = fields.Int(dump_only=True)
    type = fields.Method("get_type", deserialize="create_type")
    prompt = fields.Str()

    def get_type(self, obj):
        return obj.type.value

    def create_type(self, value):
        try:
            QuestionType(value)
        except ValueError as error:
            raise ValidationError("Invalid question type.") from error

    @post_load
    def make_question(self, data, **kwargs):
        return type(self).model_class(**data)


class ShortAnswerQuestionSchema(QuestionSchema):
    from app.db_models import ShortAnswerQuestion
    model_class = ShortAnswerQuestion

    answer = fields.Str()

    """
    @post_dump
    def foo(self, data, **kwargs):
        data['answer'] = self.answer
    """


class AnswerOptionSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str()
    correct = fields.Boolean()


class MultipleChoiceQuestionSchema(QuestionSchema):
    from app.db_models import MultipleChoiceQuestion
    model_class = MultipleChoiceQuestion

    options = fields.List(fields.Nested(AnswerOptionSchema))


class JumbleBlockSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str()
    correct_index = fields.Int()
    correct_indent = fields.Int()


class CodeJumbleQuestionSchema(QuestionSchema):
    from app.db_models import CodeJumbleQuestion
    model_class = CodeJumbleQuestion

    language = fields.Str()
    blocks = fields.List(fields.Nested(JumbleBlockSchema))


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
    id = fields.Int(dump_only=True)
    username = fields.Str()
    email = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()
    password_hash = fields.Str(load_only=True)
    admin = fields.Boolean()
    instructor = fields.Boolean()


class SectionSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    number = fields.Int()
    users = fields.List(fields.Nested(UserSchema))

    """
    formatted_name = fields.Method("format_name", dump_only=True)

    def format_name(self, author):
        return f"{author.last}, {author.first}"
    """


user_schema = UserSchema()
users_schema = UserSchema(many=True)
section_schema = SectionSchema()
question_schema = QuestionSchema()
sa_question_schema = ShortAnswerQuestionSchema()
mc_question_schema = MultipleChoiceQuestionSchema()
cj_question_schema = CodeJumbleQuestionSchema()


def init_app(flask_app):
    rf_api = Api(flask_app)
    rf_api.add_resource(UserApi, '/api/user/<int:user_id>')
    rf_api.add_resource(UsersApi, '/api/users')
    rf_api.add_resource(SectionApi, '/api/section/<int:section_id>')
    rf_api.add_resource(QuestionApi, '/api/question/<int:question_id>')


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


class SectionApi(Resource):
    def get(self, section_id):
        s = Section.query.filter_by(id=section_id).one_or_none()
        if s:
            #return s.format()
            return section_schema.dump(s)
        else:
            {}, 404

    """
    def put(self, section_id):
        todos[todo_id] = request.form['data']
        return {todo_id: todos[todo_id]}
    """

class QuestionApi(Resource):
    def get(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()
        if q:
            if q.type == QuestionType.SHORT_ANSWER:
                return sa_question_schema.dump(q)
            elif q.type == QuestionType.MULTIPLE_CHOICE:
                return mc_question_schema.dump(q)
            elif q.type == QuestionType.CODE_JUMBLE:
                return cj_question_schema.dump(q)
            else:
                return question_schema.dump(q)
        else:
            return {'message': f"Question {question_id} not found."}, 404


@api.route('/courses/<int:section_num>/questions')
def course_questions(section_num):
    """ Retrieves the questions associated with the given course. """
    section = Section.query.filter_by(id=section_num).first()

    if not section:
        abort(404)

    questions = section.questions.all()

    if len(questions) == 0:
        abort(404)

    return jsonify({
        'success': True,
        'questions': [q.format() for q in questions]
    })

@api.route('/courses/<int:section_num>/questions', methods=['POST'])
def create_question(section_num):
    """ Create a new question associated with a given course. """
    section = Section.query.filter_by(id=section_num).first()

    if not section:
        abort(404)

    if not request.json:
        abort(400)

    print("prompt field is of type", type(request.json['prompt']))

    # check that type and prompt fields are given and have valid type
    if ('type' not in request.json) or type(request.json['type']) != str:
        abort(400)
    elif ('prompt' not in request.json) or type(request.json['prompt']) != str:
        abort(400)

    # FIXME: require learning objective be given for new question (or maybe
    # allow them to specify text for learning objecive and have it also
    # create a new learning objective?

    if request.json['type'] == 'short-answer':
        # must have an answer field (string)
        if ('answer' not in request.json) or type(request.json['answer']) != str:
            abort(400)

        new_q = ShortAnswerQuestion(type=QuestionType.SHORT_ANSWER,
                                    prompt=request.json['prompt'],
                                    answer=request.json['answer'])

        new_q.section = section
        new_q.create()

        return jsonify({
            'success': True,
            'question': new_q.format()
        })

    elif request.json['type'] == 'multiple-choice':
        # need to have a list of options
        if ('options' not in request.json) or type(request.json['options']) != list:
            abort(400)

        new_q = MultipleChoiceQuestion(type=QuestionType.MULTIPLE_CHOICE,
                                       prompt=request.json['prompt'])
        new_q.section = section

        for opt in request.json['options']:
            # check that required fields are present and have the correct type
            if ('text' not in opt) or type(opt['text']) != str:
                abort(400)
            elif ('correct' not in opt) or type(opt['correct']) != bool:
                abort(400)

            ao = AnswerOption(text=opt['text'], correct=opt['correct'])
            new_q.options.append(ao)

        new_q.create()

        return jsonify({
            'success': True,
            'question': new_q.format()
        })

    abort(400)

from app.db_models import (
    QuestionType, AnswerOption, Section, ShortAnswerQuestion,
    MultipleChoiceQuestion, User, Question
)
