import { ref, isRef, unref, watchEffect } from './vue.esm-browser.js';
import { fetchOrRefresh } from './helpers.js';

export function useFilterableList(url, name, filter_func) {
  const all_data = ref([]);
  const filtered_data = ref([]);
  const error = ref(null);

  function doFetch() {
    all_data.value = [];
    error.value = [];
    
    fetchOrRefresh(unref(url), 'GET', '/auth/refresh')
      .then((res) => res.json())
      .then((json) => (all_data.value = json[name]))
      .catch((err) => (error.value = err));
  }

  function filterData() {
    filtered_data.value = all_data.value.filter(unref(filter_func));
  }

  if (isRef(url)) {
    // setup reactive re-fetch if input URL is a ref
    watchEffect(doFetch);
  } else {
    // otherwise, just fetch once
    // and avoid the overhead of a watcher
    doFetch();
  }

  watchEffect(filterData);

  return { all_data, filtered_data, error };
}

export function usePagination(all_items, items_per_page, selected_page) {
  const current_page = ref([]);

  function setPage() {
    const start = selected_page.value * items_per_page.value;
    const end = Math.min(start + items_per_page.value, all_items.value.length);

    if (start === 0 && end === 0) {
      // if start and end are both 0, then current page is an empty array
      current_page.value = [];
    }
    else if (start >= 0 && start < all_items.value.length) {
      // if the start and end are within bounds, set it!
      current_page.value = all_items.value.slice(start, end);
    }
  }

  watchEffect(setPage);

  return { current_page };
}
