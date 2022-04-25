import { showSnackbarMessage, fetchOrRefresh } from './helpers.js';
import { createNewObjective } from './cadet-api.js';

export default {
  compilerOptions: {
    delimiters: ["[[", "]]"]
  },

  props: {
    name: String,
  },

  emits: ['objectiveSet', 'cancelled'],

  data() {
    return {
      search_string: "",
      objectives: null,
      selected_objective_id: null,
      objective_text: "", // TODO: make this come from emitting event
      new_objective_description: "",
      new_objective_public: true,
      refresh_url: "/auth/refresh", // FIXME: make this a prop (or some other way to get this info)
    }
  },

  methods: {
    async setObjective() {
      /**
       * If something is selected, emit an event with the selected objective
       * ID so the parent can set the objective in whatever question(s) it
       * seems fit.
        **/
      if (this.selected_objective_id === null) {
        return;
      }
      else {
        this.$emit('objectiveSet', this.selected_objective_id);
      }

      // clear out selected id and search results before closing
      this.search_string = "";
      this.selected_objective_id = null;
      this.objectives = null;

      const modal_el = document.getElementById('setObjectiveModal');
      const objectives_modal = bootstrap.Modal.getInstance(modal_el);
      objectives_modal.hide();
    },

    async searchObjectives() {
      let url = "/api/objectives?html";  // FIXME "{{ url_for('objectives_api') }}";
      if (this.search_string) {
        url = url + "&q=" + encodeURIComponent(this.search_string);
      }
      const response = await fetchOrRefresh(url, 'GET', this.refresh_url);
      if (response.ok) {
        const foo = await response.json();
        this.objectives = foo["learning_objectives"];
      }
      else {
        const modal_el = document.getElementById('setObjectiveModal');
        const objectives_modal = bootstrap.Modal.getInstance(modal_el);
        objectives_modal.hide();
        showSnackbarMessage(`Error searching for learning objective. Try again. (HTTP Status: ${response.status})`);
      }
    },

    async addObjective() {
      const response = await createNewObjective(this.new_objective_description, this.new_objective_public);
      if (response.ok) {
        const r = await response.json();

        this.objective_text = r["objective"].description;
        this.selected_objective_id = r["objective"].id;
        await this.setObjective();

        showSnackbarMessage("Successfully created and set learning objective.");
      }
      else {
        showSnackbarMessage(`Error creating learning objective. Try again. (HTTP Status: ${response.status})`);
      }

      this.new_objective_description = "";
      this.new_objective_public = true;

      const modal_el = document.getElementById('newObjectiveModal');
      const new_objective_modal = bootstrap.Modal.getInstance(modal_el);
      new_objective_modal.hide();
    },
  },

  template: `
    <!-- Modal for setting the learning objective. -->
    <div class="modal fade" :id="name" tabindex="-1" :aria-labelledby="name + 'Label'" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">

                <div class="modal-header">
                    <h5 class="modal-title" :id="name + 'Label'">
                        Update Question's Learning Objective
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>

                <div class="modal-body">
                    <div class="row pb-2">
                        <div class="input-group">
                            <label for="searchObjectives"
                                   class="form-label visually-hidden">
                                Search Learning Objectives</label>
                            <input 
                                id="searchObjectives"
                                v-model.trim="search_string" 
                                @keyup.enter="searchObjectives()"
                                type="text"
                                class="form-control"
                                placeholder="Search learning objectives (e.g. while loop)">
                            <button class="btn btn-xs btn-primary"
                                @click="searchObjectives()">
                                <i class="bi-search"></i>
                                Search
                            </button>
                        </div>
                    </div>

                    <div v-if="objectives !== null">
                        <strong>Search Results ([[ objectives.length ]]):</strong>
                        <div class="container" v-if="objectives.length === 0">
                            <em>No search results.</em>
                        </div>
                        <div class="container" v-else>
                            <ul class="list-unstyled">
                                <li v-for="(lo, index) in objectives"
                                    :key="lo.id"
                                    class="border rounded p-1 m-2"
                                    :class="{ 'border-primary': selected_objective_id == lo.id }">
                                    <input 
                                        :id="'opt' + index"
                                        :value="lo.id"
                                        v-model.number="selected_objective_id"
                                        name="objOptions"
                                        type="radio"
                                        class="visually-hidden">
                                    <label :for="'opt' + index" v-html="lo.description"></label>
                                </li>
                            </ul>
                        </div>
                    </div>
                    <div class="mt-3">
                    <em>
                        Can't find a suitable learning objective?
                    </em>
                    <a href="#" class="text-decoration-none" data-bs-toggle="modal" data-bs-target="#newObjectiveModal" data-bs-dismiss="modal">
                        Create a New Objective
                    </a>
                    </div>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary"
                            @click="setObjective()"
                            :disabled="selected_objective_id === null"
                            >Save Selection</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal for creating a new learning objective. -->
    <div class="modal fade" id="newObjectiveModal" tabindex="-1" aria-labelledby="newObjectiveModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">

                <div class="modal-header">
                    <h5 class="modal-title" id="newObjectiveModalLabel">
                        Create a New Learning Objective
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>

                <div class="modal-body">
                    <label for="objectiveDescription"
                           class="form-label visually-hidden">
                        Description</label>
                    <textarea 
                        id="objectiveDescription"
                        v-model.trim="new_objective_description" 
                        class="form-control"
                        placeholder="Enter the learning objective's description. Markdown is allowed."
                        required></textarea>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" value=""
                                                                        id="newObjectivePublic" checked
                                                                        v-model="new_objective_public">
                        <label class="form-check-label" for="newObjectivePublic">
                            Public
                        </label>
                    </div>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary"
                            @click="addObjective()"
                                          :disabled="new_objective_description.length === 0">
                        Create Objective
                    </button>
                </div>
            </div>
        </div>
    </div>
  `,

};
