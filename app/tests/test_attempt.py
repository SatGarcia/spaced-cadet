import unittest
from app import create_app, db
from app.db_models import ShortAnswerQuestion, TextAttempt, Assessment, User
from datetime import date, timedelta, datetime

class AttemptModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.a = Assessment(title="Test assessment")
        self.q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")

        db.session.add(self.a)
        db.session.commit()
        self.a.questions.append(self.q1)

        self.u1 = User(email="test@test.com", first_name="Test", last_name="User")
        self.u1.set_password("test")

        db.session.add(self.u1)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_sm2_update_repeat_attempt(self):
        # if it is a repeated attempt for today, we do not want to update anything
        q1_attempt = TextAttempt(response="Attempt1", user=self.u1, question=self.q1, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 3, interval = 1, quality = 5)

        for i in range(6):
            q1_attempt.sm2_update(i, True) 
            db.session.add(q1_attempt)
            self.assertEqual(q1_attempt.next_attempt, date.today()) 
            self.assertEqual(q1_attempt.e_factor, 3) 
            self.assertEqual(q1_attempt.interval, 1) 
            self.assertEqual(q1_attempt.quality, i) 
 

    def test_sm2_update_question_answered_incorrectly(self):
        # if quality < 3 then the interval should be set to 1 and the next attempt will be tomorrow 
        q1_attempt = TextAttempt(response="Attempt1", user=self.u1, question=self.q1, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 4, interval = 2, quality = 4) 

        for i in range(3):
            q1_attempt.sm2_update(i) 
            db.session.add(q1_attempt)
            self.assertEqual(q1_attempt.next_attempt,date.today() + timedelta(days=1))
            self.assertEqual(q1_attempt.e_factor, 4) 
            self.assertEqual(q1_attempt.interval, 1) 
            self.assertEqual(q1_attempt.quality, i) 

    def test_sm2_update_correct_answer_with_interval1(self):
        # if quality >= 3 then the interval should be set to 6 if the interval was 1 
        q1_attempt = TextAttempt(response="Attempt1", user=self.u1, question=self.q1, time = datetime.now(),
                                 next_attempt=date.today(),  e_factor = 2.5, interval = 1, quality = 1) 

        
        q1_attempt.sm2_update(3) 
        db.session.add(q1_attempt)
        self.assertEqual(q1_attempt.interval,6) 
        self.assertEqual(q1_attempt.e_factor,2.36)
        self.assertEqual(q1_attempt.next_attempt,date.today() + timedelta(days=6))
        self.assertEqual(q1_attempt.quality, 3) 

    def test_sm2_update_correct_answer_with_not_interval1(self):
        # if quality >= 3 then the interval should be set to the new interval *  new e_factor if the interval was not 1  
        q1_attempt = TextAttempt(response="Attempt1", user=self.u1, question=self.q1, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 2.5, interval = 3, quality = 3) 

        q1_attempt.sm2_update(3) 
        db.session.add(q1_attempt)
        self.assertEqual(q1_attempt.interval,8) 
        self.assertEqual(q1_attempt.next_attempt,date.today() + timedelta(days=8))
        self.assertEqual(q1_attempt.e_factor,2.36)
        self.assertEqual(q1_attempt.quality, 3) 

    def test_sm2_update_test_efactor_floor(self):
        # checking that the floor of the e_factor is set if it goes below 1.3 in calculations
        q1_attempt = TextAttempt(response="Attempt1", user=self.u1, question=self.q1, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 1.3, interval = 2, quality = 5) 

        q1_attempt.sm2_update(3) 
        db.session.add(q1_attempt) 
        self.assertEqual(q1_attempt.interval,3) 
        self.assertEqual(q1_attempt.e_factor,1.3)
        self.assertEqual(q1_attempt.next_attempt,date.today() + timedelta(days=3))
        self.assertEqual(q1_attempt.quality, 3) 




