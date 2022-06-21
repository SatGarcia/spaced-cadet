import unittest
from unittest.mock import patch, MagicMock, call
import warnings
from urllib.parse import urlparse
from datetime import date, datetime, timedelta
from flask import url_for
from flask_login import FlaskLoginClient

from app import create_app, db
from app.db_models import (
    User, Course, ShortAnswerQuestion, Assessment, Attempt, TextAttempt,
    AutoCheckQuestion, MultipleChoiceQuestion, AnswerOption, SelectionAttempt,
    CodeJumbleQuestion, JumbleBlock
)


class TrainingTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore', category=DeprecationWarning)
        warnings.simplefilter('ignore', category=ResourceWarning)

        self.app = create_app('config.TestConfig')
        self.app.test_client_class = FlaskLoginClient
        self.app.config['SERVER_NAME'] = 'localhost.localdomain:5000'
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.course = Course(name="test-course", title="Test Course",
                             description="A test course",
                             start_date=(date.today()-timedelta(days=1)),
                             end_date=(date.today()+timedelta(days=1)))

        db.session.add(self.course)

        a = Assessment(title="Test assessment")
        self.course.assessments.append(a)

        self.sa_question = ShortAnswerQuestion(prompt="Short Answer Question", answer="Answer 1")
        a.questions.append(self.sa_question)

        self.ac_question = AutoCheckQuestion(prompt="Auto Check Question",
                                             answer="Answer 2",
                                             regex=False)
        a.questions.append(self.ac_question)

        self.mc_question = MultipleChoiceQuestion(prompt="Multiple Choice Question")
        o1 = AnswerOption(text="Good", correct=True)
        o2 = AnswerOption(text="Not good", correct=False)
        o3 = AnswerOption(text="Also bad", correct=False)
        self.mc_question.options = [o1, o2, o3]
        a.questions.append(self.mc_question)

        self.cj_question = CodeJumbleQuestion(prompt="Code Jumble Question")
        b1 = JumbleBlock(code="line 1, indent 2",
                         correct_index=1, correct_indent=2)
        b2 = JumbleBlock(code="trash 1",
                         correct_index=-1, correct_indent=-1)
        b3 = JumbleBlock(code="line 0, indent 0",
                         correct_index=0, correct_indent=0)
        b4 = JumbleBlock(code="line 2, indent 1",
                         correct_index=2, correct_indent=1)
        b5 = JumbleBlock(code="trash 2",
                         correct_index=-1, correct_indent=-1)
        self.cj_question.blocks = [b1, b2, b3, b4, b5]
        a.questions.append(self.cj_question)

        # create two example users, one enrolled in the course, another not
        self.u1 = User(email="user1@example.com", first_name="User", last_name="Uno")
        self.u1.set_password('testing1')

        self.u2 = User(email="user2@example.com", first_name="User", last_name="Uno")
        self.u2.set_password('testing2')

        self.course.users.append(self.u1)

        db.session.add_all([self.u1, self.u2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def check_text_attempt(self, question_id, user_id, response):
            # check that there is now a single (text) attempt
            self.assertEqual(Attempt.query.count(), 1)
            self.assertEqual(TextAttempt.query.count(), 1)

            attempt = TextAttempt.query.first()
            self.assertEqual(attempt.question_id, question_id)
            self.assertEqual(attempt.user_id, user_id)
            self.assertEqual(attempt.response, response)

    def check_selection_attempt(self, question_id, user_id, response_id):
            # check that there is now a single (text) attempt
            self.assertEqual(Attempt.query.count(), 1)
            self.assertEqual(SelectionAttempt.query.count(), 1)

            attempt = SelectionAttempt.query.first()
            self.assertEqual(attempt.question_id, question_id)
            self.assertEqual(attempt.user_id, user_id)
            self.assertEqual(attempt.response.id, response_id)


    def test_valid_short_answer_question_submission(self):
        self.course.users.append(self.u2)
        db.session.commit()

        for user in [self.u1, self.u2]:
            client = self.app.test_client(user=user)
            response = client.post(url_for('user_views.test_short_answer',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": "1",
                                            "response": "My response",
                                            "submit": "y"
                                        })

            # check that user was sent to the self verify page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Was your answer correct?", response.data)

            # check that there is now a single (text) attempt
            self.check_text_attempt(self.sa_question.id, user.id, "My response")

            # clear out attempts for next user test
            Attempt.query.delete()
            TextAttempt.query.delete()


    def test_correct_auto_check_question_submission(self):
        self.course.users.append(self.u2)
        db.session.commit()

        for user in [self.u1, self.u2]:
            client = self.app.test_client(user=user)
            response = client.post(url_for('user_views.test_auto_check',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": str(self.ac_question.id),
                                            "response": "Answer 2",
                                            "submit": "y"
                                        })

            # check that user was sent to the difficulty page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Rate Your Performance", response.data)

            # check that there is now a single (text) attempt
            self.check_text_attempt(self.ac_question.id, user.id, "Answer 2")

            attempt = TextAttempt.query.first()
            self.assertTrue(attempt.correct)

            # clear out attempts for next user test
            Attempt.query.delete()
            TextAttempt.query.delete()

    # TODO: check for correct auto check submission when caSiNG is different

    def test_incorrect_auto_check_question_submission(self):
        client = self.app.test_client(user=self.u1)
        response = client.post(url_for('user_views.test_auto_check',
                                            course_name="test-course",
                                            mission_id=1),
                                    data={
                                        "question_id": str(self.ac_question.id),
                                        "response": "Wrong Answer",
                                        "submit": "y"
                                    })

        # check that user was sent to the difficulty page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Incorrect Answer", response.data)

        attempt = TextAttempt.query.first()
        self.assertFalse(attempt.correct)


    def test_correct_multiple_choice_question_submission(self):
        self.course.users.append(self.u2)
        db.session.commit()

        for user in [self.u1, self.u2]:
            client = self.app.test_client(user=user)
            response = client.post(url_for('user_views.test_multiple_choice',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": str(self.mc_question.id),
                                            "response": "1",
                                            "submit": "y"
                                        })

            # check that user was sent to the difficulty page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Rate Your Performance", response.data)

            # check that there is now a single (text) attempt
            self.check_selection_attempt(self.mc_question.id, user.id, 1)

            attempt = SelectionAttempt.query.first()
            self.assertTrue(attempt.correct)

            # clear out attempts for next user test
            Attempt.query.delete()
            SelectionAttempt.query.delete()


    def test_incorrect_multiple_choice_question_submission(self):
        for response_id in [2, 3]:
            client = self.app.test_client(user=self.u1)
            response = client.post(url_for('user_views.test_multiple_choice',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": str(self.mc_question.id),
                                            "response": str(response_id),
                                            "submit": "y"
                                        })

            # check that user was sent to the difficulty page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Incorrect Answer", response.data)

            attempt = SelectionAttempt.query.first()
            self.assertFalse(attempt.correct)
            self.assertEqual(attempt.quality, 2)

            # clear out attempts for next user test
            Attempt.query.delete()
            SelectionAttempt.query.delete()


    def test_idk_multiple_choice_question_submission(self):
        client = self.app.test_client(user=self.u1)
        response = client.post(url_for('user_views.test_multiple_choice',
                                            course_name="test-course",
                                            mission_id=1),
                                    data={
                                        "question_id": str(self.mc_question.id),
                                        "response": "-1",
                                        "submit": "y"
                                    })

        # check that user was sent to the difficulty page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Incorrect Answer", response.data)

        attempt = SelectionAttempt.query.first()
        self.assertFalse(attempt.correct)
        self.assertEqual(attempt.quality, 1)


    def test_correct_code_jumble_question_submission(self):
        self.course.users.append(self.u2)
        db.session.commit()

        for user in [self.u1, self.u2]:
            client = self.app.test_client(user=user)
            response = client.post(url_for('user_views.test_code_jumble',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": str(self.cj_question.id),
                                            "response": "[(3,0), (1,2), (4,1)]",
                                            "submit": "y"
                                        })

            # check that user was sent to the difficulty page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Rate Your Performance", response.data)

            # check that there is now a single (text) attempt
            self.check_text_attempt(self.cj_question.id, user.id, "[(3,0), (1,2), (4,1)]")

            attempt = TextAttempt.query.first()
            self.assertTrue(attempt.correct)

            # clear out attempts for next user test
            Attempt.query.delete()
            TextAttempt.query.delete()


    def test_incorrect_code_jumble_question_submission(self):
        for response_str in ["[(1,2), (3,0), (4,1)]", # wrong ordering
                             "[(3,0), (1,2), (4,0)]", # wrong indent
                             "[(3,0), (1,2)]", # missing block
                             "[(3,0), (1,2), (4,1), (2,0)]"]: # extraneous block
            client = self.app.test_client(user=self.u1)
            response = client.post(url_for('user_views.test_code_jumble',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": str(self.cj_question.id),
                                            "response": response_str,
                                            "submit": "y"
                                        })

            # check that user was sent to the difficulty page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Incorrect Answer", response.data)

            # check that there is now a single (text) attempt
            self.check_text_attempt(self.cj_question.id, self.u1.id,
                                    response_str)

            attempt = TextAttempt.query.first()
            self.assertFalse(attempt.correct)

            # clear out attempts for next user test
            Attempt.query.delete()
            TextAttempt.query.delete()


    def test_unauthorized_user(self):
        client = self.app.test_client(user=self.u2)
        response = client.post(url_for('user_views.test_short_answer',
                                            course_name="test-course",
                                            mission_id=1),
                                    data={
                                        "question_id": "1",
                                        "response": "My response",
                                        "submit": "y"
                                    })

        self.assertEqual(response.status_code, 401)

    def test_idk_short_answer_question_submission(self):
        client = self.app.test_client(user=self.u1)
        response = client.post(url_for('user_views.test_short_answer',
                                            course_name="test-course",
                                            mission_id=1),
                                    data={
                                        "question_id": "1",
                                        "response": "",
                                        "no_answer": "y"
                                    })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Incorrect Answer", response.data)

        # check that there is now a single (text) attempt
        self.assertEqual(Attempt.query.count(), 1)
        self.assertEqual(TextAttempt.query.count(), 1)

        # check that attempt is labeled as incorrect and has quality of 1
        attempt = TextAttempt.query.first()
        self.assertFalse(attempt.correct)
        self.assertEqual(attempt.quality, 1)


    def test_missing_short_answer_response(self):
        # System should reject blank strings as well as strings that have only
        # whitespace characters
        for response in ["", " ", "\n"]:
            client = self.app.test_client(user=self.u1)
            response = client.post(url_for('user_views.test_short_answer',
                                                course_name="test-course",
                                                mission_id=1),
                                        data={
                                            "question_id": "1",
                                            "response": response,
                                            "submit": "y"
                                        })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Enter an answer or click", response.data)

            # make sure no attempt was created
            self.assertEqual(Attempt.query.count(), 0)

    def test_self_review_correct(self):
        """ Tests user selecting that they correctly got the question correct. """
        # create the existing attempt that will be updated
        attempt = TextAttempt(response="Whatever", question=self.sa_question,
                              user=self.u1,
                              time=datetime(2022, 1, 2))
        db.session.add(attempt)
        db.session.commit()

        client = self.app.test_client(user=self.u1)
        response = client.post(url_for('user_views.self_review',
                                            course_name="test-course",
                                            mission_id=1),
                                        data={
                                            "attempt_id": attempt.id,
                                            "yes": "y"
                                        })

        # check that user was sent to the difficulty rating page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rate Your Performance", response.data)

        # check that attempt's correctness was set but that all other fields
        # remain unchanged
        updated_attempt = Attempt.query.filter_by(id=attempt.id).first()
        self.assertIsNotNone(updated_attempt)
        self.assertTrue(updated_attempt.correct)
        self.assertEqual(updated_attempt.next_attempt, date.today())
        self.assertEqual(updated_attempt.e_factor, 2.5)
        self.assertEqual(updated_attempt.interval, 1)
        self.assertEqual(updated_attempt.quality, -1)
        self.assertEqual(updated_attempt.time, datetime(2022, 1, 2))

    def test_self_review_incorrect(self):
        """ Tests user selecting that they incorrectly answered the question. """
        # create the existing attempt that will be updated
        attempt = TextAttempt(response="Whatever", question=self.sa_question,
                              user=self.u1,
                              time=datetime(2022, 1, 2))
        db.session.add(attempt)
        db.session.commit()

        client = self.app.test_client(user=self.u1)
        with patch('app.db_models.Attempt.sm2_update') as mock_sm2_update:
            response = client.post(url_for('user_views.self_review',
                                                course_name="test-course",
                                                mission_id=1),
                                            data={
                                                "attempt_id": attempt.id,
                                                "no": "y"
                                            })

            self.assertEqual(mock_sm2_update.call_count, 1)
            self.assertEqual(mock_sm2_update.call_args, call(2, repeat_attempt=False))

        # check that user was sent to the difficulty rating page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path,
                                  url_for('user_views.test',
                                          course_name="test-course",
                                          mission_id=1,
                                          _external=False))


        # check that attempt's correctness was set, but no other fields were
        # changed (they should only be changed through sm2_update)
        updated_attempt = Attempt.query.filter_by(id=attempt.id).first()
        self.assertIsNotNone(updated_attempt)
        self.assertFalse(updated_attempt.correct)
        self.assertEqual(updated_attempt.next_attempt, date.today())
        self.assertEqual(updated_attempt.e_factor, 2.5)
        self.assertEqual(updated_attempt.interval, 1)
        self.assertEqual(updated_attempt.quality, -1)
        self.assertEqual(updated_attempt.time, datetime(2022, 1, 2))

    def test_unauthorized_self_review(self):
        attempt = TextAttempt(response="Whatever", question=self.sa_question,
                              user=self.u1,
                              time=datetime(2022, 1, 2))
        db.session.add(attempt)
        db.session.commit()

        # test when user isn't in the course at all

        client = self.app.test_client(user=self.u2)
        response = client.post(url_for('user_views.self_review',
                                            course_name="test-course",
                                            mission_id=1),
                                        data={
                                            "attempt_id": attempt.id,
                                            "yes": "y"
                                        })

        self.assertEqual(response.status_code, 401)

        # test when user is in the course but this isn't their attempt
        self.course.users.append(self.u2)
        db.session.commit()

        response = client.post(url_for('user_views.self_review',
                                            course_name="test-course",
                                            mission_id=1),
                                        data={
                                            "attempt_id": attempt.id,
                                            "yes": "y"
                                        })

        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main(verbosity=2)
