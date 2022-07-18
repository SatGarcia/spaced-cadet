import unittest
from app import create_app, db
from app.db_models import User, Assessment, ShortAnswerQuestion, TextAttempt, Objective, Topic
from datetime import date, timedelta, datetime

class AssessmentModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.a = Assessment(title="Test assessment")

        self.u1 = User(email="test@test.com", first_name="Test", last_name="User")
        self.u1.set_password("test")
        self.u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        self.u2.set_password("test")


        self.lo1 = Objective(description="Learning Objective 1")
        self.lo2 = Objective(description="Learning Objective 2")

        self.q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1",objective = self.lo1)
        self.q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2",objective = self.lo1)
        self.q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3",objective = self.lo1)
        self.q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4",objective = self.lo1)

        #single question for lo2 to ensure differentiation
        self.q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5",objective = self.lo2)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_get_e_factor_average_with_assessment(self):
        db.session.add_all([self.a, self.u1, self.u2])
        db.session.commit()

        self.a.objectives.append(self.lo1)
        self.a.objectives.append(self.lo2)

        self.a.questions.append(self.q1)
        self.a.questions.append(self.q2)
        self.a.questions.append(self.q3)
        self.a.questions.append(self.q4)
        self.a.questions.append(self.q5)


        # before any attempts, there shouldn't be an average
        self.assertEqual(self.a.get_e_factor_average(self.u1,self.lo1,self.a).all(), 0)

        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=self.q2,
                                 next_attempt=date.today(),e_factor = 3.5)
        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=self.q3,
                                 next_attempt=date.today(), e_factor = 1.4)

        # multiple attempts for the same question, only the last one should be included in the average
        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=self.q4,
                                 next_attempt=date.today(), e_factor = 1)
        q4_attempt2 = TextAttempt(response="Attempt4b", user=self.u1, question=self.q4,
                                 next_attempt=date.today(), e_factor = 2)

        # ensure differentiation between lo1 and lo2
        q5_attempt = TextAttempt(response="Attempt5", user=self.u1, question=self.q5,
                                 next_attempt=date.today(), e_factor = 4)

        # lo1: single attempt for u2, to make sure method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=self.q1,
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q4_attempt2, q1_attempt, q5_attempt])

        self.assertEqual(self.a.get_e_factor_average(self.u1,self.lo1,self.a).all(), 2.3)

        
