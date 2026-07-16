import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue')
      },
      {
        path: 'subjects',
        name: 'Subjects',
        component: () => import('../views/Subjects.vue')
      },
      {
        path: 'subjects/:id',
        name: 'SubjectConsole',
        component: () => import('../views/SubjectConsole.vue')
      },
      {
        path: 'assessment/:id',
        name: 'Assessment',
        component: () => import('../views/Assessment.vue')
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('../views/Upload.vue')
      },
      {
        path: 'analysis',
        name: 'Analysis',
        component: () => import('../views/Analysis.vue')
      },
      {
        path: 'analysis/status/:dimType/:statusValue',
        name: 'StatusDetail',
        component: () => import('../views/StatusDetail.vue')
      },
      {
        path: 'report/:id',
        name: 'Report',
        component: () => import('../views/Report.vue')
      },
      {
        path: 'stat-detail/:type',
        name: 'StatDetail',
        component: () => import('../views/StatDetail.vue')
      },
      {
        path: 'analysis/subjects',
        name: 'SubjectList',
        component: () => import('../views/SubjectList.vue')
      },
      {
        path: 'standard',
        name: 'Standard',
        component: () => import('../views/Standard.vue')
      },
      {
        path: 'help',
        name: 'Help',
        component: () => import('../views/Help.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router