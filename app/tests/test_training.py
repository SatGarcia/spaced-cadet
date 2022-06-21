import unittest
from unittest.mock import patch, MagicMock, call
import warnings
from urllib.parse import urlparse
from datetime import date, datetime, timedelta
from flask import url_for
from flask_login import FlaskLoginClient

from app import create_app, db
from app.db_models import (
    User, Course, ShortAnswerQuestion, Assessment, Attempt, TextAttempt
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
        self.client = self.app.test_client()
        db.create_all()

        self.course = Course(name="test-course", title="Test Course",
                             description="A test course",
                             start_date=(date.today()-timedelta(days=1)),
                             end_date=(date.today()+timedelta(days=1)))

        db.session.add(self.course)

        a = Assessment(title="Test assessment")
        self.course.assessments.append(a)

        self.q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        a.questions.append(self.q1)

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
            self.assertEqual(Attempt.query.count(), 1)
            self.assertEqual(TextAttempt.query.count(), 1)

            attempt = TextAttempt.query.first()
            self.assertEqual(attempt.question_id, 1)
            self.assertEqual(attempt.user_id, user.id)
            self.assertEqual(attempt.response, "My response")

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
        attempt = TextAttempt(response="Whatever", question=self.q1,
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
        attempt = TextAttempt(response="Whatever", question=self.q1,
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
        attempt = TextAttempt(response="Whatever", question=self.q1,
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
