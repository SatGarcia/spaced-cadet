describe('The Login Page', () => {
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
  })

  it('sets auth cookie when logging in via form submission', function () {
    // destructuring assignment of the this.currentUser object
    //const { username, password } = this.currentUser

    cy.visit('/auth/login')

    cy.get('input[name=email]').type('test@cadet.com')

    // {enter} causes the form to submit
    cy.get('input[name=password]').type(`testing{enter}`)

    // we should be redirected to /
    cy.url().should('eq', 'http://localhost:5000/')

    // our auth cookies should be present (both session and JWT)
    cy.getCookie('session').should('exist')
    cy.getCookie('access_token_cookie').should('exist')
    cy.getCookie('csrf_access_token').should('exist')

    // UI should reflect this user being logged in
    cy.get('h2').should('contain', 'Foo')
  })
})

describe('Course Overview Page', () => {
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
  })

  it('logs in programmatically without using the UI', function () {
    // destructuring assignment of the this.currentUser object
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

    // now that we're logged in, we can visit
    // any kind of restricted route!
    cy.visit('/c/test-course')

    cy.get('h3').should('contain', this.testCourse.title)
  })
})

