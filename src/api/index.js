import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  // 默认使用同源相对路径（空 baseURL），配合 vite.config.js 中的 /api 代理转发到后端。
  // 这样局域网设备只访问前端端口即可，无需为后端单独放行防火墙，也不存在跨域问题。
  // 如需直连某个后端地址，可在 .env 设置 VITE_API_URL=http://ip:port。
  baseURL: import.meta.env.VITE_API_URL ?? '',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
      ElMessage.error('登录已过期，请重新登录')
    } else {
      // 对 404 不弹窗（可能接口尚不可用，由页面自行处理空状态）
      const detail = error.response?.data?.detail
      if (error.response?.status !== 404) {
        ElMessage.error(detail || '请求失败')
      }
      console.warn('[API]', error.config?.method, error.config?.url, error.response?.status, detail)
    }
    return Promise.reject(error)
  }
)

// 认证API
export const authApi = {
  login: (username, password) => {
    return api.post('/api/auth/login', `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  register: (data) => api.post('/api/auth/register', data),
  getMe: () => api.get('/api/auth/me')
}

// 受试者API
export const subjectApi = {
  list: (params) => api.get('/api/subjects', { params }),
  get: (id, params) => api.get(`/api/subjects/${id}`, { params }),
  create: (data) => api.post('/api/subjects', data),
  update: (id, data) => api.put(`/api/subjects/${id}`, data),
  delete: (id) => api.delete(`/api/subjects/${id}`),
  // 一键下发质疑：导出受试者信息 + 各周期判断结果为 Excel（blob）
  exportQuery: (id, params) => api.get(`/api/subjects/${id}/export-query`, { params: { ...params, responseType: 'blob' } })
}

// 评估API
export const assessmentApi = {
  calculate: (data) => api.post('/api/assessments/calculate', data),
  create: (data) => api.post('/api/assessments', data),
  listBySubject: (subjectId, params) => api.get(`/api/assessments/subject/${subjectId}`, { params }),
  get: (id) => api.get(`/api/assessments/${id}`),
  delete: (id) => api.delete(`/api/assessments/${id}`),
  // 删除单个病灶（靶/非靶/新）
  deleteLesion: (type, assessmentId, lesionId) => {
    const map = {
      target: `/api/assessments/${assessmentId}/target-lesions/${lesionId}`,
      nonTarget: `/api/assessments/${assessmentId}/non-target-lesions/${lesionId}`,
      newLesion: `/api/assessments/${assessmentId}/new-lesions/${lesionId}`
    }
    return api.delete(map[type])
  }
}

// 智能分析API
export const analysisApi = {
  getTrend: (subjectId, batchId) => api.get(`/api/analysis/trend/${subjectId}`, { params: batchId ? { batch_id: batchId } : {} }),
  getStatistics: (batchId) => api.get('/api/analysis/statistics', { params: batchId ? { batch_id: batchId } : {} }),
  getBatches: () => api.get('/api/analysis/batches'),
  deleteBatch: (batchId) => api.delete(`/api/analysis/batches/${batchId}`),
  clearBatches: () => api.post('/api/analysis/batches/clear')
}

// 数据导入导出API
export const dataApi = {
  import: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/data/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  export: () => api.get('/api/data/export', { responseType: 'blob' })
}

export default api