import { showSnackbarMessage, fetchOrRefresh } from './helpers.js';
import { createNewTopic } from './cadet-api.js';

const refresh_url = Flask.url_for('auth.refresh_jwts');

export default {
  compilerOptions: {
    delimiters: ["[[", "]]"]
  },

  props: {
    name: String,
  },

  emits: ['topicSet', 'createdNewTopic', 'failedToCreate', 'failedToSearch'],

  data() {
    return {
      search_string: "",
      topics: null,
      selected_topic_id: null,
      new_topic_text: "",
    }
  },

  methods: {
    setTopic() {
      /**
       * If something is selected, emit an event with the selected topic
       * ID so the parent can set the topic in whatever objectives(s) it
       * see fit.
       **/
      if (this.selected_topic_id === null) {
        return;
      }
      else {
        this.$emit('topicSet', this.selected_topic_id);
      }

      // clear out selected id and search results before closing
      this.search_string = "";
      this.selected_topic_id = null;
      this.topics = null;

      const modal_el = document.getElementById(this.name);
      const modal = bootstrap.Modal.getInstance(modal_el);
      modal.hide();
    },

    async searchTopics() {
      let url = Flask.url_for('topics_api');
      if (this.search_string) {
        url = url + "?q=" + encodeURIComponent(this.search_string);
      }
      const response = await fetchOrRefresh(url, 'GET', refresh_url);
      if (response.ok) {
        const r = await response.json();
        this.topics = r["topics"];
      }
      else {
        const modal_el = document.getElementById(this.name);
        const modal = bootstrap.Modal.getInstance(modal_el);
        modal.hide();
        this.$emit('failedToSearch');
      }
    },

    async addTopic() {
      const response = await createNewTopic(this.new_topic_text);
      if (response.ok) {
        this.$emit('createdNewTopic');

        const r = await response.json();

        this.selected_topic_id = r["topic"].id;
        this.setTopic();
      }
      else {
        this.$emit('failedToCreate');
      }

      this.new_topic_text = "";

      const modal_el = document.getElementById('newTopicModal');
      const new_topic_modal = bootstrap.Modal.getInstance(modal_el);
      new_topic_modal.hide();
    },
  },

  template: `
    <!-- Modal for setting the topic. -->
    <div class="modal fade" :id="name" tabindex="-1" :aria-labelledby="name + 'Label'" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">

                <div class="modal-header">
                    <h5 class="modal-title" :id="name + 'Label'">
                        Set a Topic
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>

                <div class="modal-body">
                    <div class="row pb-2">
                        <div class="input-group">
                            <label for="searchTopics"
                                   class="form-label visually-hidden">
                                Search Topics</label>
                            <input 
                                id="searchTopics"
                                v-model.trim="search_string" 
                                @keyup.enter="searchTopics()"
                                type="text"
                                class="form-control"
                                placeholder="Search topics (e.g. loop)">
                            <button class="btn btn-xs btn-primary"
                                @click="searchTopics()">
                                <i class="bi-search"></i>
                                Search
                            </button>
                        </div>
                    </div>

                    <div v-if="topics !== null">
                        <strong>Search Results ([[ topics.length ]]):</strong>
                        <div class="container" v-if="topics.length === 0">
                            <em>No search results.</em>
                        </div>
                        <div class="container" v-else>
                            <ul class="list-unstyled">
                                <li v-for="(t, index) in topics"
                                    :key="t.id"
                                    class="border rounded p-1 m-2"
                                    :class="{ 'border-primary': selected_topic_id == t.id }">
                                    <input 
                                        :id="'opt' + index"
                                        :value="t.id"
                                        v-model.number="selected_topic_id"
                                        name="topicOptions"
                                        type="radio"
                                        class="visually-hidden">
                                    <label :for="'opt' + index">[[ t.text ]]</label>
                                </li>
                            </ul>
                        </div>
                    </div>
                    <div class="mt-3">
                    <em>
                        Can't find a suitable topic?
                    </em>
                    <a href="#" class="text-decoration-none" data-bs-toggle="modal" data-bs-target="#newTopicModal" data-bs-dismiss="modal">
                        Create a New Topic
                    </a>
                    </div>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary"
                            @click="setTopic()"
                            :disabled="selected_topic_id === null"
                            >Save Selection</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal for creating a new topic. -->
    <div class="modal fade" id="newTopicModal" tabindex="-1" aria-labelledby="newTopicModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">

                <div class="modal-header">
                    <h5 class="modal-title" id="newTopicModalLabel">
                        Create a New Topic
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>

                <div class="modal-body">
                    <label for="topicText"
                           class="form-label visually-hidden">
                        Text</label>
                    <input 
                        type="text"
                        id="topicText"
                        v-model.trim="new_topic_text" 
                        class="form-control"
                        placeholder="Enter the topic keyword/phrase."
                        required />
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary"
                            @click="addTopic()"
                            :disabled="new_topic_text.length === 0">
                        Create Topic
                    </button>
                </div>
            </div>
        </div>
    </div>
  `,

};
