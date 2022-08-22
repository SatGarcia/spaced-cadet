describe('The Home Page', function() {
  beforeEach(function() {
    // reset and seed the database prior to every test
    cy.request('/test/reset_db')

    // create an instructor
    cy.request('POST', '/test/seed/user', { 
      instructor: true,
      email: 'instructor@cadet.com',
      password: 'testing',
      'first-name': 'Foo',
      'last-name': 'Instructor' })
      .its('body')
      .as('instructorUser')

    cy.request('POST', '/test/seed/course', {
      name: 'test-course',
      'instructor_email': 'instructor@cadet.com',
      'num_students': 2,
      'num_past_assessments': 1,
      'num_upcoming_assessments': 2})
      .its('body')
      .as('testCourse')
      .then(course => {
        return course.users.filter(u => u.email !== 'instructor@cadet.com')
      })
      .should('have.length', 2)
      .then(students => {
	    cy.login(students[0].email, 'testing')
      })

    // create questions for the five assessments created with the course
    for (let i = 1; i <= 3; i++) {
      cy.request('POST', '/test/seed/question/short-answer', { 
        'author_id': 1, // FIXME: not safe to assume ID of instructor is 1
        'assessment_id': i,
        'amount': i*2,
      })
    }

  })

  it('Basic Layout', function() {
    cy.visit('/')

    cy.get('#course-0').contains('test-course')
    cy.get('#course-0').contains('Visit Course Training Center')
    
    // only upcoming assignments (2 and 3) should show up
    cy.get('#course-0').contains('Assessment 2')
    cy.get('#course-0').contains('Assessment 3')
    cy.get('#course-0').should('not.contain', 'Assessment 1')

    cy.get('#mission-0_0').contains('Deadline')
    cy.get('#mission-0_0').contains('Begin Training').click()

    cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/2/train`)
  })
})

