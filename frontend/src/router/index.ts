import {createRouter, createWebHistory, type RouteLocationNormalized, type RouteLocationRaw} from 'vue-router'
import {rolleVon} from '../api/uebung'
import AusbilderView from '../views/AusbilderView.vue'
import StartView from '../views/StartView.vue'
import TraineeView from '../views/TraineeView.vue'

/**
 * Sends a code to the view of the role it stands for, so a trainee code never opens the trainer's
 * view nor the other way round. When the role cannot be asked, the view opens and says why.
 *
 * @param ziel the route being entered
 * @returns the route of the code's role, or true to enter as asked
 */
export async function passendeRolle(ziel: RouteLocationNormalized): Promise<RouteLocationRaw | true> {
    const code = String(ziel.params.code)
    try {
        const rolle = await rolleVon(code)
        return rolle === ziel.name ? true : {name: rolle, params: {code}}
    } catch {
        return true
    }
}

/** The application's routes: the start page, and the two views of an exercise by code. */
export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {path: '/', name: 'start', component: StartView},
        {path: '/a/:code', name: 'ausbilder', component: AusbilderView, props: true, beforeEnter: passendeRolle},
        {path: '/t/:code', name: 'trainee', component: TraineeView, props: true, beforeEnter: passendeRolle},
    ],
})
