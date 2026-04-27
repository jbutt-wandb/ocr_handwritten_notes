import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import EditorView from '../views/EditorView.vue'

const routes = [
  {
    path: '/',
    name: 'upload',
    component: UploadView
  },
  {
    path: '/editor',
    name: 'editor',
    component: EditorView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
