from flask import (
    Blueprint, url_for, redirect, request, abort, jsonify
)
from datetime import date, timedelta, datetime

from app import db

api = Blueprint('api', __name__)

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
    MultipleChoiceQuestion
)
