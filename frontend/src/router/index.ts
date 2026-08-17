import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/components/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/notes',
    name: 'Notebooks',
    component: () => import('@/components/NotebooksList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/notes/:notebookId',
    name: 'Notes',
    component: () => import('@/components/NotesList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/notes/:notebookId/:noteId',
    name: 'NoteEditor',
    component: () => import('@/components/NoteEditor.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    redirect: '/notes'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/notes'
  }
]

const router = createRouter({
  history: createWebHistory('/'),
  routes
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuth()
  auth.initAuth()

  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !auth.isAuthenticated.value) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && auth.isAuthenticated.value) {
    next({ name: 'Notebooks' })
  } else {
    next()
  }
})

export default router
