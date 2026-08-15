const { getMoodForScore } = require('../../config/moods')

Component({
  properties: {
    value: {
      type: Number,
      value: 50,
      observer(value) {
        this.updateMood(value)
      }
    },
    surfaceColor: {
      type: String,
      value: '#FBF1E5'
    }
  },

  data: {
    mood: getMoodForScore(50),
    knobLeft: 50,
    knobTop: 27
  },

  lifetimes: {
    attached() {
      this.updateMood(this.properties.value)
    },

    ready() {
      this.measureArc()
    }
  },

  methods: {
    updateMood(value) {
      const position = this.positionForScore(value)
      this.setData({
        mood: getMoodForScore(value),
        knobLeft: position.left,
        knobTop: position.top
      })
    },

    measureArc(callback) {
      this.createSelectorQuery()
        .select('.mood-arc')
        .boundingClientRect((rect) => {
          this.arcRect = rect
          if (callback) callback()
        })
        .exec()
    },

    handleTouch(event) {
      const update = () => {
        if (!this.arcRect || !event.touches.length) return
        const touch = event.touches[0]
        const touchX = typeof touch.clientX === 'number' ? touch.clientX : touch.pageX
        const value = Math.round(
          Math.max(0, Math.min(1, (touchX - this.arcRect.left) / this.arcRect.width)) * 100
        )
        this.emitChange(value)
      }

      if (!this.arcRect) {
        this.measureArc(update)
        return
      }
      update()
    },

    positionForScore(value) {
      const normalized = Math.max(0, Math.min(100, Number(value)))
      const angle = Math.PI - (normalized / 100) * Math.PI
      return {
        left: 50 + Math.cos(angle) * 32,
        top: 95 - Math.sin(angle) * 66
      }
    },

    emitChange(value) {
      const mood = getMoodForScore(value)
      const position = this.positionForScore(value)
      this.setData({
        mood,
        knobLeft: position.left,
        knobTop: position.top
      })
      this.triggerEvent('change', {
        value,
        label: mood.label
      })
    }
  }
})
