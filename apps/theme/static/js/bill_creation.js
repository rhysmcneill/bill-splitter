// this handles bill creation, including OCR
function billFormHandler({ initialCount = 0, uploadUrl = '', csrfToken = '' }) {
  return {
    forms: Array.from({ length: initialCount }, () => ({
      _delete: false,
      name: '',
      price: '',
      nameError: '',
      priceError: '',
    })),
    loading: false,
    error: false,
    errorMessage: '',

    uploadReceipt(event) {
      const file = event.target.files[0];
      if (!file) return;

      this.loading = true;
      this.error = false;
      this.errorMessage = "";

      const formData = new FormData();
      formData.append("receipt", file);

      fetch(uploadUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
        },
        body: formData
      })
      .then(async response => {
        const data = await response.json();
        this.loading = false;

        if (!response.ok) {
          this.errorMessage = data.error || "Unexpected error occurred during receipt processing.";
          this.error = true;
          return;
        }

        if (data.items && Array.isArray(data.items) && data.items.length > 0) {
          this.forms = data.items
            .filter(item => item.description && item.price)
            .map(item => ({
              name: item.description,
              price: parseFloat(item.price).toFixed(2),
              _delete: false,
              nameError: '',
              priceError: ''
            }));
        } else {
          this.errorMessage = "OCR returned no valid items.";
          this.error = true;
        }
      })
      .catch(err => {
        console.error("OCR error:", err);
        this.loading = false;
        this.errorMessage = "There was a problem scanning the receipt.";
        this.error = true;
      });
    },



    add() {
      this.forms.push({
        _delete: false,
        name: '',
        price: '',
        nameError: '',
        priceError: '',
      });

      this.$nextTick(() => {
        const container = document.getElementById('create-formset-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
          const inputs = container.querySelectorAll('.item-name-input');
          inputs[inputs.length - 1]?.focus();
        }
      });
    },

    remove(index) {
      this.forms.splice(index, 1);
    },

    validate() {
      let isValid = true;
      this.forms.forEach(form => {
        form.nameError = '';
        form.priceError = '';
        if (!form.name.trim()) {
          form.nameError = 'Name is required';
          isValid = false;
        }
        if (!form.price || parseFloat(form.price) <= 0) {
          form.priceError = 'Price must be a positive number';
          isValid = false;
        }
      });
      return isValid;
    },

    totalAmount() {
      return this.forms.reduce((sum, form) => {
        if (!form._delete && form.price) {
          const price = parseFloat(form.price);
          return sum + (isNaN(price) ? 0 : price);
        }
        return sum;
      }, 0).toFixed(2);
    }
  }
}

window.billFormHandler = billFormHandler;
