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
      .then((user) => {
        cy.request('POST', '/test/seed/objective', {author_id: user.id})
          .its('body')
          .as('learningObjective')
      })

	cy.login('test@cadet.com', 'testing')
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

  it('My Questions', function () {
    cy.visit(`/u/${this.currentUser.id}/questions`)
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

})

