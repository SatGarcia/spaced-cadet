import unittest
from app import create_app, db
from app.db_models import User, Assessment, ShortAnswerQuestion, TextAttempt, Objective
from datetime import date, timedelta, datetime

class AssessmentModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_unattempted_questions(self):
        a = Assessment(title="Test assessment")
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")

        db.session.add(a)
        db.session.commit()
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        self.assertCountEqual(a.unattempted_questions(u1), [q1, q2, q3])

        q2_attempt = TextAttempt(response="Meow", user=u1, question=q2)
        q3_attempt = TextAttempt(response="Arf", user=u2, question=q3)
        db.session.add_all([q2_attempt, q3_attempt])
        db.session.commit()

        self.assertCountEqual(a.unattempted_questions(u1), [q1, q3])
        self.assertCountEqual(a.unattempted_questions(u2), [q1, q2])


    def test_due_questions(self):
        a = Assessment(title="Test assessment")
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")

        db.session.add(a)
        db.session.commit()
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)
        a.questions.append(q4)

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        # before any attempts, there shouldn't be any due
        self.assertEqual(a.due_questions(u1).all(), [])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1)))
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1)))

        # single attempt for u2, with next attempt of today to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(a.due_questions(u1).all(), [q2])

        # test that we successfully get multiple questions by changing one of
        # the attempts to be due today
        q3_attempt.next_attempt = date.today()
        db.session.commit()

        self.assertCountEqual(a.due_questions(u1).all(), [q2, q3])


    
    def test_overdue_questions(self):
        a = Assessment(title="Test assessment")
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")

        db.session.add(a)
        db.session.commit()
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        # before any attempts, there shouldn't be any overdue
        self.assertEqual(a.overdue_questions(u1).all(), [])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1)))
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1)))

        # single attempt for u2, with next attempt of yesterday to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 next_attempt=date.today()-timedelta(days=1))

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(a.overdue_questions(u1).all(), [q3])

        # test that we successfully get multiple questions by changing one of
        # the attempts to be due yesterday
        q2_attempt.next_attempt = date.today()-timedelta(days=1)
        db.session.commit()

        self.assertCountEqual(a.overdue_questions(u1).all(), [q2, q3])

    
    def test_waiting_questions(self):
        a = Assessment(title="Test assessment")
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")

        db.session.add(a)
        db.session.commit()
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)
        a.questions.append(q4)

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        # before any attempts, there shouldn't be any waiting
        self.assertEqual(a.waiting_questions(u1).all(), [])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1)))
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1)))

        # single attempt for u2, with next attempt of tomorrow to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 next_attempt=date.today()+timedelta(days=1))

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(a.waiting_questions(u1).all(), [q4])

        # test that we successfully get multiple questions by changing one of
        # the attempts to be due tomorrow
        q2_attempt.next_attempt = date.today()+timedelta(days=1)
        db.session.commit()

        self.assertCountEqual(a.waiting_questions(u1).all(), [q2, q4])
        

    def test_fresh_questions(self):
        """ Returns all "fresh" assessment questions, where fresh is defined as needing
        to be practiced by the user for the FIRST time today. 
        """
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
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        # if no questions are attempted yet, they should be fresh
        self.assertCountEqual(a.fresh_questions(u1).all(), [q1,q2,q3,q4,q5])


        #ADDING ATTEMPTS
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2, time = datetime.now()-timedelta(days=1),
                                 next_attempt=date.today()) # last attempt: yesterday, next attempt: today
                                                            # due today and no attempt today so is a fresh question

        #checking with multiple attempts, one of yesterday and one of today
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3, time = datetime.now()-timedelta(days=1),
                                 next_attempt=date.today()) # last attempt: yesterday, next attempt: today
        q3_attempt2 = TextAttempt(response="Attempt3b", user=u1, question=q3, time = datetime.now(),
                                 next_attempt=(date.today()+timedelta(days=1))) # last attempt: today, next attempt: tomorrow
                                                                                # (already practiced today so not a fresh question)

        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4, time = datetime.now()-timedelta(days=1),
                                 next_attempt=(date.today()+timedelta(days=1))) # last attempt: yesterday, next attempt: tomorrow 
                                                                                # (doesn't need to be practiced by user today so not a fresh question)

        q5_attempt = TextAttempt(response="Attempt5", user=u1, question=q5, time = datetime.now()-timedelta(days=2),
                                 next_attempt=(date.today()-timedelta(days=1))) # last attempt: 2 days ago, next attempt: yesterday
                                                                                # (question is overdue so it is a fresh question) 


        # single attempt for u2, with next attempt of today to make sure method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1, time = datetime.now()-timedelta(days=1),
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q3_attempt, q3_attempt2, q4_attempt,q5_attempt,q1_attempt])

        self.assertCountEqual(a.fresh_questions(u1).all(), [q1,q2,q5]) # unattempted questions are still fresh
        self.assertCountEqual(a.fresh_questions(u2).all(), [q1,q2,q3,q4,q5])
        


    def test_repeat_questions(self):
        """ Returns all assessment questions that the user has already attempted today
        but that haven't gotten a quality score of 4 or above."""
        # adds questions and users to this session 
        a = Assessment(title="Test assessment")
        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5")
        q6 = ShortAnswerQuestion(prompt="Question 6", answer="Answer 6")
        q7 = ShortAnswerQuestion(prompt="Question 7", answer="Answer 7")

        db.session.add(a)
        db.session.commit()
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)
        a.questions.append(q4)
        a.questions.append(q5)
        a.questions.append(q6)
        a.questions.append(q7)

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        # if no questions are attempted yet today, they should not be repreated
        self.assertEqual(a.repeat_questions(u1).all(), [])

        # attempts of yesterday and today: q2 attempts test improving quality the next day(not a repeat question), 
        # q3 attempts test stagnant quality the next day (still less than 4 so not a repeat question), q4 attempts test
        # decreasing quality the next day (less than 4 so is a repreat question)
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 time=(datetime.now()-timedelta(days=1)), quality = 3) # last attempt: yesterday, quality: 3
        q2_attempt2 = TextAttempt(response="Attempt2b", user=u1, question=q2,
                                 time=datetime.now(), quality = 4) # last attempt: today, quality: 4

        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 time=(datetime.now()-timedelta(days=1)), quality = 3) # last attempt: yesterday, quality: 3
        q3_attempt2 = TextAttempt(response="Attempt3b", user=u1, question=q3,
                                 time=datetime.now(), quality = 3) # last attempt: today, quality: 3

        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 time=(datetime.now()-timedelta(days=1)), quality = 5) # last attempt: yesterday, quality: 5
        q4_attempt2 = TextAttempt(response="Attempt4b", user=u1, question=q4,
                                 time=datetime.now(), quality = 1) # last attempt: today, quality: 1

        # multiple attempts today: q5 attempts test improving quality the same day but still not greater than 
        # 4 on the next attempt(repeat question), q6 attempts test decreasing quality the same day (less than 
        # 4 so is a repeat question), q7 attempts test increasing quality the same day (4 or greater so not a repreat question)
        q5_attempt = TextAttempt(response="Attempt5", user=u1, question=q5,
                                 time=(datetime.now()), quality = 2)  # last attempt: today, quality: 2
        q5_attempt2 = TextAttempt(response="Attempt5b", user=u1, question=q5,
                                 time=datetime.now(), quality = 3) # last attempt: today, quality: 3

        q6_attempt = TextAttempt(response="Attempt6", user=u1, question=q6,
                                 time=(datetime.now()), quality = 5)  # last attempt: today, quality: 5
        q6_attempt2 = TextAttempt(response="Attempt6b", user=u1, question=q6,
                                 time=datetime.now(), quality = 3) # last attempt: today, quality: 3

        q7_attempt = TextAttempt(response="Attempt7", user=u1, question=q7,
                                 time=(datetime.now()), quality = 3)  # last attempt: today, quality: 3
        q7_attempt2 = TextAttempt(response="Attempt7b", user=u1, question=q7,
                                 time=datetime.now(), quality = 4) # last attempt: today, quality: 4

        # single attempt for u2, with next attempt of today to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 time=(date.today()), quality = 2)

        db.session.add_all([q2_attempt, q2_attempt2, q3_attempt, q3_attempt2, q4_attempt, q4_attempt2, 
                           q5_attempt, q5_attempt2, q6_attempt, q6_attempt2, q7_attempt, q7_attempt2, q1_attempt])

        self.assertCountEqual(a.repeat_questions(u1).all(), [q3, q4, q5])
        
    def test_objectives_to_review(self):
        " Returns a list of the three learning objectives with the lowest average e_factor"
        a = Assessment(title="Test assessment")
        lo1 = Objective(description="Learning Objective 1")
        lo2 = Objective(description="Learning Objective 2")
        lo3 = Objective(description="Learning Objective 3")
        lo4 = Objective(description="Learning Objective 4")

        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5")
        q6 = ShortAnswerQuestion(prompt="Question 6", answer="Answer 6")
        q7 = ShortAnswerQuestion(prompt="Question 7", answer="Answer 7")
        q8 = ShortAnswerQuestion(prompt="Question 8", answer="Answer 8")

        db.session.add(a)
        db.session.commit()
        a.objectives.append(lo1)
        a.objectives.append(lo2)
        a.objectives.append(lo3)
        a.objectives.append(lo4)
        a.questions.append(q1)
        a.questions.append(q2)
        a.questions.append(q3)
        a.questions.append(q4)
        a.questions.append(q5)
        a.questions.append(q6)
        a.questions.append(q7)
        a.questions.append(q8)
        lo1.questions.append(q2)
        lo1.questions.append(q3)
        lo1.questions.append(q1)
        lo2.questions.append(q4)
        lo2.questions.append(q5)
        lo3.questions.append(q6)
        lo3.questions.append(q7)
        lo4.questions.append(q8)

        u1 = User(email="test@test.com", first_name="Test", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        # before any attempts, there shouldn't be any objectives to review
        self.assertEqual(a.objectives_to_review(u1).all(), [])

        # lo1: attempts for different questions(same objective) where average e_factor is above 2.5, shouldn't be returned
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 next_attempt=date.today(),e_factor = 3)
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 next_attempt=date.today(), e_factor = 3.5)

        # lo2: attempts for different questions(same objective) where average e_factor is below 2.5, will be returned
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 next_attempt=date.today(), e_factor = 1)
        q5_attempt = TextAttempt(response="Attempt5", user=u1, question=q5,
                                 next_attempt=date.today(), e_factor = 2)

        # lo3: attempts for different questions(same objective) where average e_factor is same as 2.5, shouldn't be returned
        q6_attempt = TextAttempt(response="Attempt6", user=u1, question=q6,
                                 next_attempt=date.today(), e_factor = 2.5)
        q7_attempt = TextAttempt(response="Attempt7", user=u1, question=q7,
                                 next_attempt=date.today(), e_factor = 2.5)

        # lo4: attempts for the same question(same objective) (only most recent attempt should be counted), attempt 2 should be returned
        q8_attempt = TextAttempt(response="Attempt8", user=u1, question=q8,
                                 next_attempt=date.today()-timedelta(days=1), e_factor = 2.5)
        q8_attempt2 = TextAttempt(response="Attempt8b", user=u1, question=q8,
                                 next_attempt=date.today(), e_factor = 2)

        # lo1: single attempt for u2, to make sure method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 next_attempt=date.today()+timedelta(days=1))


        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, 
                    q5_attempt,  q6_attempt, q7_attempt, q8_attempt, q8_attempt2, q1_attempt])

        self.assertEqual(a.objectives_to_review(u1).all(), [(lo2,1.5),(lo4,2)])

        #add more tests for where more than three objective have an average e_factor < 2.5


if __name__ == '__main__':
    unittest.main(verbosity=2)
