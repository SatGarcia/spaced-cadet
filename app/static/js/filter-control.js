export default {
  compilerOptions: {
    delimiters: ["[[", "]]"]
  },

  props: {
    filters: {
      type: Array,
      required: true,
    },
  },

  emits: ['selected-filter'],

  computed: {
    div_style() {
      return this.filters.map(
        f => {
                  const is_active = f.name === this.selected_filter.name;
                  return {'border-bottom': is_active, 'border-primary': is_active, 'border-3': is_active};
                });
    },
  },

  data() {
    return {
      selected_filter: undefined,
    }
  },

  methods: {
    setFilter(index) {
      this.selected_filter = this.filters[index];
      this.$emit('selected-filter', this.selected_filter.func);
    },
  },

  created() {
    this.selected_filter = this.filters[0];
  },

  template: `
  <div>
      Show:
      <span v-for="(filter, index) in filters" :key="index" class="ms-2 pb-2" :class="div_style[index]">
          <button role="button" class="btn btn-link text-decoration-none link-secondary"
                  :class="filter.name === selected_filter.name ?  'link-dark' : 'link-secondary'"
                 @click="setFilter(index)">
              [[ filter.name ]]
          </button>
      </span>
  </div>
  `

};
