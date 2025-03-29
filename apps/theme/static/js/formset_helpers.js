function itemFormset() {
  return {
    showDeleteItemModal: false,
    itemToDelete: null,

    add() {
      const totalForms = document.getElementById('id_items-TOTAL_FORMS');
      const formIdx = totalForms.value;

      const template = document.getElementById('empty-form-template');
      const clone = template.content.cloneNode(true).firstElementChild;

      let html = clone.innerHTML
        .replace(/__prefix__/g, formIdx)
        .replace(/items-__prefix__/g, `items-${formIdx}`);

      clone.innerHTML = html;
      document.getElementById('formset-container').appendChild(clone);
      totalForms.value = parseInt(formIdx) + 1;

      // Scroll to bottom
      this.$nextTick(() => {
        const container = document.getElementById('formset-container');
        container.scrollTop = container.scrollHeight;
      });
    },

    triggerRemove(event) {
      this.itemToDelete = event.target.closest('.bill-item-block');
      this.showDeleteItemModal = true;
    },

    confirmRemove() {
      const block = this.itemToDelete;
      const deleteInput = block?.querySelector('input.delete-checkbox');

      if (deleteInput) {
        deleteInput.checked = true;
        block.style.display = 'none';
      } else {
        block?.remove();
      }

      this.showDeleteItemModal = false;
      this.itemToDelete = null;
    }
  };
}
