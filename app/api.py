from flask import (
    Blueprint, url_for, redirect, request, abort, jsonify
)
from datetime import date, timedelta, datetime

from app import db

api = Blueprint('api', __name__)

@api.route('/courses/<int:section_num>/questions')
def course_questions(section_num):
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


from app.db_models import (
    Question, Attempt, Student, enrollments, QuestionType, AnswerOption,
    TextAttempt, SelectionAttempt, Section
)
