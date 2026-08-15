Component({
  properties: {
    diary: {
      type: Object,
      value: null
    }
  },

  methods: {
    handleSelect() {
      if (this.data.diary && this.data.diary.id) {
        this.triggerEvent('select', { diaryId: this.data.diary.id })
      }
    }
  }
})
