import {createRouter, createWebHistory, type RouteLocationNormalized, type RouteLocationRaw} from 'vue-router'
import {rolleVon} from '../api/uebung'
import AusbilderView from '../views/AusbilderView.vue'
import StartView from '../views/StartView.vue'
import DebriefView from '../views/DebriefView.vue'
import TraineeView from '../views/TraineeView.vue'
import UebersichtView from '../views/UebersichtView.vue'
import type {Rolle} from '../modell/uebung'

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
        return rolle === ziel.meta.rolle ? true : {name: rolle, params: {code}}
    } catch {
        return true
    }
}

/**
 * The routes of one role: its view, the debrief of a call, and the overview.
 *
 * @param rolle the role
 * @param kuerzel the path prefix of the role
 * @returns the routes
 */
function routenFuer(rolle: Rolle, kuerzel: string) {
    const meta = {rolle}
    return [
        {path: `/${kuerzel}/:code`, name: rolle, component: rolle === 'ausbilder' ? AusbilderView : TraineeView, props: true, meta, beforeEnter: passendeRolle},
        {path: `/${kuerzel}/:code/debrief/:anrufId`, name: `${rolle}-debrief`, component: DebriefView, props: (route: RouteLocationNormalized) => ({...route.params, rolle}), meta, beforeEnter: passendeRolle},
        {path: `/${kuerzel}/:code/uebersicht`, name: `${rolle}-uebersicht`, component: UebersichtView, props: (route: RouteLocationNormalized) => ({...route.params, rolle}), meta, beforeEnter: passendeRolle},
    ]
}

/** The application's routes: the start page, and per role the view, the debriefs and the overview. */
export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {path: '/', name: 'start', component: StartView},
        ...routenFuer('ausbilder', 'a'),
        ...routenFuer('trainee', 't'),
    ],
})
