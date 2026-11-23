import {createRouter, createWebHistory} from 'vue-router'
import StartView from '../views/StartView.vue'

/** The application's routes; every view of an exercise is added beside the start page. */
export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {path: '/', name: 'start', component: StartView},
    ],
})
