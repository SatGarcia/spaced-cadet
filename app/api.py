from flask import request, jsonify
from flask_restful import Resource, Api
from marshmallow import (
    Schema, fields, ValidationError, validates, pre_load, EXCLUDE
)
from flask_jwt_extended import (
    jwt_required, create_access_token, set_access_cookies, unset_jwt_cookies,
    current_user
)
from marshmallow.decorators import post_load
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime
from enum import Enum
import secrets

from app import db
from app.user_views import markdown_to_html

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

class AuthenticationSchema(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True)

class ImmutableFieldError(Exception):
    pass


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


class ShortAnswerQuestionSchema(QuestionSchema):
    answer = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD

    def make_obj(self, data):
        return ShortAnswerQuestion(**data)

    def update_obj(self, question, data):
        super().update_obj(question, data)

        for field in ['answer']:
            if field in data:
                setattr(question, field, data[field])


class AnswerOptionSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD
    correct = fields.Boolean(required=True)


class MultipleChoiceQuestionSchema(QuestionSchema):
    options = fields.List(fields.Nested(AnswerOptionSchema), required=True)

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


class JumbleBlockSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(required=True)  # CHANGE TO FUNCTION/METHOD
    correct_index = fields.Int(required=True, data_key='correct-index')
    correct_indent = fields.Int(required=True, data_key='correct-indent')


class CodeJumbleQuestionSchema(QuestionSchema):
    language = fields.Str(required=True)
    blocks = fields.List(fields.Nested(JumbleBlockSchema), required=True)

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

    users = fields.List(fields.Nested(UserSchema, only=('id', 'email')),
                        dump_only=True)
    meetings = fields.List(fields.Nested(ClassMeetingSchema,
                                          only=('id', 'title')),
                           dump_only=True)
    textbooks = fields.List(fields.Nested("TextbookSchema",
                                          only=("id", "title", "edition")),
                            dump_only=True)

    @validates("name")
    def unique_name(self, course_name):
        if Course.query.filter_by(name=course_name).count() > 0:
            raise ValidationError("name must be unique")


user_schema = UserSchema()
users_schema = UserSchema(many=True)
course_schema = CourseSchema()
topic_schema = TopicSchema()
topics_schema = TopicSchema(many=True)
question_schema = QuestionSchema(unknown=EXCLUDE)
sa_question_schema = ShortAnswerQuestionSchema()
ac_question_schema = AutoCheckQuestionSchema()
mc_question_schema = MultipleChoiceQuestionSchema()
cj_question_schema = CodeJumbleQuestionSchema()
textbook_schema = TextbookSchema()
textbook_section_schema = TextbookSectionSchema()
class_meeting_schema = ClassMeetingSchema()
class_meetings_schema = ClassMeetingSchema(many=True)
objective_schema = LearningObjectiveSchema()
objectives_schema = LearningObjectiveSchema(many=True)
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
    rf_api.add_resource(CourseTextbooksApi,
                        '/api/course/<int:course_id>/textbooks',
                        endpoint='course_textbooks')
    rf_api.add_resource(CourseMeetingsApi,
                        '/api/course/<int:course_id>/meetings',
                        endpoint='course_meetings')

    rf_api.add_resource(TopicApi, '/api/topic/<int:topic_id>')
    rf_api.add_resource(TopicsApi, '/api/topics',
                        endpoint='topics_api')
    rf_api.add_resource(ObjectiveTopicApi,
                        '/api/objective/<int:objective_id>/topic',
                        endpoint='object_topic')
    rf_api.add_resource(SourceTopicsApi,
                        '/api/source/<int:source_id>/topics',
                        endpoint='source_topics')

    rf_api.add_resource(TextbookApi, '/api/textbook/<int:textbook_id>')
    rf_api.add_resource(TextbooksApi, '/api/textbooks')
    rf_api.add_resource(TextbookSectionsApi, '/api/textbook/<int:textbook_id>/sections')
    rf_api.add_resource(ClassMeetingsApi, '/api/class-meetings')

    rf_api.add_resource(QuestionApi, '/api/question/<int:question_id>',
                        endpoint='question_api')
    rf_api.add_resource(QuestionsApi, '/api/questions',
                        endpoint='questions_api')

    rf_api.add_resource(ObjectiveApi, '/api/objective/<int:objective_id>')
    rf_api.add_resource(ObjectivesApi, '/api/objectives',
                        endpoint='objectives_api')
    rf_api.add_resource(QuestionObjectiveApi,
                        '/api/question/<int:question_id>/objective',
                        endpoint='question_objective')



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
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        return create_and_commit(Textbook, textbook_schema, request.get_json())


class TextbookSectionsApi(Resource):
    @jwt_required()
    def get(self, textbook_id):
        t = Textbook.query.filter_by(id=textbook_id).one_or_none()

        if not t:
            return {"message": f"No textbook found with id {textbook_id}"}, 404

        # only return public sections or those which this user has authored
        available_sections = t.sections.filter(db.or_(TextbookSection.public == True,
                                                      TextbookSection.author == current_user))

        result = textbook_section_schema.dump(available_sections, many=True)
        return {'textbook_sections': result}

    @jwt_required()
    def post(self, textbook_id):
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        t = Textbook.query.filter_by(id=textbook_id).one_or_none()

        if not t:
            return {"message": f"No textbook found with id {textbook_id}"}, 404

        return create_and_commit(TextbookSection, textbook_section_schema,
                                 request.get_json(), add_to=t.sections)


class ClassMeetingsApi(Resource):
    @jwt_required()
    def get(self):
        if not current_user.admin:
            return {'message': "Unauthorized access"}, 401

        meetings = ClassMeetings.query.all()
        result = class_meetings_schema.dump(meetings)
        return {'class-meetings': result}

    @jwt_required()
    def post(self):
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        return create_and_commit(ClassMeeting, class_meeting_schema, request.get_json())


class UserApi(Resource):
    @jwt_required()
    def get(self, user_id):
        if not current_user.admin:
            return {'message': "Unauthorized access"}, 401

        u = User.query.filter_by(id=user_id).one_or_none()
        if u:
            return user_schema.dump(u)
        else:
            return {"message": f"No user found with id {user_id}"}, 404

    @jwt_required()
    def delete(self, user_id):
        if not current_user.admin:
            return {'message': "Unauthorized access"}, 401

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
        if not current_user.admin:
            return {'message': "Unauthorized access"}, 401

        users = User.query.all()
        result = users_schema.dump(users)
        return {'users': result}

    @jwt_required()
    def post(self):
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        return create_and_commit(User, user_schema, request.get_json())


class CourseApi(Resource):
    @jwt_required()
    def get(self, course_id):
        c = Course.query.filter_by(id=course_id).one_or_none()
        if c:
            # Limit access to admins and course instructors
            if (not current_user.admin)\
                    and (not current_user.instructor or current_user not in course.users):
                return {'message': "Unauthorized access"}, 401

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
        # admins will get all courses, everyone else gets only the courses
        # they are part of
        if current_user.admin:
            courses = Course.query.all()
        else:
            courses = current_user.courses

        schema = CourseSchema(many=True, exclude=('users',))
        result = schema.dump(courses)
        return {'courses': result}

    @jwt_required()
    def post(self):
        # Only instructors and admins are allowed to create courses
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

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


class TopicApi(Resource):
    @jwt_required()
    def get(self, topic_id):
        t = Topic.query.filter_by(id=topic_id).one_or_none()
        if t:
            # Limit access to admins and instructors
            if not (current_user.admin or current_user.instructor):
                return {'message': "Unauthorized access"}, 401

            return topic_schema.dump(t)
        else:
            return {'message': f"Topic {topic_id} not found."}, 404


class TopicsApi(Resource):
    @jwt_required()
    def get(self):
        if not (current_user.admin or current_user.instructor):
            return {'message': "Unauthorized access"}, 401

        query_str = request.args.get("q")

        if query_str is None:
            topics = Topic.query
        else:
            topics = Topic.search(query_str)[0]

        topics = topics.order_by(Topic.text)


        schema = TopicSchema(many=True, exclude=('sources', 'objectives'))
        result = schema.dump(topics.all())
        return {'topics': result}

    @jwt_required()
    def post(self):
        # Only instructors and admins are allowed to create topics
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        return create_and_commit(Topic, topic_schema, request.get_json())


class ObjectiveTopicApi(Resource):
    @jwt_required()
    def get(self, objective_id):
        o = Objective.query.filter_by(id=objective_id).one_or_none()
        if not o:
            return {"message": f"No objective found with id {objective_id}"}, 404

        elif not (o.public or current_user.admin or o.author == current_user):
            # has to be a public question or user needs to be the question's
            # author or an admin to access this
            return {'message': "Unauthorized access"}, 401

        elif not o.topic:
            return {"message": f"No topic found for objective with id {objective_id}"}, 404

        return topic_schema.dump(o.topic)


    @jwt_required()
    def put(self, objective_id):
        o = Objective.query.filter_by(id=objective_id).one_or_none()
        if not o:
            return {"message": f"No objective found with id {objective_id}"}, 404

        elif not (current_user.admin or o.author == current_user):
            # user needs to be the objective's author or an admin to access
            # this
            return {'message': "Unauthorized access"}, 401


        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        try:
            data = SingleIdSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422

        t = Topic.query.filter_by(id=data['id']).first()
        if not t:
            return {"message": f"No topic found with id {data['id']}"}, 400

        o.topic = t
        db.session.commit()

        return {'updated': objective_schema.dump(o)}


    @jwt_required()
    def delete(self, objective_id):
        o = Objective.query.filter_by(id=objective_id).one_or_none()
        if not o:
            return {"message": f"No objective found with id {objective_id}"}, 404

        elif not (current_user.admin or o.author == current_user):
            return {'message': "Unauthorized access"}, 401

        elif not o.topic:
            return {'message': "No topic to delete."}, 400

        else:
            o.topic = None
            db.session.commit()
            return {'updated': objective_schema.dump(o)}


class SourceTopicsApi(Resource):
    @jwt_required()
    def get(self, source_id):
        s = Source.query.filter_by(id=source_id).one_or_none()
        if s:
            # Limit access to admins and source author
            if not (current_user.admin or current_user == s.author):
                return {'message': 'Unauthorized access.'}, 401

            result = TopicSchema(only=('id', 'text'), many=True).dump(s.topics)
            return {"source-topics": result}

        else:
            return {'message': f"Source {source_id} not found."}, 404

    @jwt_required()
    def post(self, source_id):
        source = Source.query.filter_by(id=source_id).one_or_none()
        if not source:
            return {'message': f"Source {source_id} not found."}, 404

        # Limit access to admins and source author
        if not (current_user.admin or current_user == source.author):
            return {'message': 'Unauthorized access.'}, 401

        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        # validate and load the list of question IDs
        try:
            data = IdListSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422

        duplicate_topics = []
        new_topics = []
        invalid_ids = []

        for topic_id in data['ids']:
            topic = Topic.query.filter_by(id=topic_id).one_or_none()

            if topic:
                if topic in source.topics:
                    duplicate_topics.append(topic)
                else:
                    new_topics.append(topic)
                    source.topics.append(topic)

            else:
                invalid_ids.append(topic_id)

        db.session.commit()

        return {
            "added-topics": TopicSchema(many=True, only=("id", "text")).dump(new_topics),
            "duplicates": TopicSchema(many=True, only=("id", "text")).dump(duplicate_topics),
            "invalid-ids": invalid_ids
        }



class LogoutApi(Resource):
    def post(self):
        response = jsonify({"message": "logout successful"})
        unset_jwt_cookies(response)
        return response


class QuestionApi(Resource):
    def dump_by_type(question):
        if question.type == QuestionType.SHORT_ANSWER:
            return sa_question_schema.dump(question)
        if question.type == QuestionType.AUTO_CHECK:
            return ac_question_schema.dump(question)
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
            # Limit access to admins, question author, and (if public) all
            # instructors
            if not ((q.public and current_user.instructor)\
                    or current_user.admin\
                    or q.author == current_user):
                return {'message': "Unauthorized access"}, 401

            return {"question": QuestionApi.dump_by_type(q)}
        else:
            return {'message': f"Question {question_id} not found."}, 404

    @jwt_required()
    def delete(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()

        if q:
            # Limit access to admins and the question author.
            # TODO: restrict removal of public questions?
            if not (current_user.admin or q.author == current_user):
                return {'message': "Unauthorized access"}, 401

            deleted_q = QuestionApi.dump_by_type(q)
            db.session.delete(q)
            db.session.commit()

            # TODO: ensure all attempts get deleted as well

            return {"deleted": deleted_q}

        else:
            return {'message': f"Question {question_id} not found."}, 404

    @jwt_required()
    def patch(self, question_id):
        # Limit access to instructors and admins
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        q = Question.query.filter_by(id=question_id).first()
        if not q:
            return {'message': f"Question {question_id} not found."}, 404

        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        # check that basic question fields exists
        errors = question_schema.validate(json_data, partial=True)
        if errors:
            return errors, 422

        # based on the type of question, pick the schema to load with
        if q.type == QuestionType.SHORT_ANSWER:
            schema = sa_question_schema
        elif q.type == QuestionType.AUTO_CHECK:
            schema = ac_question_schema
        elif q.type == QuestionType.MULTIPLE_CHOICE:
            schema = mc_question_schema
        elif q.type == QuestionType.CODE_JUMBLE:
            schema = cj_question_schema

        try:
            data = schema.load(json_data, partial=True)
        except ValidationError as err:
            return err.messages, 422

        try:
            schema.update_obj(q, data)
        except ImmutableFieldError:
            return {"message": "Question type may not be changed."}, 400
        else:
            db.session.commit()
            return {"updated": schema.dump(q)}

class CourseQuestionApi(Resource):
    @jwt_required()
    def delete(self, course_id, question_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        # Limit access to admins and course instructors
        if not (current_user.admin \
                or (current_user.instructor and (current_user in course.users))):
            return {'message': 'Unauthorized access.'}, 401

        q = course.questions.filter_by(id=question_id).one_or_none()
        if not q:
            return {'message': f"Question {question_id} not found in Course {course_id}."}, 404
        deleted_q = QuestionApi.dump_by_type(q)
        course.questions.remove(q)
        db.session.commit()

        return {"removed": deleted_q}

class IdListSchema(Schema):
    ids = fields.List(fields.Int(), required=True)

class SingleIdSchema(Schema):
    id = fields.Int(required=True)


class RosterApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = UserSchema(only=('id','email'))
        return course_collections_getter(course_id, schema, 'users')

    @jwt_required()
    def post(self, course_id):
        schema = UserSchema(only=('id','email'))
        return course_collections_poster(course_id, schema, 'users',
                                         User)


class EnrolledStudentApi(Resource):
    @jwt_required()
    def delete(self, course_id, student_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        # Limit access to admins and course instructors
        if (not current_user.admin)\
                and (not current_user.instructor or current_user not in course.users):
            return {'message': 'Unauthorized access.'}, 401

        s = course.users.filter_by(id=student_id).one_or_none()
        if not s:
            return {'message': f"User {student_id} not enrolled in Course {course_id}."}, 404

        removed_student = UserSchema(only=("email", "last_name", "first_name")).dump(s)
        course.users.remove(s)
        db.session.commit()

        return {"removed": removed_student}


def course_collections_getter(course_id, schema, collection_name):
    c = Course.query.filter_by(id=course_id).one_or_none()
    if c:
        # Limit access to admins and course instructors
        if (not current_user.admin)\
                and (not current_user.instructor or current_user not in c.users):
            return {'message': 'Unauthorized access.'}, 401

        result = schema.dump(getattr(c, collection_name), many=True)
        return {collection_name: result}

    else:
        return {'message': f"Course {course_id} not found."}, 404


def course_collections_poster(course_id, schema, collection_name, collection_type):
    # NOTE: collection_type is the type of item in collection (e.g. User or
    # Question)
    course = Course.query.filter_by(id=course_id).one_or_none()
    if not course:
        return {'message': f"Course {course_id} not found."}, 404

    # Limit access to admins and course instructors
    if (not current_user.admin)\
            and (not current_user.instructor or current_user not in course.users):
        return {'message': 'Unauthorized access.'}, 401

    json_data = request.get_json()

    if not json_data:
        return {"message": "No input data provided"}, 400

    # validate and load the list of question IDs
    try:
        data = IdListSchema().load(json_data)
    except ValidationError as err:
        return err.messages, 422

    ignored = []
    added = []
    invalid_ids = []

    for item_id in data['ids']:
        item = collection_type.query.filter_by(id=item_id).one_or_none()

        if item:
            collection = getattr(course, collection_name)
            if item in collection:
                ignored.append(item)
            else:
                added.append(item)
                collection.append(item)

        else:
            invalid_ids.append(item_id)

    db.session.commit()

    return {
        "added": schema.dump(added, many=True),
        "previously-added": schema.dump(ignored, many=True),
        "invalid-ids": invalid_ids
    }


class CourseQuestionsApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = QuestionSchema(only=('id','prompt'))
        return course_collections_getter(course_id, schema, 'questions')

    @jwt_required()
    def post(self, course_id):
        schema = QuestionSchema(only=('id','prompt'))
        return course_collections_poster(course_id, schema, 'questions',
                                         Question)


class CourseTextbooksApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = TextbookSchema(only=('id','title','edition'))
        return course_collections_getter(course_id, schema, 'textbooks')

    @jwt_required()
    def post(self, course_id):
        schema = TextbookSchema(only=('id','title','edition'))
        return course_collections_poster(course_id, schema, 'textbooks',
                                         Textbook)


class CourseMeetingsApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = ClassMeetingSchema(only=('id','title'))
        return course_collections_getter(course_id, schema, 'meetings')

    @jwt_required()
    def post(self, course_id):
        schema = ClassMeetingSchema(only=('id','title'))
        return course_collections_poster(course_id, schema, 'meetings',
                                         ClassMeeting)


class QuestionsApi(Resource):
    @jwt_required()
    def get(self):
        # Limit access to instructors and admins
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        query_str = request.args.get("q")

        if query_str is None:
            questions = Question.query
        else:
            questions = Question.search(query_str)[0]

        target_author = request.args.get('author')

        if target_author == 'self':
            # restrict results to current user if author=self is specified
            questions = questions.filter(Question.author_id == current_user.id)

        elif target_author:
            # Restrict results to specific user id if author is given (and not
            # it's not 'self'). This option is only available to admins
            if not current_user.admin:
                return {'message': "author usage restricted to 'self'"}, 401

            try:
                target_id = int(target_author)
            except:
                return {'message': f"Invalid value for author argument: {target_author}"}, 400
            else:
                questions = questions.filter(Question.author_id == target_id)

        elif not current_user.admin:
            # if no author specified and user isn't an admin, get all public
            # questions as well as those that are authored by the current user
            questions = questions.filter(db.or_(Question.public == True,
                                                Question.author == current_user))

        result = question_schema.dump(questions.all(), many=True)
        return {'questions': result}


    @jwt_required()
    def post(self):
        # Limit access to instructors and admins
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

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
        if json_data['type'] == 'auto-check':
            schema = ac_question_schema
        elif json_data['type'] == 'multiple-choice':
            schema = mc_question_schema
        elif json_data['type'] == 'code-jumble':
            schema = cj_question_schema

        try:
            data = schema.load(json_data)
        except ValidationError as err:
            return err.messages, 422

        obj = schema.make_obj(data)
        db.session.add(obj)

        author = User.query.filter_by(id=current_user.id).first()
        author.authored_questions.append(obj)

        db.session.commit()

        return {"question": schema.dump(obj)}


class ObjectiveApi(Resource):
    @jwt_required()
    def get(self, objective_id):
        t = Objective.query.filter_by(id=objective_id).one_or_none()
        if t:
            if request.args.get("html") is not None:
                schema = LearningObjectiveSchema()
                schema.context = {"html": True}
            else:
                schema = objective_schema

            return schema.dump(t)
        else:
            return {"message": f"No learning objective found with id {objective_id}"}, 404

    @jwt_required()
    def delete(self, objective_id):
        lo = Objective.query.filter_by(id=objective_id).one_or_none()

        if lo:
            # Limit access to admins and the question author.
            # TODO: restrict removal of public learning objectives
            if not (current_user.admin or lo.author == current_user):
                return {'message': "Unauthorized access"}, 401

            deleted_lo = objective_schema.dump(lo)
            db.session.delete(lo)
            db.session.commit()

            return {"deleted": deleted_lo}

        else:
            return {"message": f"No learning objective found with id {objective_id}"}, 404

    @jwt_required()
    def patch(self, objective_id):
        o = Objective.query.filter_by(id=objective_id).first()
        if not o:
            return {'message': f"Objective {objective_id} not found."}, 404

        # Limit access to admins and objective author
        if not (current_user.admin or o.author == current_user):
            return {'message': "Unauthorized access"}, 401

        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        try:
            data = objective_schema.load(json_data, partial=True)
        except ValidationError as err:
            return err.messages, 422

        objective_schema.update_obj(o, data)
        db.session.commit()

        return {"updated": objective_schema.dump(o)}


class QuestionObjectiveApi(Resource):
    @jwt_required()
    def get(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()
        if not q:
            return {"message": f"No question found with id {question_id}"}, 404

        elif (not q.public) and (not current_user.admin) and (q.author != current_user):
            # has to be a public question or user needs to be the question's
            # author or an admin to access this
            return {'message': "Unauthorized access"}, 401

        elif not q.objective:
            return {"message": f"No learning objective found for question with id {question_id}"}, 404

        else:
            if request.args.get("html") is not None:
                schema = LearningObjectiveSchema()
                schema.context = {"html": True}
            else:
                schema = objective_schema

            return schema.dump(q.objective)

    @jwt_required()
    def put(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()
        if not q:
            return {"message": f"No question found with id {question_id}"}, 404

        elif (not current_user.admin) and (q.author != current_user):
            # user needs to be the question's author or an admin to access
            # this
            return {'message': "Unauthorized access"}, 401


        json_data = request.get_json()

        if not json_data:
            return {"message": "No input data provided"}, 400

        try:
            data = SingleIdSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422

        o = Objective.query.filter_by(id=data['id']).first()
        if not o:
            return {"message": f"No learning objective found with id {data['id']}"}, 400

        q.objective = o
        db.session.commit()

        return {'updated': question_schema.dump(q)}


    @jwt_required()
    def delete(self, question_id):
        q = Question.query.filter_by(id=question_id).one_or_none()
        if not q:
            return {"message": f"No question found with id {question_id}"}, 404

        elif (not current_user.admin) and (q.author != current_user):
            # user needs to be the question's author or an admin to access
            # this
            return {'message': "Unauthorized access"}, 401

        elif not q.objective:
            return {'message': "No learning objective to delete."}, 400

        else:
            q.objective = None
            db.session.commit()
            return {'updated': question_schema.dump(q)}


class ObjectivesApi(Resource):
    @jwt_required()
    def get(self):
        query_str = request.args.get("q")

        if query_str is None:
            objectives = Objective.query
        else:
            objectives = Objective.search(query_str)[0]

        target_author = request.args.get('author')

        if target_author == 'self':
            # restrict results to current user if author=self is specified
            objectives = objectives.filter(Objective.author_id == current_user.id)

        elif target_author:
            # Restrict results to specific user id if author is given (and not
            # it's not 'self'). This option is only available to admins
            if not current_user.admin:
                return {'message': "author usage restricted to 'self'"}, 401

            try:
                target_id = int(target_author)
            except:
                return {'message': f"Invalid value for author argument: {target_author}"}, 400
            else:
                objectives = objectives.filter(Objective.author_id == target_id)

        elif not current_user.admin:
            # if no author specified and user isn't an admin, get all public
            # objectives as well as those that are authored by the current user
            objectives = objectives.filter(db.or_(Objective.public == True,
                                                  Objective.author == current_user))

        # if they used the 'html' argument, get the HTML version of the field
        if request.args.get("html") is not None:
            schema = LearningObjectiveSchema(many=True)
            schema.context = {"html": True}
        else:
            schema = objectives_schema

        result = schema.dump(objectives.all())
        return {'learning_objectives': result}

    @jwt_required()
    def post(self):
        if not (current_user.instructor or current_user.admin):
            return {'message': "Unauthorized access"}, 401

        return create_and_commit(Objective,
                                 objective_schema,
                                 request.get_json(),
                                 add_to=current_user.authored_objectives)



from app.db_models import (
    QuestionType, AnswerOption, Course, ShortAnswerQuestion,
    AutoCheckQuestion, MultipleChoiceQuestion, User, Question, JumbleBlock,
    CodeJumbleQuestion, Textbook, TextbookSection, SourceType, Objective,
    Topic, ClassMeeting
)
