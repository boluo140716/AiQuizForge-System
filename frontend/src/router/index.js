import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true },
    redirect: '/notes',
    children: [
      {
        path: 'notes',
        name: 'NoteList',
        component: () => import('@/views/NoteList.vue'),
      },
      {
        path: 'notes/new',
        name: 'NoteCreate',
        component: () => import('@/views/NoteEdit.vue'),
      },
      {
        path: 'notes/:id/edit',
        name: 'NoteEdit',
        component: () => import('@/views/NoteEdit.vue'),
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
      },
      {
        path: 'wrong-questions',
        name: 'WrongQuestions',
        component: () => import('@/views/WrongQuestions.vue'),
      },
      {
        path: 'quiz-history',
        name: 'QuizHistory',
        component: () => import('@/views/QuizHistory.vue'),
      },
      {
        path: 'quiz/:id',
        name: 'Quiz',
        component: () => import('@/views/Quiz.vue'),
      },
      {
        path: 'quiz/:id/review',
        name: 'QuizReview',
        component: () => import('@/views/QuizReview.vue'),
      },
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    next('/')
  } else {
    next()
  }
})

export default router
