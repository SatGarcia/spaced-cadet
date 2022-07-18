import unittest
from app import create_app, db
from app.db_models import Objective, Topic, User, Assessment, ShortAnswerQuestion, TextAttempt
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
        db.session.add_all([self.a, self.u1, self.u2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_unattempted_questions(self):
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)

        self.assertCountEqual(self.a.unattempted_questions(self.u1), [q1, q2, q3])

        q2_attempt = TextAttempt(response="Meow", user=self.u1, question=q2)
        q3_attempt = TextAttempt(response="Arf", user=self.u2, question=q3)
        db.session.add_all([q2_attempt, q3_attempt])
        db.session.commit()

        self.assertCountEqual(self.a.unattempted_questions(self.u1), [q1, q3])
        self.assertCountEqual(self.a.unattempted_questions(self.u2), [q1, q2])


    def test_due_questions(self):
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)
        self.a.questions.append(q4)

        # before any attempts, there shouldn't be any due
        self.assertEqual(self.a.due_questions(self.u1).all(), [])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1)))
        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1)))

        # single attempt for u2, with next attempt of today to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=q1,
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(self.a.due_questions(self.u1).all(), [q2])

        # test that we successfully get multiple questions by changing one of
        # the attempts to be due today
        q3_attempt.next_attempt = date.today()
        db.session.commit()

        self.assertCountEqual(self.a.due_questions(self.u1).all(), [q2, q3])


    
    def test_overdue_questions(self):

        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)

        # before any attempts, there shouldn't be any overdue
        self.assertEqual(self.a.overdue_questions(self.u1).all(), [])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1)))
        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1)))

        # single attempt for u2, with next attempt of yesterday to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=q1,
                                 next_attempt=date.today()-timedelta(days=1))

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(self.a.overdue_questions(self.u1).all(), [q3])

        # test that we successfully get multiple questions by changing one of
        # the attempts to be due yesterday
        q2_attempt.next_attempt = date.today()-timedelta(days=1)
        db.session.commit()

        self.assertCountEqual(self.a.overdue_questions(self.u1).all(), [q2, q3])

    
    def test_waiting_questions(self):

        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)
        self.a.questions.append(q4)

        # before any attempts, there shouldn't be any waiting
        self.assertEqual(self.a.waiting_questions(self.u1).all(), [])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1)))
        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1)))

        # single attempt for u2, with next attempt of tomorrow to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=q1,
                                 next_attempt=date.today()+timedelta(days=1))

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(self.a.waiting_questions(self.u1).all(), [q4])

        # test that we successfully get multiple questions by changing one of
        # the attempts to be due tomorrow
        q2_attempt.next_attempt = date.today()+timedelta(days=1)
        db.session.commit()

        self.assertCountEqual(self.a.waiting_questions(self.u1).all(), [q2, q4])
        

    def test_fresh_questions(self):
        """ Returns all "fresh" assessment questions, where fresh is defined as needing
        to be practiced by the user for the FIRST time today. 
        """
        # adds questions to this session 
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)
        self.a.questions.append(q4)
        self.a.questions.append(q5)

        # if no questions are attempted yet, they should be fresh
        self.assertCountEqual(self.a.fresh_questions(self.u1).all(), [q1,q2,q3,q4,q5])

        #ADDING ATTEMPTS
        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=q2, time = datetime.now()-timedelta(days=1),
                                 next_attempt=date.today()) # last attempt: yesterday, next attempt: today
                                                            # due today and no attempt today so is a fresh question

        #checking with multiple attempts, one of yesterday and one of today
        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=q3, time = datetime.now()-timedelta(days=1),
                                 next_attempt=date.today()) # last attempt: yesterday, next attempt: today
        q3_attempt2 = TextAttempt(response="Attempt3b", user=self.u1, question=q3, time = datetime.now(),
                                 next_attempt=(date.today()+timedelta(days=1))) # last attempt: today, next attempt: tomorrow
                                                                                # (already practiced today so not a fresh question)

        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=q4, time = datetime.now()-timedelta(days=1),
                                 next_attempt=(date.today()+timedelta(days=1))) # last attempt: yesterday, next attempt: tomorrow 
                                                                                # (doesn't need to be practiced by user today so not a fresh question)

        q5_attempt = TextAttempt(response="Attempt5", user=self.u1, question=q5, time = datetime.now()-timedelta(days=2),
                                 next_attempt=(date.today()-timedelta(days=1))) # last attempt: 2 days ago, next attempt: yesterday
                                                                                # (question is overdue so it is a fresh question) 


        # single attempt for u2, with next attempt of today to make sure method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=q1, time = datetime.now()-timedelta(days=1),
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q3_attempt, q3_attempt2, q4_attempt,q5_attempt,q1_attempt])

        self.assertCountEqual(self.a.fresh_questions(self.u1).all(), [q1,q2,q5]) # unattempted questions are still fresh
        self.assertCountEqual(self.a.fresh_questions(self.u2).all(), [q1,q2,q3,q4,q5])
        


    def test_repeat_questions(self):
        """ Returns all assessment questions that the user has already attempted today
        but that haven't gotten a quality score of 4 or above."""

        # adds questions to this session 
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5")
        q6 = ShortAnswerQuestion(prompt="Question 6", answer="Answer 6")
        q7 = ShortAnswerQuestion(prompt="Question 7", answer="Answer 7")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)
        self.a.questions.append(q4)
        self.a.questions.append(q5)
        self.a.questions.append(q6)
        self.a.questions.append(q7)

        # if no questions are attempted yet today, they should not be repreated
        self.assertEqual(self.a.repeat_questions(self.u1).all(), [])

        # attempts of yesterday and today: q2 attempts test improving quality the next day(not a repeat question), 
        # q3 attempts test stagnant quality the next day (still less than 4 so not a repeat question), q4 attempts test
        # decreasing quality the next day (less than 4 so is a repreat question)
        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=q2,
                                 time=(datetime.now()-timedelta(days=1)), quality = 3) # last attempt: yesterday, quality: 3
        q2_attempt2 = TextAttempt(response="Attempt2b", user=self.u1, question=q2,
                                 time=datetime.now(), quality = 4) # last attempt: today, quality: 4

        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=q3,
                                 time=(datetime.now()-timedelta(days=1)), quality = 3) # last attempt: yesterday, quality: 3
        q3_attempt2 = TextAttempt(response="Attempt3b", user=self.u1, question=q3,
                                 time=datetime.now(), quality = 3) # last attempt: today, quality: 3

        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=q4,
                                 time=(datetime.now()-timedelta(days=1)), quality = 5) # last attempt: yesterday, quality: 5
        q4_attempt2 = TextAttempt(response="Attempt4b", user=self.u1, question=q4,
                                 time=datetime.now(), quality = 1) # last attempt: today, quality: 1

        # multiple attempts today: q5 attempts test improving quality the same day but still not greater than 
        # 4 on the next attempt(repeat question), q6 attempts test decreasing quality the same day (less than 
        # 4 so is a repeat question), q7 attempts test increasing quality the same day (4 or greater so not a repreat question)
        q5_attempt = TextAttempt(response="Attempt5", user=self.u1, question=q5,
                                 time=(datetime.now()), quality = 2)  # last attempt: today, quality: 2
        q5_attempt2 = TextAttempt(response="Attempt5b", user=self.u1, question=q5,
                                 time=datetime.now(), quality = 3) # last attempt: today, quality: 3

        q6_attempt = TextAttempt(response="Attempt6", user=self.u1, question=q6,
                                 time=(datetime.now()), quality = 5)  # last attempt: today, quality: 5
        q6_attempt2 = TextAttempt(response="Attempt6b", user=self.u1, question=q6,
                                 time=datetime.now(), quality = 3) # last attempt: today, quality: 3

        q7_attempt = TextAttempt(response="Attempt7", user=self.u1, question=q7,
                                 time=(datetime.now()), quality = 3)  # last attempt: today, quality: 3
        q7_attempt2 = TextAttempt(response="Attempt7b", user=self.u1, question=q7,
                                 time=datetime.now(), quality = 4) # last attempt: today, quality: 4

        # single attempt for u2, with next attempt of today to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=q1,
                                 time=(date.today()), quality = 2)

        db.session.add_all([q2_attempt, q2_attempt2, q3_attempt, q3_attempt2, q4_attempt, q4_attempt2, 
                           q5_attempt, q5_attempt2, q6_attempt, q6_attempt2, q7_attempt, q7_attempt2, q1_attempt])

        self.assertCountEqual(self.a.repeat_questions(self.u1).all(), [q3, q4, q5])
        
    def test_breakdown_today(self):

        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5")
        q6 = ShortAnswerQuestion(prompt="Question 6", answer="Answer 6")

        self.a.questions.append(q1)
        self.a.questions.append(q2)
        self.a.questions.append(q3)
        self.a.questions.append(q4)
        self.a.questions.append(q5)
        self.a.questions.append(q6)

        db.session.commit()

        # if no questions are attempted yet, there is nothing to breakdown
        (incorrect, easy, med, hard) = self.a.breakdown_today(self.u1)
        test1 = (incorrect.all(), easy.all(), med.all(), hard.all())
        self.assertTupleEqual(test1, ([], [], [], []))


        # last attempt: yesterday
        q2_attempt = TextAttempt(response="Attempt2", user=self.u1, question=q2, time = datetime.now()-timedelta(days=1), correct=False, quality = 1)

        # checking with multiple attempts
        # first attempt today: true, quality=3
        q3_attempt = TextAttempt(response="Attempt3", user=self.u1, question=q3, time = datetime.now(), correct=True, quality = 3)
        q3_attempt2 = TextAttempt(response="Attempt3b", user=self.u1, question=q3, time = datetime.now(), correct=False, quality = 1) 
                                                                        
        # first attempt today: false, quality=1
        q4_attempt = TextAttempt(response="Attempt4", user=self.u1, question=q4, time = datetime.now(), correct = False, quality = 1)
        q4_attempt2 = TextAttempt(response="Attempt4b", user=self.u1, question=q4, time = datetime.now(), correct=True, quality = 3)

        # true, quality=4                                                                
        q5_attempt = TextAttempt(response="Attempt5", user=self.u1, question=q5, time = datetime.now(), correct=True, quality = 4)

        # true, quality=5                                                                
        q6_attempt = TextAttempt(response="Attempt6", user=self.u1, question=q6, time = datetime.now(), correct=True, quality = 5)                                                                  

        # single attempt for u2, with next attempt of today to make sure method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=self.u2, question=q1, time = datetime.now(), correct=False)

        db.session.add_all([q2_attempt, q3_attempt, q3_attempt2, q4_attempt, q4_attempt2, q5_attempt, q1_attempt, q6_attempt])
        db.session.commit()
        
        # if no questions are attempted yet, there is nothing to breakdown
        (incorrect, easy, med, hard) = self.a.breakdown_today(self.u1)
        test2 = (incorrect.all(), easy.all(), med.all(), hard.all())
        self.assertTupleEqual(test2, ([q4], [q6], [q5], [q3]))
        


if __name__ == '__main__':
    unittest.main(verbosity=2)
