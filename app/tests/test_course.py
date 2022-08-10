import unittest
from app import create_app, db
from app.db_models import Course, Assessment, ClassMeeting, User, Objective, TextAttempt, ShortAnswerQuestion
from datetime import date, timedelta, datetime

class CourseModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # create a test course that is a week long to give room to test assessments that will be added to this course
        self.c = Course(name="test-course1", title="Test Course 1", description="",
                    start_date=(date.today()-timedelta(days=3)),
                    end_date=(date.today()+timedelta(days=3)))

        # create a second test course that is a week long to give room to test assessments that will be added to this course
        self.c2 = Course(name="test-course2", title="Test Course 2", description="",
                    start_date=(date.today()-timedelta(days=3)),
                    end_date=(date.today()+timedelta(days=3)))
        
        db.session.add(self.c)
        db.session.add(self.c2)
        db.session.commit()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_users(self):
        self.u1 = User(email="test@test.com", first_name="Test", last_name="User")
        self.u1.set_password("test")
        self.u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        self.u2.set_password("test")
        self.u3 = User(email="test3@test.com", first_name="Test3", last_name="User")
        self.u3.set_password("test")
        self.u4 = User(email="test4@test.com", first_name="Test4", last_name="User")
        self.u4.set_password("test")
        self.u5 = User(email="test5@test.com", first_name="Test5", last_name="User")
        self.u5.set_password("test")
        self.u6 = User(email="test6@test.com", first_name="Test6", last_name="User")
        self.u6.set_password("test")
        self.u7 = User(email="test7@test.com", first_name="Test7", last_name="User")
        self.u7.set_password("test")
        self.u8 = User(email="test8@test.com", first_name="Test8", last_name="User")
        self.u8.set_password("test")
        self.u9 = User(email="test9@test.com", first_name="Test9", last_name="User")
        self.u9.set_password("test")
        self.u10 = User(email="test10@test.com", first_name="Test10", last_name="User")
        self.u10.set_password("test")

        db.session.add_all([self.u1, self.u2,self.u3, self.u4, self.u5, self.u6, self.u7, self.u8, self.u9, self.u10])
        db.session.commit()

        self.c.users.append(self.u1)
        self.c.users.append(self.u2)
        self.c2.users.append(self.u3)
        self.c2.users.append(self.u4)
        self.c3.users.append(self.u5)
        self.c3.users.append(self.u6)
        self.c4.users.append(self.u7)
        self.c4.users.append(self.u8)
        self.c5.users.append(self.u9)
        self.c5.users.append(self.u10)

    def create_objectives_and_more_courses(self):
        self.c3 = Course(name="test-course3", title="Test Course 3", description="",
                    start_date=(date.today()-timedelta(days=3)),
                    end_date=(date.today()+timedelta(days=3)))

        self.c4 = Course(name="test-course4", title="Test Course 4", description="",
                    start_date=(date.today()-timedelta(days=3)),
                    end_date=(date.today()+timedelta(days=3)))

        self.c5 = Course(name="test-course5", title="Test Course 5", description="",
                    start_date=(date.today()-timedelta(days=3)),
                    end_date=(date.today()+timedelta(days=3)))
        
        db.session.add(self.c3)
        db.session.add(self.c4)
        db.session.add(self.c5)
        db.session.commit()

        self.a = Assessment(title="Test assessment3", time = datetime.now()) 

        self.lo1 = Objective(description="Learning Objective 1")
        self.lo2 = Objective(description="Learning Objective 2")
        self.lo3 = Objective(description="Learning Objective 3")
        self.lo4 = Objective(description="Learning Objective 4")
        self.lo5 = Objective(description="Learning Objective 5")

        self.q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1",objective = self.lo1)
        self.q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2",objective = self.lo2)
        self.q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3",objective = self.lo3)
        self.q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4",objective = self.lo4)
        self.q5 = ShortAnswerQuestion(prompt="Question 5", answer="Answer 5",objective = self.lo5)

        db.session.add_all([self.a, self.lo1, self.lo2, self.lo3, self.lo4, self.lo5, self.q1, self.q2, self.q3, self.q4, self.q5])
        db.session.commit()

        self.a.objectives.append(self.lo1)
        self.a.objectives.append(self.lo2)
        self.a.objectives.append(self.lo3)
        self.a.objectives.append(self.lo4)
        self.a.objectives.append(self.lo5)

        self.a.questions.append(self.q1)
        self.a.questions.append(self.q2)
        self.a.questions.append(self.q3)
        self.a.questions.append(self.q4)
        self.a.questions.append(self.q5)


    def create_assessments(self):
        self.a1 = Assessment(title="Test assessment1", time = datetime.now()-timedelta(days=2))  # assessment occurs during course, before current date
        self.a2 = Assessment(title="Test assessment2", time = datetime.now()-timedelta(hours=1)) # assessment occurs during course, today (an hour before this moment)
        self.a3 = Assessment(title="Test assessment3", time = datetime.now())                    # assessment occurs during course, today (right at this moment)
        self.a4 = Assessment(title="Test assessment4", time = datetime.now()+timedelta(hours=1)) # assessment occurs during course, today (an hour after this moment)
        self.a5 = Assessment(title="Test assessment5", time = datetime.now()+timedelta(days=2))  # assessment occurs during course, after current date

        # add assessments within the first course all with differing times
        self.c.assessments.append(self.a5)
        self.c.assessments.append(self.a4)
        self.c.assessments.append(self.a3)
        self.c.assessments.append(self.a2)
        self.c.assessments.append(self.a1)

        # extra assessments to add to a second course
        self.a6 = Assessment(title="Test assessment6", time = datetime.now()-timedelta(hours=1)) # assessment occurs during course, today (an hour before this moment)
        self.a7 = Assessment(title="Test assessment7", time = datetime.now()+timedelta(hours=1)) # assessment occurs during course, today (an hour after this moment)
        
        # add assessments within the second course: will ensure that the function can differentiate between different courses
        self.c2.assessments.append(self.a6)
        self.c2.assessments.append(self.a7)

        db.session.commit()


    def create_meetings(self):
        # course meetings to add
        self.cm1 = ClassMeeting(title = 'Meeting 1', date = datetime.now()-timedelta(days=2))
        self.cm2 = ClassMeeting(title = 'Meeting 2', date = datetime.now())
        self.cm3 = ClassMeeting(title = 'Meeting 3', date = datetime.now()+timedelta(days=2))

        # add meetings within the first course all with differing times
        self.c.meetings.append(self.cm2)
        self.c.meetings.append(self.cm3)
        self.c.meetings.append(self.cm1)
        db.session.commit()

        # extra meetings to add to a second course
        self.cm4 = ClassMeeting(title = 'Meeting 4', date = datetime.now()-timedelta(days=1))
        self.cm5 = ClassMeeting(title = 'Meeting 5', date = datetime.now()+timedelta(days=1))

        # add meetings within the second course: will ensure that the function can differentiate between different courses
        self.c2.meetings.append(self.cm4)
        self.c2.meetings.append(self.cm5)

        db.session.commit()


    def test_upcoming_assessments(self):
        # test: if no assessments are added to the course yet, then none should be upcoming
        self.assertCountEqual(self.c.upcoming_assessments(), []) 

        self.create_assessments()

        # a4 and a5 should be upcoming because they haven't occurred yet
        self.assertCountEqual(self.c.upcoming_assessments(), [self.a4, self.a5])


    def test_past_assessments(self):
        # test: if no assessments are added to the course yet, then none should be upcoming
        self.assertCountEqual(self.c.past_assessments(), []) 

        self.create_assessments()

        # a1,a2,a3 should be past because they have already occurred 
        self.assertCountEqual(self.c.past_assessments(), [self.a1, self.a2, self.a3])


    def test_upcoming_meetings(self):
        # test: if no meetings are added to the course yet, then none should be upcoming
        self.assertCountEqual(self.c.upcoming_meetings(), []) 

        self.create_meetings()

        # cm2,cm3 should be upcoming because they haven't occurred yet or are today
        self.assertCountEqual(self.c.upcoming_meetings(), [self.cm2, self.cm3])


    def test_previous_meetings(self):
        # test: if no meetings are added to the course yet, then none should be upcoming
        self.assertCountEqual(self.c.previous_meetings(), []) 

        self.create_meetings()
        
        # any meetings before today are previous
        self.assertCountEqual(self.c.previous_meetings(), [self.cm1])

    def test_star_rating(self):
        self.create_objectives_and_more_courses()
        # test: if no attempts are made then 0 should be returned
        self.assertEqual(self.c.star_rating(self.lo1, self.a), 0) 

        self.create_users()
        # test: if no users are made then 0 should be returned
        self.assertEqual(self.c.star_rating(self.lo1, self.a), 0) 

        # test with u1, u2 and lo1 for 1 full star
        user1_attempt = TextAttempt(response="Attempt1", user=self.u1, question=self.q1, e_factor = 1.5)
        user2_attempt = TextAttempt(response="Attempt2", user=self.u2, question=self.q1, e_factor = 1.5)
        db.session.add_all([user1_attempt, user2_attempt])

        self.assertEqual(self.c.star_rating(self.lo1, self.a), 1) 

        # test with u3, u4 and lo2 for 2 full stars
        user3_attempt = TextAttempt(response="Attempt1", user=self.u3, question=self.q2, e_factor = 2.5)
        user4_attempt = TextAttempt(response="Attempt2", user=self.u4, question=self.q2, e_factor = 2.5)
        db.session.add_all([user3_attempt, user4_attempt])

        self.assertEqual(self.c2.star_rating(self.lo2, self.a), 2) 

        # test with u5, u6 and lo3 for 3 full stars
        user5_attempt = TextAttempt(response="Attempt1", user=self.u5, question=self.q3, e_factor = 4)
        user6_attempt = TextAttempt(response="Attempt2", user=self.u6, question=self.q3, e_factor = 4)
        db.session.add_all([user5_attempt, user6_attempt])

        self.assertEqual(self.c3.star_rating(self.lo3, self.a), 3) 

        # test with u7, u8 and lo4 for 4 full stars
        user7_attempt = TextAttempt(response="Attempt1", user=self.u7, question=self.q4, e_factor = 6)
        user8_attempt = TextAttempt(response="Attempt2", user=self.u8, question=self.q4, e_factor = 6)
        db.session.add_all([user7_attempt, user8_attempt])

        self.assertEqual(self.c4.star_rating(self.lo4, self.a), 4) 

        # test with u9, u10 and lo5 for 5 full stars
        user9_attempt = TextAttempt(response="Attempt1", user=self.u9, question=self.q5, e_factor = 10)
        user10_attempt = TextAttempt(response="Attempt2", user=self.u10, question=self.q5, e_factor = 10)
        db.session.add_all([user9_attempt, user10_attempt])

        self.assertEqual(self.c5.star_rating(self.lo5, self.a), 5) 

        
        