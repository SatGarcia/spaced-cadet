from flask import request, jsonify
from flask_restful import Resource, Api
from marshmallow import (
    Schema, fields, ValidationError, EXCLUDE
)
from flask_jwt_extended import (
    jwt_required, create_access_token, set_access_cookies, unset_jwt_cookies,
    current_user
)

from app import db
from app.auth import AuthorizationError
from app.db_models import (
    Question, QuestionSchema,
    QuestionType,
    ShortAnswerQuestion, ShortAnswerQuestionSchema,
    AutoCheckQuestion, AutoCheckQuestionSchema,
    MultipleChoiceQuestion, MultipleChoiceQuestionSchema,
    MultipleSelectionQuestion, MultipleSelectionQuestionSchema,
    AnswerOption,
    User, UserSchema,
    JumbleBlock,
    CodeJumbleQuestion, CodeJumbleQuestionSchema,
    Source,
    Textbook, TextbookSchema,
    TextbookSection, TextbookSectionSchema,
    Topic, TopicSchema,
    Objective, LearningObjectiveSchema,
    Course, CourseSchema,
    ClassMeeting, ClassMeetingSchema,
    Assessment, AssessmentSchema
)

class ImmutableFieldError(Exception):
    pass

def admin_only(item):
    if not current_user.admin:
        raise AuthorizationError()


def admin_or_course_instructor(course):
    if not (current_user.admin or (current_user.instructor and current_user in course.users)):
        raise AuthorizationError()


def admin_or_course_instructor_nested(course_collection):
    if not (current_user.admin\
            or (current_user.instructor and current_user in course_collection.course.users)):
        raise AuthorizationError()


def admin_or_author(obj):
    if not (current_user.admin or obj.author == current_user):
        raise AuthorizationError()


def item_collection_getter(item_type, item_id, schema, collection_name,
                              authorization_checker):
    item = item_type.query.filter_by(id=item_id).one_or_none()
    if item:
        # check that current_user is authorized
        try:
            authorization_checker(item)
        except AuthorizationError as e:
            return {'message': 'Unauthorized access.'}, 401

        result = schema.dump(getattr(item, collection_name), many=True)
        return {collection_name: result}

    else:
        return {'message': f"{item_type.__name__} with id {item_id} not found."}, 404


def item_collection_poster(item_type, item_id, schema, collection_name,
                            collection_type, authorization_checker):
    # NOTE: collection_type is the type of item in collection (e.g. User or
    # Question)
    item = item_type.query.filter_by(id=item_id).one_or_none()
    if not item:
        return {'message': f"{item_type.__name__} with id {item_id} not found."}, 404

    # check authorization for updating
    try:
        authorization_checker(item)
    except AuthorizationError as e:
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

    collection = getattr(item, collection_name)

    for new_item_id in data['ids']:
        item_to_add = collection_type.query.filter_by(id=new_item_id).one_or_none()

        if item_to_add:
            if item_to_add in collection:
                ignored.append(item_to_add)
            else:
                added.append(item_to_add)
                collection.append(item_to_add)

        else:
            invalid_ids.append(new_item_id)

    db.session.commit()

    return {
        "added": schema.dump(added, many=True),
        "previously-added": schema.dump(ignored, many=True),
        "invalid-ids": invalid_ids
    }


user_schema = UserSchema()
users_schema = UserSchema(many=True)
course_schema = CourseSchema()
assessment_schema = CourseSchema()
topic_schema = TopicSchema()
topics_schema = TopicSchema(many=True)
question_schema = QuestionSchema(unknown=EXCLUDE)
sa_question_schema = ShortAnswerQuestionSchema()
ac_question_schema = AutoCheckQuestionSchema()
mc_question_schema = MultipleChoiceQuestionSchema()
ms_question_schema = MultipleSelectionQuestionSchema()
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

    rf_api.add_resource(UserApi, '/api/user/<int:user_id>',
                        endpoint='user_api')
    rf_api.add_resource(UsersApi, '/api/users', endpoint='users_api')

    rf_api.add_resource(CourseApi, '/api/course/<int:course_id>',
                        endpoint="course")
    rf_api.add_resource(CoursesApi, '/api/courses',
                        endpoint='courses_api')

    rf_api.add_resource(RosterApi,
                        '/api/course/<int:course_id>/students')
    rf_api.add_resource(EnrolledStudentApi,
                        '/api/course/<int:course_id>/student/<int:student_id>',
                        endpoint="enrolled_student")
    rf_api.add_resource(CourseAssessmentQuestionsApi,
                        '/api/course/<int:course_id>/assessment/<int:assessment_id>/questions',
                        endpoint='course_assessment_questions')
    rf_api.add_resource(CourseAssessmentQuestionApi,
                        '/api/course/<int:course_id>/assessment/<int:assessment_id>/question/<int:question_id>',
                        endpoint='course_assessment_question')
    rf_api.add_resource(CourseTextbooksApi,
                        '/api/course/<int:course_id>/textbooks',
                        endpoint='course_textbooks')
    rf_api.add_resource(CourseTextbookApi,
                        '/api/course/<int:course_id>/textbook/<int:textbook_id>',
                        endpoint='course_textbook')
    rf_api.add_resource(CourseTopicsApi,
                        '/api/course/<int:course_id>/topics',
                        endpoint='course_topics')
    rf_api.add_resource(CourseTopicApi,
                        '/api/course/<int:course_id>/topic/<int:topic_id>',
                        endpoint='course_topic')
    rf_api.add_resource(CourseMeetingsApi,
                        '/api/course/<int:course_id>/meetings',
                        endpoint='course_meetings')

    rf_api.add_resource(TopicApi, '/api/topic/<int:topic_id>',
                        endpoint='topic_api')
    rf_api.add_resource(TopicsApi, '/api/topics',
                        endpoint='topics_api')
    rf_api.add_resource(ObjectiveTopicApi,
                        '/api/objective/<int:objective_id>/topic',
                        endpoint='objective_topic')
    rf_api.add_resource(SourceTopicsApi,
                        '/api/source/<int:source_id>/topics',
                        endpoint='source_topics')

    rf_api.add_resource(TextbookApi, '/api/textbook/<int:textbook_id>',
                        endpoint='textbook_api')
    rf_api.add_resource(TextbooksApi, '/api/textbooks',
                        endpoint='textbooks_api')
    rf_api.add_resource(TextbookSearchApi, '/api/textbooks/search',
                        endpoint='textbook_search_api')
    rf_api.add_resource(TextbookSectionsApi,
                        '/api/textbook/<int:textbook_id>/sections',
                        endpoint='textbook_sections')
    rf_api.add_resource(TextbookSectionTopicsApi,
                        '/api/textbook/<int:textbook_id>/section/<int:section_id>/topics',
                        endpoint='textbook_section_topics')
    rf_api.add_resource(ClassMeetingsApi, '/api/class-meetings',
                        endpoint='class_meetings')

    rf_api.add_resource(QuestionApi, '/api/question/<int:question_id>',
                        endpoint='question_api')
    rf_api.add_resource(QuestionsApi, '/api/questions',
                        endpoint='questions_api')

    rf_api.add_resource(ObjectiveApi, '/api/objective/<int:objective_id>',
                        endpoint='objective_api')
    rf_api.add_resource(ObjectivesApi, '/api/objectives',
                        endpoint='objectives_api')
    rf_api.add_resource(ObjectiveSearchApi, '/api/objectives/search',
                        endpoint='objective_search_api')
    rf_api.add_resource(QuestionObjectiveApi,
                        '/api/question/<int:question_id>/objective',
                        endpoint='question_objective')

    rf_api.add_resource(AssessmentApi, '/api/assessment/<int:assessment_id>',
                        endpoint="assessment_api")



class TextbookApi(Resource):
    @jwt_required()
    def get(self, textbook_id):
        t = Textbook.query.filter_by(id=textbook_id).one_or_none()
        if t:
            return textbook_schema.dump(t)
        else:
            return {"message": f"No textbook found with id {textbook_id}"}, 404


class TextbookSearchApi(Resource):
    @jwt_required()
    def get(self):
        query_str = request.args.get("q")

        if query_str is None:
            return {'message': "Missing query argument (q)"}, 400

        textbooks = Textbook.search(query_str)[0]

        result = textbook_schema.dump(textbooks.all(), many=True)
        return {'textbooks': result}


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
                                 request.get_json(), add_to=[t.sections,
                                                             current_user.authored_sources])


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

        return create_and_commit(ClassMeeting, class_meeting_schema,
                                 request.get_json(),
                                 add_to=[current_user.authored_sources])


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

        email_str = request.args.get("email")

        if email_str is None:
            users = User.query.all()
            result = users_schema.dump(users)
            return {'users': result}
        else:
            user = User.query.filter_by(email=email_str).first()
            if not user:
                return {"message": f"No user found with email {email_str}"}, 404

            result = user_schema.dump(user)
            return {'user': result}

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


def create_and_commit(obj_type, schema, json_data, add_to=[]):
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
    for collection in add_to:
        collection.append(obj)

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


class AuthenticationSchema(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True)


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
        schema = TopicSchema(only=('id', 'text'))
        return item_collection_getter(Source, source_id, schema, 'topics',
                                      admin_or_author)

    @jwt_required()
    def post(self, source_id):
        schema = TopicSchema(only=('id', 'text'))
        return item_collection_poster(Source, source_id, schema, 'topics',
                                      Topic, admin_or_author)


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
        elif question.type == QuestionType.MULTIPLE_SELECTION:
            return ms_question_schema.dump(question)
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
        elif q.type == QuestionType.MULTIPLE_SELECTION:
            schema = ms_question_schema
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


class CourseAssessmentQuestionApi(Resource):
    @jwt_required()
    def delete(self, course_id, assessment_id, question_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        assessment = course.assessments.filter_by(id=assessment_id).first()
        if not assessment:
            return {'message': f"Assessment with id {assessment_id} not found in Course {course_id}."}, 404

        # Limit access to admins and course instructors
        if not (current_user.admin \
                or (current_user.instructor and (current_user in course.users))):
            return {'message': 'Unauthorized access.'}, 401

        q = assessment.questions.filter_by(id=question_id).one_or_none()
        if not q:
            return {'message': f"Question {question_id} not found in Assessment {assessment_id}."}, 404
        deleted_q = QuestionApi.dump_by_type(q)
        assessment.questions.remove(q)
        db.session.commit()

        return {"removed": deleted_q}


class CourseTextbookApi(Resource):
    @jwt_required()
    def delete(self, course_id, textbook_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        # Limit access to admins and course instructors
        if not (current_user.admin \
                or (current_user.instructor and (current_user in course.users))):
            return {'message': 'Unauthorized access.'}, 401

        tb = course.textbooks.filter_by(id=textbook_id).one_or_none()
        if not tb:
            return {'message': f"Textbook {textbook_id} not found in Course {course_id}."}, 404

        deleted_tb = textbook_schema.dump(tb)
        course.textbooks.remove(tb)
        db.session.commit()

        return {"removed": deleted_tb}


class CourseTopicApi(Resource):
    @jwt_required()
    def delete(self, course_id, topic_id):
        course = Course.query.filter_by(id=course_id).one_or_none()
        if not course:
            return {'message': f"Course {course_id} not found."}, 404

        # Limit access to admins and course instructors
        if not (current_user.admin \
                or (current_user.instructor and (current_user in course.users))):
            return {'message': 'Unauthorized access.'}, 401

        topic = course.topics.filter_by(id=topic_id).one_or_none()
        if not topic:
            return {'message': f"Topic {topic_id} not found in Course {course_id}."}, 404

        deleted_topic = topic_schema.dump(topic)
        course.topics.remove(topic)
        db.session.commit()

        return {"removed": deleted_topic}


class IdListSchema(Schema):
    ids = fields.List(fields.Int(), required=True)

class SingleIdSchema(Schema):
    id = fields.Int(required=True)


class RosterApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = UserSchema(only=('id','email'))
        return item_collection_getter(Course, course_id, schema, 'users',
                                      admin_or_course_instructor)

    @jwt_required()
    def post(self, course_id):
        schema = UserSchema(only=('id','email'))
        return item_collection_poster(Course, course_id, schema, 'users',
                                         User, admin_or_course_instructor)


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


class CourseAssessmentQuestionsApi(Resource):
    @jwt_required()
    def get(self, course_id, assessment_id):
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return {'message': f"Course with id {course_id} not found."}, 404
        elif not course.assessments.filter_by(id=assessment_id).first():
            return {'message': f"Assessment with id {assessment_id} not found in Course {course_id}."}, 404

        schema = QuestionSchema(only=('id','prompt'))
        return item_collection_getter(Assessment, assessment_id, schema, 'questions',
                                      admin_or_course_instructor_nested)

    @jwt_required()
    def post(self, course_id, assessment_id):
        course = Course.query.filter_by(id=course_id).first()
        if not course:
            return {'message': f"Course with id {course_id} not found."}, 404
        elif not course.assessments.filter_by(id=assessment_id).first():
            return {'message': f"Assessment with id {assessment_id} not found in Course {course_id}."}, 404

        schema = QuestionSchema(only=('id','prompt'))
        return item_collection_poster(Assessment, assessment_id, schema, 'questions',
                                         Question, admin_or_course_instructor_nested)

class TextbookSectionTopicsApi(Resource):
    @jwt_required()
    def get(self, textbook_id, section_id):
        textbook = Textbook.query.filter_by(id=textbook_id).first()
        if not textbook:
            return {'message': f"Textbook with id {textbook_id} not found."}, 404
        elif not textbook.sections.filter_by(id=section_id).first():
            return {'message': f"TextbookSection with id {section_id} not found in Textbook {textbook_id}."}, 404

        schema = TextbookSectionSchema(only=('id','number','title'))
        return item_collection_getter(TextbookSection, section_id, schema, 'topics', admin_only)

    @jwt_required()
    def post(self, textbook_id, section_id):
        textbook = Textbook.query.filter_by(id=textbook_id).first()
        if not textbook:
            return {'message': f"Textbook with id {textbook_id} not found."}, 404
        elif not textbook.sections.filter_by(id=section_id).first():
            return {'message': f"TextbookSection with id {section_id} not found in Textbook {textbook_id}."}, 404

        schema = TextbookSectionSchema(only=('id','number','title'))
        return item_collection_poster(TextbookSection, section_id, schema,
                                      'topics', Topic, admin_only)

class CourseTextbooksApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = TextbookSchema(only=('id','title','edition','authors','sections'))
        return item_collection_getter(Course, course_id, schema, 'textbooks',
                                      admin_or_course_instructor)

    @jwt_required()
    def post(self, course_id):
        schema = TextbookSchema(only=('id','title','edition'))
        return item_collection_poster(Course, course_id, schema, 'textbooks',
                                         Textbook, admin_or_course_instructor)


class CourseTopicsApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = TopicSchema(only=('id','text'))
        return item_collection_getter(Course, course_id, schema, 'topics',
                                      admin_or_course_instructor)

    @jwt_required()
    def post(self, course_id):
        schema = TopicSchema(only=('id','text'))
        return item_collection_poster(Course, course_id, schema, 'topics',
                                         Topic, admin_or_course_instructor)


class CourseMeetingsApi(Resource):
    @jwt_required()
    def get(self, course_id):
        schema = ClassMeetingSchema(only=('id','title'))
        return item_collection_getter(Course, course_id, schema, 'meetings',
                                      admin_or_course_instructor)

    @jwt_required()
    def post(self, course_id):
        schema = ClassMeetingSchema(only=('id','title'))
        return item_collection_poster(Course, course_id, schema, 'meetings',
                                         ClassMeeting,
                                      admin_or_course_instructor)


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

        # handle request to limit to questions with specific objectives
        objective_list_str = request.args.get("objectives")
        if objective_list_str:
            try:
                objective_ids = [int(i) for i in objective_list_str.split(',')]
            except:
                return {'message': f"Invalid objectives argument: {objective_list_str}"}, 400

            questions = questions.join(Objective).filter(Objective.id.in_(objective_ids))


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
        elif json_data['type'] == 'multiple-selection':
            schema = ms_question_schema
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


class ObjectiveSearchApi(Resource):
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

        # topic_q parameter is a query string to search for topics and limit
        # objective search results to only those objectives that have one of
        # the topics.
        topic_query_str = request.args.get("topics_q")
        if topic_query_str is not None:
            print("SEARCHING FOR TOPIC QUERY:", topic_query_str)
            topics = Topic.search(topic_query_str)[0]
            objectives = objectives.join(topics)

        # if they used the 'html' argument, get the HTML version of the field
        if request.args.get("html") is not None:
            schema = LearningObjectiveSchema(many=True)
            schema.context = {"html": True}
        else:
            schema = objectives_schema

        result = schema.dump(objectives.all())
        return {'learning_objectives': result}


class ObjectivesApi(Resource):
    @jwt_required()
    def get(self):
        objectives = Objective.query

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

        # handle request to limit to specific topics
        topic_list_str = request.args.get("topics")
        if topic_list_str:
            try:
                topic_ids = [int(i) for i in topic_list_str.split(',')]
            except:
                return {'message': f"Invalid topics argument: {topic_list_str}"}, 400

            objectives = objectives.join(Topic).filter(Topic.id.in_(topic_ids))

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
                                 add_to=[current_user.authored_objectives])


class AssessmentApi(Resource):
    @jwt_required()
    def get(self, assessment_id):
        assessment = Assessment.query.filter_by(id=assessment_id).one_or_none()
        if assessment:
            # Limit access to admins and instructors of the course this
            # assessment is assigned to
            if (not current_user.admin)\
                    and (not current_user.instructor or current_user not in assessment.course.users):
                return {'message': "Unauthorized access"}, 401

            return assessment_schema.dump(assessment)
        else:
            return {'message': f"Assessment {assessment_id} not found."}, 404

    @jwt_required()
    def delete(self, assessment_id):
        assessment = Assessment.query.filter_by(id=assessment_id).one_or_none()
        if assessment:
            # Limit access to admins and instructors of the course this
            # assessment is assigned to
            if (not current_user.admin)\
                    and (not current_user.instructor or current_user not in assessment.course.users):
                return {'message': "Unauthorized access"}, 401

            db.session.delete(assessment)
            db.session.commit()
            return {"deleted": assessment_schema.dump(assessment)}

        else:
            return {'message': f"Assessment {assessment_id} not found."}, 404


