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

    cy.request('POST', '/test/seed/objective', { 
      author_id: 1})
      .its('body')
      .as('learningObjective')

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

  const getIframeDocument = () => {
    return cy
      .get('iframe')
      .its('0.contentDocument').should('exist')
  }

  const getIframeBody = () => {
    // get the document
    return getIframeDocument()
      .its('body').should('not.be.undefined')
      .then(cy.wrap)
  }

  /*
  it('gets the post', () => {
    cy.visit('index.html')
    getIframeBody().find('#run-button').should('have.text', 'Try it').click()
    getIframeBody().find('#result').should('include.text', '"delectus aut autem"')
  })
  */

  it('My Questions', function () {
    cy.visit('/u/1/questions')
    cy.contains('Create New Question').click()
    cy.contains('Short Answer (Self-Graded)').click()

    cy.get('textarea[name=prompt]').type("What is this?")
    cy.get('textarea[name=answer]').type("No one really knows.")
    cy.get('input[type=submit]').click()

    getIframeBody().contains("Question Preview")
    getIframeBody().contains("What is this?")
    getIframeBody().contains("I Don't Know").should('be.disabled')
    getIframeBody().contains("Submit").should('be.disabled')

    cy.contains("No one really knows")
    cy.get('#learningObjective').contains("None")
    cy.get('#learningObjective').contains("Add Objective").click()

    // manually wait because of a race condition with modal being ready in
    // time for typing
    cy.get("#searchObjectives")
      .should('be.visible')
      .wait(1000)
      .type(this.learningObjective.description + '{enter}')

    cy.get("#objectiveSearchResults")
      .should('exist.and.be.visible')
      .contains(this.learningObjective.description)
      .click()

    cy.get("#setObjectiveModal")
      .should('be.visible')
      .contains('Save Selection')
      .click()

    cy.get("#setObjectiveModal")
      .should('not.be.visible')
    
    cy.get('#learningObjective')
      .contains(this.learningObjective.description)

    cy.get('#objectiveActions')
      .contains('Remove Objective')
      .click()

    cy.get("#learningObjective")
      .should('not.contain', this.learningObjective.description)
      .and('contain', 'None')

    cy.get("#publicQuestion").uncheck()
    cy.get("#enabledQuestion").check()

    cy.contains("Finish Review").click()

    // TODO: check URL to see that we are on the my questions overview page
    
    cy.get('tbody')
      .should('have.length', 1)
      .as('questionOverview')

    cy.get('@questionOverview')
      .contains("Public:")
      .next()
      .find('i')
      .should('have.length', 1)
      .and('have.class', 'bi-x-circle')

    cy.get('@questionOverview')
      .contains("Enabled:")
      .next()
      .find('i')
      .should('have.length', 1)
      .and('have.class', 'bi-check-circle')

    //cy.get("#searchObjectives").type(this.learningObjective.description + '{enter}')
    //cy.get('#setObjectiveModal').contains("Create a New Objective").click()
    //cy.get('#newObjectiveModal').contains("Create Objective").should('be.disabled')
    //cy.get('#newObjectiveModal').get('textarea[id=objectiveDescription]').type('DoSomethingSmart')
    //cy.get('textarea[id=objectiveDescription]').type('XOXOXOXOXO')
    //cy.get('#newObjectiveModal').contains("Create Objective").should('not.be.disabled').click()
    //cy.get('#newObjectiveModal').contains("Create Objective").click()
    //cy.get('#learningObjective').contains("X")

    //cy.get('iframe').contains("What is this?")

    /*
    cy.get('h3').should('contain', this.testCourse.title)

    cy.get('[id=instructorMenu]').contains('Manage Assessments')
    cy.get('[id=instructorMenu]').should('contain', 'Manage Roster')
    cy.get('[id=instructorMenu]').should('contain', 'Edit Settings')
    cy.get('[id=instructorMenu]').should('contain', 'Course Setup')
    */
  })

  /*
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

    cy.get('input[type=file]').selectFile('cypress/fixtures/text_files/roster1.csv')
    cy.get('input[type=submit]').contains('Upload Roster').click()
    cy.get('tbody').contains('bradley@mockingbird.com')
    cy.get('tbody').contains('gravy@thanksgiving.org')

    // upload another roster file with column names that don't auto populate
    // correctly, using the add/drop option to remove all students not in the
    // file
    cy.get('input[type=file]').selectFile('cypress/fixtures/text_files/roster2.csv')
    cy.get('select[name=email_index]').select('Correo')
    cy.get('select[name=last_name_index]').select('Surname')
    cy.get('select[name=first_name_index]').select('Primary Name')
    cy.get('input[name=add_drop]').check()
    cy.get('input[type=submit]').contains('Upload Roster').click()

    // check flash messages
    cy.contains("Removed 5 students")
    cy.contains("Added 2 new students")
    cy.contains("Skipped 1 who were")

    // check contents of table
    cy.get('tbody').contains('bradley@mockingbird.com')
    cy.get('tbody').contains("chocolate@swiss.ch")
    cy.get('tbody').contains("Michael")
    cy.get('tbody').contains("Toblerone")
    cy.get('tbody').contains("gravey@thanksgiving.org").should('not.exist')

  })
  */
})

