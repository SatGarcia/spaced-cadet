from flask import Blueprint, render_template
from  sqlalchemy.sql.expression import func

user_views = Blueprint('user_views', __name__)

@user_views.route('/')
def root():
    return render_template("home.html")

@user_views.route('/test')
def test():
    first_q = Question.query.order_by(func.random()).first()
    return render_template("question.html",
                           page_title="Cadet Test",
                           term=first_q.prompt,
                           definition=first_q.answer)


from app.db_models import Question

"""
class NewAssignmentForm(FlaskForm):
    assignment_num = IntegerField('Assignment Number', validators=[NumberRange(min=0)])
    base_assignment_id = SelectField('Base Assignment', coerce=int)
    due_date = DateField('Due Date', widget=DateInput(), validators=[DataRequired()])
    due_time = TimeField('Due Time', widget=TimeInput(), validators=[DataRequired()])
    section_id = IntegerField('Section ID',
                                widget=HiddenInput(), 
                                validators=[NumberRange(min=0)])
    submit = SubmitField("Create Assignment")

    def validate_assignment_num(form, field):
        with current_app.Session() as session:
            num_matches = (
                    session.query(db_models.Assignment)
                        .filter(db_models.Assignment.section_id == form.section_id.data)
                        .filter(db_models.Assignment.num == form.assignment_num.data)
                        .count()
            )

            if num_matches != 0:
                raise ValidationError("Number already in use")

class RosterUploadForm(FlaskForm):
    roster_file = FileField('Class Roster', 
                            validators=[FileRequired(),
                                        FileAllowed(['csv'], 'Roster file must be CSV format')])
    add_drop = BooleanField('Enable Add/Drop')
    submit = SubmitField('Upload Roster')
"""
