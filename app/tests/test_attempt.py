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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_sm2_update(self):
        # adds questions and users to this session 
        a = Assessment(title="Test assessment")
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5")


        db.session.add(a)
        db.session.commit()
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)
        a.questions.append(q4)
        a.questions.append(q5)


        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")

        db.session.add(u1)
        db.session.commit()


        # if it is a repeated attempt for today, we do not want to update anything
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2, time = datetime.now(),
                                 next_attempt=date.today())
        q2_attempt2 = TextAttempt(response="Attempt2b", user=u1, question=q2, time = datetime.now(),
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q2_attempt2])
        
        q2_attempt2.sm2_update(q2_attempt2.quality, True) # is there a seperate function somewhere checking if it a repeat attempt?
        #by checking the next attempt, we assure the attempt did not change because that updates every time if it is not a repeat_attempt
        self.assertEqual(q2_attempt.next_attempt, q2_attempt2.next_attempt) 


        # if quality < 3 then the interval should be set to 1 and the next attempt will be tomorrow 
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3, time = datetime.now(),
                                 next_attempt=date.today(), interval = 2, quality = 2) 

        q3_attempt.sm2_update(q3_attempt.quality) 
        db.session.add(q3_attempt)
        self.assertEqual(q3_attempt.next_attempt,date.today() + timedelta(days=1))
        self.assertEqual(q3_attempt.interval,1)

        # if quality >= 3 then the interval should be set to 6 if the interval was 1 
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 2.5, interval = 1, quality = 3) 

        q4_attempt.sm2_update(q4_attempt.quality) 
        db.session.add(q4_attempt) 
        self.assertEqual(q4_attempt.interval,6) # by checking the interval we are also checking the next_attempt
        self.assertEqual(q4_attempt.e_factor,2.36)

        # if quality >= 3 then the interval should be set to the new interval *  new e_factor if the interval was not 1  
        q5_attempt = TextAttempt(response="Attempt5", user=u1, question=q5, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 2.5, interval = 3, quality = 3) 

        q5_attempt.sm2_update(q5_attempt.quality) 
        db.session.add(q5_attempt) 
        self.assertEqual(q5_attempt.interval,8) # by checking the interval we are also checking the next_attempt
        self.assertEqual(q5_attempt.e_factor,2.36)

        # checking that the floor of the e_factor is set if it goes below 1.3 in calculations
        q1_attempt = TextAttempt(response="Attempt1", user=u1, question=q1, time = datetime.now(),
                                 next_attempt=date.today(), e_factor = 1.3, interval = 2, quality = 3) 

        q1_attempt.sm2_update(q1_attempt.quality) 
        db.session.add(q1_attempt) 
        self.assertEqual(q1_attempt.interval,3) # by checking the interval we are also checking the next_attempt
        self.assertEqual(q1_attempt.e_factor,1.3)




