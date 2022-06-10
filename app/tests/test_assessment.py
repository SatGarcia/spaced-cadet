import unittest
from app import create_app, db
from app.db_models import User, Assessment, ShortAnswerQuestion, TextAttempt
from datetime import date, timedelta

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


    @unittest.skip("Test not implemented")
    def test_overdue_questions(self):
        pass

    @unittest.skip("Test not implemented")
    def test_waiting_questions(self):
        pass






    @unittest.skip("Test not implemented")
    def test_fresh_questions(self):
        """ Returns all "fresh" assessment questions, where fresh is defined as needing
        to be practiced by the user for the FIRST time today. 
        
        questions should be unattempted, due, or overdue
        """
        # adds questions and users to this session 
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

        # if no questions are attempted yet, they should be fresh
        self.assertCountEqual(a.fresh_questions(u1).all(), [q1,q2,q3,q4])

        # three attempts for u1: one with next attempt of today, one with next
        # attempt yesterday, and one with tomorrow
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 next_attempt=date.today())
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 next_attempt=(date.today()-timedelta(days=1))) # attempt of yesterday
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 next_attempt=(date.today()+timedelta(days=1))) # attempt of tomorrow

        # single attempt for u2, with next attempt of today to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 next_attempt=date.today())

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(a.fresh_questions(u1).all(), [q2,q3])


    @unittest.skip("Test not implemented")
    def test_repeat_questions(self):
        """ Returns all assessment questions that the user has already attempted today
        but that haven't gotten a quality score of 4 or above."""
        # adds questions and users to this session 
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

        # if no questions are attempted yet today, they should not be repreated
        self.assertEqual(a.repeat_questions(u1).all(), [])

        # three attempts for u1
        q2_attempt = TextAttempt(response="Attempt2", user=u1, question=q2,
                                 time=date.today(), quality = 4) # attempt today and quality of 4 
        q3_attempt = TextAttempt(response="Attempt3", user=u1, question=q3,
                                 time=(date.today()-timedelta(days=1)), quality = 3) # attempt of yesterday and 4 or above
        q4_attempt = TextAttempt(response="Attempt4", user=u1, question=q4,
                                 time=(date.today()), quality = 2)  # attempt of today and quality not above a 4

        # single attempt for u2, with next attempt of today to make sure
        # method differentiates between users
        q1_attempt = TextAttempt(response="Attempt1", user=u2, question=q1,
                                 time=(date.today()), quality = 2)

        db.session.add_all([q2_attempt, q3_attempt, q4_attempt, q1_attempt])

        self.assertCountEqual(a.repeat_questions(u1).all(), [q4])
        
        # test that we successfully get multiple questions by changing one of
        # the attempts to be due today
        q3_attempt.time = date.today()
        db.session.commit()

        self.assertCountEqual(a.repeat_questions(u1).all(), [q4, q3])


if __name__ == '__main__':
    unittest.main(verbosity=2)
