const ConfirmationDialog = {
  compilerOptions: {
    delimiters: ["[[", "]]"]
  },

  props: {
    name: String,
  },

  emits: ['confirmed', 'cancelled'],

  data() {
    return {
    }
  },

  template: `
<!-- Confirmation Dialog Modal -->
<div class="modal fade" :id="name" tabindex="-1" :aria-labelledby="name + 'Label'" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" :id="name + 'Label'">Confirmation</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" @click="$emit('cancelled')"></button>
      </div>
      <div class="modal-body">
        <slot />
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="$emit('cancelled')">Cancel</button>
        <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="$emit('confirmed')">Confirm</button>
      </div>
    </div>
  </div>
</div>
  `,

};
