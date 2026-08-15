Component({
  data: {
    dragIndex: -1,
    dragTargetIndex: -1
  },

  properties: {
    images: {
      type: Array,
      value: []
    },
    maxCount: {
      type: Number,
      value: 3
    },
    disabled: {
      type: Boolean,
      value: false
    }
  },

  methods: {
    startDrag(event) {
      if (this.properties.disabled || this.properties.images.length < 2) return
      const dragIndex = Number(event.currentTarget.dataset.index)
      this.dragItemRects = null
      this.setData({ dragIndex, dragTargetIndex: dragIndex })
      if (wx.vibrateShort) wx.vibrateShort({ type: 'light' })
      wx.createSelectorQuery().in(this).selectAll('.image-item').boundingClientRect((rects) => {
        this.dragItemRects = rects || []
      }).exec()
    },

    moveDrag(event) {
      if (this.data.dragIndex < 0 || !this.dragItemRects || !event.touches.length) return
      const x = event.touches[0].clientX
      let targetIndex = this.data.dragTargetIndex
      let nearestDistance = Infinity
      this.dragItemRects.forEach((rect, index) => {
        const distance = Math.abs(x - (rect.left + rect.width / 2))
        if (distance < nearestDistance) {
          nearestDistance = distance
          targetIndex = index
        }
      })
      if (targetIndex !== this.data.dragTargetIndex) this.setData({ dragTargetIndex: targetIndex })
    },

    endDrag() {
      const fromIndex = this.data.dragIndex
      const toIndex = this.data.dragTargetIndex
      this.resetDrag()
      if (fromIndex >= 0 && toIndex >= 0 && fromIndex !== toIndex) {
        this.suppressPreview = true
        this.triggerEvent('reorder', { fromIndex, toIndex })
        setTimeout(() => { this.suppressPreview = false }, 200)
      }
    },

    cancelDrag() {
      this.resetDrag()
    },

    resetDrag() {
      this.dragItemRects = null
      this.setData({ dragIndex: -1, dragTargetIndex: -1 })
    },

    chooseImages() {
      if (this.properties.disabled) return
      const remaining = this.properties.maxCount - this.properties.images.length
      if (remaining <= 0) return
      wx.chooseMedia({
        count: remaining,
        mediaType: ['image'],
        sourceType: ['album', 'camera'],
        sizeType: ['compressed'],
        success: (result) => {
          this.triggerEvent('select', { files: result.tempFiles })
        }
      })
    },

    removeImage(event) {
      this.triggerEvent('remove', {
        localId: event.currentTarget.dataset.id
      })
    },

    retryImage(event) {
      this.triggerEvent('retry', {
        localId: event.currentTarget.dataset.id
      })
    },

    previewImage(event) {
      if (this.suppressPreview || this.data.dragIndex >= 0) return
      const localId = event.currentTarget.dataset.id
      const current = this.properties.images.find((image) => image.localId === localId)
      const urls = this.properties.images
        .map((image) => image.localPath)
        .filter(Boolean)
      if (!current || !current.localPath || !urls.length) return
      wx.previewImage({ current: current.localPath, urls })
    }
  }
})
