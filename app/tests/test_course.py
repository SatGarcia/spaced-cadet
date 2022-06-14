import unittest
from app import create_app, db
from app.db_models import Course, Assessment, ClassMeeting
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
        