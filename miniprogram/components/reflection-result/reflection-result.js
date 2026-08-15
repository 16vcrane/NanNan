Component({
  properties: {
    status: { type: String, value: 'pending' },
    content: { type: String, value: '' },
    canRetry: { type: Boolean, value: false },
    retrying: { type: Boolean, value: false }
  },

  methods: {
    handleRetry() {
      if (!this.data.retrying && this.data.canRetry) {
        this.triggerEvent('retry')
      }
    }
  }
})
