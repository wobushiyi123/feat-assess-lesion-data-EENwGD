import { reactive } from 'vue'

const store = reactive({
  subjects: [
    {
      id: 'S001',
      name: '受试者A',
      gender: '男',
      age: 56,
      baselineDate: '2024-01-15',
      assessments: [
        {
          id: 'A001',
          date: '2024-02-15',
          targetLesions: [
            { name: '肺部病灶1', baselineSize: 30, currentSize: 22 },
            { name: '肺部病灶2', baselineSize: 25, currentSize: 18 }
          ],
          nonTargetLesions: [
            { name: '淋巴结', status: '持续存在' }
          ],
          newLesion: false,
          tumorMarkerNormal: true,
          result: null
        }
      ]
    },
    {
      id: 'S002',
      name: '受试者B',
      gender: '女',
      age: 48,
      baselineDate: '2024-01-20',
      assessments: [
        {
          id: 'A002',
          date: '2024-02-20',
          targetLesions: [
            { name: '肝脏病灶', baselineSize: 50, currentSize: 55 }
          ],
          nonTargetLesions: [],
          newLesion: true,
          tumorMarkerNormal: false,
          result: null
        }
      ]
    },
    {
      id: 'S003',
      name: '受试者C',
      gender: '男',
      age: 62,
      baselineDate: '2024-01-10',
      assessments: [
        {
          id: 'A003',
          date: '2024-02-10',
          targetLesions: [
            { name: '脑部病灶', baselineSize: 40, currentSize: 0 }
          ],
          nonTargetLesions: [
            { name: '骨转移', status: '消失' }
          ],
          newLesion: false,
          tumorMarkerNormal: true,
          result: null
        }
      ]
    }
  ],
  addSubject(subject) {
    this.subjects.push(subject)
  },
  getSubject(id) {
    return this.subjects.find(s => s.id === id)
  },
  addAssessment(subjectId, assessment) {
    const subject = this.getSubject(subjectId)
    if (subject) {
      subject.assessments.push(assessment)
    }
  },
  updateAssessment(subjectId, assessmentId, data) {
    const subject = this.getSubject(subjectId)
    if (subject) {
      const assessment = subject.assessments.find(a => a.id === assessmentId)
      if (assessment) {
        Object.assign(assessment, data)
      }
    }
  }
})

export default store