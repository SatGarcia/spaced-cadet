describe('Instructor Course Management', () => {
  beforeEach(() => {
    // reset and seed the database prior to every test
    cy.request('/test/reset_db')

    // seed a user in the DB that we can control from our tests
    cy.request('POST', '/test/seed/user', { 
      instructor: true,
      email: 'test@cadet.com',
      password: 'testing',
      'first-name': 'Foo',
      'last-name': 'Bar' })
      .its('body')
      .as('currentUser')

    cy.request('POST', '/test/seed/course', { 
      name: 'test-course',
      'instructor_email': 'test@cadet.com',
      'num_students': 5,
      'num_past_assessments': 2,
      'num_upcoming_assessments': 3})
      .its('body')
      .as('testCourse')

    // login (without UI)
    cy.request({
      url: '/auth/login',
      method: 'POST',
      form: true,
      body: {
        email: 'test@cadet.com',
        password: 'testing'
      },
    })

    // our auth cookie should be present
    cy.getCookie('access_token_cookie').should('exist')
  })

  it('Course Overview Page', function () {
    cy.visit(`/c/${this.testCourse.name}`)

    cy.get('h3').should('contain', this.testCourse.title)

    cy.get('[id=instructorMenu]').contains('Manage Assessments')
    cy.get('[id=instructorMenu]').should('contain', 'Manage Roster')
    cy.get('[id=instructorMenu]').should('contain', 'Edit Settings')
    cy.get('[id=instructorMenu]').should('contain', 'Course Setup')
  })

  it('Edit Course Settings Page', function () {
    cy.visit(`/c/${this.testCourse.name}`)

    cy.get('[id=instructorMenu]').contains('Edit Settings').click()

    cy.contains("Edit Course Settings")

    cy.get('input[name=title]').clear().type('Zippy Course Title')
    cy.get('textarea[name=description]').clear().type('A shiny new course description')
    cy.get('input[name=start_date]').type('2021-01-15')
    cy.get('input[name=submit]').click()
    cy.url().should('contain', '/c/test-course')
    cy.get('h3').should('contain', 'Zippy Course Title')
    cy.contains('A shiny new course description')
  })

  it('Manage Roster', function () {
    cy.visit(`/c/${this.testCourse.name}`)

    cy.get('[id=instructorMenu]').contains('Manage Roster').click()

    cy.contains(`Manage Roster (${this.testCourse.name})`)

    // Check that all the students appear
    for (const user of this.testCourse.users) {
      cy.get('tr').contains(user.email)
    }

    const user_to_delete = this.testCourse.users[2]
    cy.get('tr').contains(user_to_delete.email).parent().contains('Remove').click()
    cy.get('table').contains(user_to_delete.email).should('not.exist')
  })
})

