import {createToolApp, emberboxUi} from '@emberbox/ui'
import {createWebHistory} from 'vue-router'
import App from './App.vue'
import {i18n} from './i18n'
import {createAppRouter, reloadOnStaleChunk} from './router'
import 'leaflet/dist/leaflet.css'
import './style.css'

const router = createAppRouter(createWebHistory())
reloadOnStaleChunk(router)
const app = createToolApp(App).use(router).use(i18n).use(emberboxUi)
void router.isReady().then(() => app.mount('#app'))
