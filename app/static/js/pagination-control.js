export default {
  compilerOptions: {
    delimiters: ["[[", "]]"]
  },

  props: {
    num_items: {
      type: Number,
      required: true,
    },
    items_per_page: {
      type: Number,
      default: 10,
    },
    description: {
      type: String,
      required: true,
    },
  },

  emits: ['selected-page'],

  computed: {
    num_pages() {
      return Math.ceil(this.num_items / this.items_per_page);
    },

    pages() {
      const num_pages = Math.ceil(this.num_items / this.items_per_page);
      let arr = [];
      for (let i = 0; i < num_pages; i++) {
        arr.push({start: i * this.items_per_page, end: Math.min((i+1)*this.items_per_page, this.num_items)});
      }

      return arr;
    }
  },

  data() {
    return {
      selected_page_num: 0,
    }
  },

  methods: {
    setSelectedPage(index) {
      this.selected_page_num = index;
      this.$emit('selected-page', this.pages[index].start, this.pages[index].end);
    },

    selectPreviousPage() {
      this.setSelectedPage(this.selected_page_num - 1);
    },

    selectNextPage() {
      this.setSelectedPage(this.selected_page_num + 1);
    },
  },

  template: `
  <nav :aria-label="description" v-if="num_items > items_per_page">
    <ul class="pagination justify-content-center">
      <li class="page-item" :class="{disabled: selected_page_num === 0}">
        <a class="page-link" href="javascript:undefined" @click="selectPreviousPage">Previous</a>
      </li>

      <li class="page-item" v-for="(page, index) in pages" :key="index"
          :class="{active: selected_page_num === index}">
        <a class="page-link" href="javascript:undefined"
            @click="setSelectedPage(index)">[[index + 1]]</a>
      </li>

      <li class="page-item" :class="{disabled: selected_page_num === (pages.length-1)}">
        <a class="page-link" href="javascript:undefined" @click="selectNextPage">Next</a>
      </li>
    </ul>
  </nav>
  `

};
