const MOODS = [
  { min: 0, max: 20, label: '低落', color: '#8F88C9' },
  { min: 21, max: 40, label: '平静', color: '#6EA7C8' },
  { min: 41, max: 60, label: '明亮', color: '#79A985' },
  { min: 61, max: 80, label: '愉悦', color: '#D69B58' },
  { min: 81, max: 100, label: '高亢', color: '#D87958' }
]

function getMoodForScore(score) {
  const normalizedScore = Math.max(0, Math.min(100, Number(score)))
  return MOODS.find((mood) => normalizedScore >= mood.min && normalizedScore <= mood.max)
    || MOODS[2]
}

module.exports = {
  MOODS,
  getMoodForScore
}
