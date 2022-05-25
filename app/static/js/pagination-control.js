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

  emits: ['selected-page', 'selected-page-num'],

  watch: {
    all_pages(new_pages, old_pages) {
      if (new_pages.length === 0) {
        // if there are now no items, 0 out page number and emit event saying
        // no items were selected (start and end both 0)
        this.selected_page_num = 0;
        this.$emit('selected-page', 0, 0);
        this.$emit('selected-page-num', 0);
      }

      else if (new_pages.length > 0 && old_pages.length === 0) {
        // if going from no pages to some pages set page number as 0
        this.setSelectedPage(0);
      }

      else if (this.selected_page_num >= new_pages.length) {
        // if the page we were on doesn't exist anymore, switch to whatever
        // page is the last one now
        this.setSelectedPage(new_pages.length-1);
      }
    },
  },

  computed: {
    num_pages() {
      return Math.ceil(this.num_items / this.items_per_page);
    },

    all_pages() {
      const num_pages = Math.ceil(this.num_items / this.items_per_page);
      let arr = [];
      for (let i = 0; i < num_pages; i++) {
        arr.push({num: i, start: i * this.items_per_page, end: Math.min((i+1)*this.items_per_page, this.num_items)});
      }

      return arr;
    },

    shown_pages() {
      if (this.all_pages.length > 5) {
        const slice_start = Math.max(this.selected_page_num - 1, 0);
        const slice_end = Math.min(slice_start + 3, this.all_pages.length);
        return this.all_pages.slice(slice_start, slice_end);
      }
      else {
        return this.all_pages;
      }
    },

    prev_tab_index() {
      if (this.selected_page_num === 0) {
        return "-1";
      } else {
        return "0";
      }
    },

    next_tab_index() {
      if (this.selected_page_num === (this.all_pages.length-1)) {
        return "-1";
      } else {
        return "0";
      }
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
      this.$emit('selected-page', this.all_pages[index].start, this.all_pages[index].end);
      this.$emit('selected-page-num', index);
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
    <ul class="pagination pagination-sm justify-content-center">
      <li class="page-item" v-if="all_pages.length > 5"
          :class="{disabled: selected_page_num === 0}">
        <a class="page-link" href="javascript:undefined"
            @click="setSelectedPage(0)">&lt;&lt;</a>
      </li>

      <li class="page-item" :class="{disabled: selected_page_num === 0}"
          :tabIndex="prev_tab_index">
        <a class="page-link" href="javascript:undefined" @click="selectPreviousPage">Previous</a>
      </li>

      <li class="page-item disabled" tabIndex="-1" aria-disabled="true"
          v-if="all_pages.length > 5 && selected_page_num > 0">
        <a class="page-link" href="javascript:undefined">...</a>
      </li>

      <li class="page-item" tabIndex="0" v-for="page in shown_pages" :key="page.num"
          :class="{active: selected_page_num === page.num}">
        <a class="page-link" href="javascript:undefined"
            @click="setSelectedPage(page.num)">[[page.num + 1]]</a>
      </li>

      <li class="page-item disabled" tabIndex="-1" aria-disbled="true"
          v-if="all_pages.length > 5 && selected_page_num < all_pages.length-1">
        <a class="page-link" href="javascript:undefined">...</a>
      </li>

      <li class="page-item" :class="{disabled: selected_page_num === (all_pages.length-1)}"
          :tabIndex="next_tab_index">
        <a class="page-link" href="javascript:undefined" @click="selectNextPage">Next</a>
      </li>

      <li class="page-item" v-if="all_pages.length > 5"
          :class="{disabled: selected_page_num === (all_pages.length-1)}">
        <a class="page-link" href="javascript:undefined"
            @click="setSelectedPage(all_pages.length-1)">&gt;&gt;</a>
      </li>
    </ul>
  </nav>
  `

};
