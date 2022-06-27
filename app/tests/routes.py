from flask import jsonify, request
from marshmallow import (
    ValidationError, Schema, fields
)
from faker import Faker
from random import shuffle, randint
from datetime import date, datetime, timedelta

from app import db
from app.tests import tests
from app.db_models import (
    User, UserSchema, Course, CourseSchema, Assessment, Objective,
    LearningObjectiveSchema, Question,
    ShortAnswerQuestion, ShortAnswerQuestionSchema,
    AutoCheckQuestion, AutoCheckQuestionSchema,
    MultipleChoiceQuestion, MultipleChoiceQuestionSchema, AnswerOption,
    MultipleSelectionQuestion, MultipleSelectionQuestionSchema,
    CodeJumbleQuestion, CodeJumbleQuestionSchema, JumbleBlock, Topic,
    TopicSchema, Textbook, TextbookSchema, TextbookSection
)

Faker.seed(0)
fake = Faker()

class InvalidIDError(Exception):
    """ Error to indicate that a given ID is invalid. """
    pass

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


@tests.route('/seed/topics', methods=['POST'])
def seed_topics():
    AmountSchema = Schema.from_dict({
        'amount': fields.Int(required=True)
    })
    try:
        data = load_data(AmountSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    new_topics = []
    for _ in range(data['amount']):
        new_topics.append(Topic(text=fake.word(part_of_speech="noun")))

    db.session.add_all(new_topics)
    db.session.commit()

    return jsonify(TopicSchema().dump(new_topics, many=True))


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


@tests.route('/seed/textbook', methods=['POST'])
def seed_textbook():
    AmountSchema = Schema.from_dict({
        'author_id': fields.Int(required=True),
        'num_sections': fields.Int(required=True)
    })
    try:
        data = load_data(AmountSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    author_id = data['author_id']
    author = User.query.filter_by(id=author_id).first()

    if not author:
        return jsonify(message=f"No user found with ID {author_id}"), 422

    new_tb = Textbook(title=fake.sentence(nb_words=5,
                                          variable_nb_words=False),
                      edition=randint(1,5),
                      authors=f"{fake.name()} and {fake.name()}",
                      publisher=f"{fake.last_name()} Publishing",
                      year=int(fake.year()),
                      isbn=fake.isbn10(),
                      url=fake.url())

    db.session.add(new_tb)

    sections = []
    for i in range(data['num_sections']):
        tb_section = TextbookSection(title=fake.sentence(nb_words=5),
                                     author=author,
                                     number=str(i),
                                     url=fake.url())

        section_topics = []
        for _ in range(3):
            section_topics.append(Topic(text=fake.word(part_of_speech="noun")))

        tb_section.topics = section_topics
        sections.append(tb_section)

    new_tb.sections = sections
    db.session.commit()

    return jsonify(TextbookSchema().dump(new_tb))


def get_author_and_assessment(author_id, assessment_id):
    author = User.query.filter_by(id=author_id).first()
    if not author:
        raise InvalidIDError(f"No user found with ID {author_id}")

    if assessment_id is not None:
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if not assessment:
            raise InvalidIDError(f"No assessment with ID {assessment_id}")
    else:
        assessment = None

    return author, assessment

def random_short_answer(author, is_public, is_enabled):
    answer = fake.sentence(nb_words=3)
    prompt = f"Type in something similar to the following: **{answer}**"
    return ShortAnswerQuestion(prompt=prompt, answer=answer, author=author,
                               public=is_public, enabled=is_enabled)

def random_auto_check(author, is_public, is_enabled):
    answer = str(randint(1,100))
    prompt = f"What is {answer}+0?"
    return AutoCheckQuestion(prompt=prompt, answer=answer, regex=False,
                             author=author, public=is_public,
                             enabled=is_enabled)

def random_multiple_choice(author, is_public, is_enabled):
    options = []
    options.append(AnswerOption(text="Good answer", correct=True))

    for i in range(1,4):
        options.append(AnswerOption(text=f"Bad answer {i}", correct=False))

    shuffle(options) # randomize the order of the options

    prompt = "MULTIPLE CHOICE: " + fake.sentence(nb_words=3)
    q = MultipleChoiceQuestion(prompt=prompt, author=author,
                               public=is_public, enabled=is_enabled)

    q.options = options
    return q

def random_multiple_selection(author, is_public, is_enabled):
    options = []

    # two correct options
    for i in range(1,3):
        options.append(AnswerOption(text=f"Good answer {i}", correct=True))

    # two incorrect options
    for i in range(1,3):
        options.append(AnswerOption(text=f"Bad answer {i}", correct=False))

    shuffle(options) # randomize the order of the options

    prompt = "MULTIPLE SELECTION: " + fake.sentence(nb_words=3)
    q = MultipleSelectionQuestion(prompt=prompt, author=author,
                               public=is_public, enabled=is_enabled)

    q.options = options
    return q

def random_code_jumble(author, is_public, is_enabled):
    blocks = []
    blocks.append(JumbleBlock(code=f"# line 0, indent 0",
                              correct_index=0, correct_indent=0))
    blocks.append(JumbleBlock(code=f"# line 1, indent 2",
                              correct_index=1, correct_indent=2))
    blocks.append(JumbleBlock(code=f"# line 2, indent 1",
                              correct_index=2, correct_indent=1))

    for i in range(1,3):
        blocks.append(JumbleBlock(code=f"# trash {i}",
                                  correct_index=-1, correct_indent=-1))

    shuffle(blocks) # randomize the order of the blocks

    prompt = "Read the code and figure it out!"
    q = CodeJumbleQuestion(prompt=prompt, language='python', author=author,
                               public=is_public, enabled=is_enabled)

    q.blocks = blocks
    return q

def create_questions(create_new_question):
    """
    Creates questions and adds them to the database.

    Params:
    create_new_question: Function that generates a new question given three
    parameters: the question author, whether the question should be public,
    and whether the question should be enabled.

    Returns:
    List of questions created
    """
    QuestionInfoSchema = Schema.from_dict({
        'author_id': fields.Int(required=True),
        'assessment_id': fields.Int(),
        'amount': fields.Int(required=True),  # the number of questions to create
    })

    try:
        data = load_data(QuestionInfoSchema())
    except LoadDataError as err:
        return err.response, err.status_code

    try:
        author, assessment = get_author_and_assessment(data.get('author_id'),
                                                       data.get('assessment_id'))
    except InvalidIDError as err:
        return jsonify(message=str(err)), 422

    new_questions = []

    for i in range(data['amount']):
        new_q = create_new_question(author, True, True)

        new_questions.append(new_q)
        db.session.add(new_q)

        if assessment:
            assessment.questions.append(new_q)

        db.session.commit()

    return new_questions

@tests.route('/seed/question/short-answer', methods=['POST'])
def seed_short_answer():
    """ Creates randomized short answer (self-graded) questions. """
    new_questions = create_questions(random_short_answer)
    return jsonify(ShortAnswerQuestionSchema().dump(new_questions, many=True))


@tests.route('/seed/question/auto-check', methods=['POST'])
def seed_auto_check():
    """ Creates randomized short answer (auto-graded) questions. """
    new_questions = create_questions(random_auto_check)
    return jsonify(AutoCheckQuestionSchema().dump(new_questions, many=True))


@tests.route('/seed/question/multiple-choice', methods=['POST'])
def seed_multiple_choice():
    """ Creates randomized multiple choice questions. """
    new_questions = create_questions(random_multiple_choice)
    return jsonify(MultipleChoiceQuestionSchema().dump(new_questions, many=True))


@tests.route('/seed/question/multiple-selection', methods=['POST'])
def seed_multiple_selection():
    """ Creates randomized multiple choice questions. """
    new_questions = create_questions(random_multiple_selection)
    return jsonify(MultipleSelectionQuestionSchema().dump(new_questions, many=True))


@tests.route('/seed/question/code-jumble', methods=['POST'])
def seed_code_jumble():
    """ Creates randomized code jumble questions. """
    new_questions = create_questions(random_code_jumble)
    return jsonify(CodeJumbleQuestionSchema().dump(new_questions, many=True))
