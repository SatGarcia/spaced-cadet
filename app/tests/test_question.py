import unittest
from app import create_app, db
from app.db_models import User, ShortAnswerQuestion, TextAttempt
from datetime import date, timedelta, datetime

class QuestionModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_latest_attempt(self):
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2, q1, q2])
        db.session.commit()

        self.assertIsNone(q1.get_latest_attempt(u1))

        q1_attempt = TextAttempt(response="Attempt1", user=u1, question=q1, time = datetime.now() - timedelta(days=1))
        q1_attempt2 = TextAttempt(response="Attempt2", user=u1, question=q1, time = datetime.now())

        q1_attempt_u2 = TextAttempt(response="Attempt1", user=u2, question=q1, time = datetime.now())

        db.session.add_all([q1_attempt, q1_attempt2, q1_attempt_u2])
        db.session.commit()

        self.assertEqual(q1.get_latest_attempt(u1), q1_attempt2)
        self.assertIsNone(q2.get_latest_attempt(u1))


        

