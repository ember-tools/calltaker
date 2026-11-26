import {createRouter, type RouteLocationNormalized, type RouteLocationRaw, type Router, type RouterHistory} from 'vue-router'
import {rolleVon} from '../api/uebung'
import StartView from '../views/StartView.vue'
import HilfeView from '../views/HilfeView.vue'
import {HELP_TOPICS} from '../helpTopics'
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
        {path: `/${kuerzel}/:code`, name: rolle, component: rolle === 'ausbilder' ? () => import('../views/AusbilderView.vue') : () => import('../views/TraineeView.vue'), props: true, meta, beforeEnter: passendeRolle},
        {path: `/${kuerzel}/:code/debrief/:anrufId`, name: `${rolle}-debrief`, component: () => import('../views/DebriefView.vue'), props: (route: RouteLocationNormalized) => ({...route.params, rolle}), meta, beforeEnter: passendeRolle},
        {path: `/${kuerzel}/:code/uebersicht`, name: `${rolle}-uebersicht`, component: () => import('../views/UebersichtView.vue'), props: (route: RouteLocationNormalized) => ({...route.params, rolle}), meta, beforeEnter: passendeRolle},
    ]
}

/**
 * The application's router: the public start page, the help overview and its topics, and per role the
 * view, the debriefs and the overview. The browser passes web history, the prerender memory history. An
 * unknown help topic leads to the overview, also from another topic, and a new page starts at the top.
 *
 * @param history the history to navigate in
 * @returns the router
 */
export function createAppRouter(history: RouterHistory) {
    const router = createRouter({
        history,
        routes: [
            {path: '/', name: 'start', component: StartView, meta: {public: true}},
            {path: '/hilfe', name: 'hilfe', component: HilfeView, meta: {public: true}},
            {path: '/hilfe/:slug', name: 'helpTopic', component: () => import('../views/HelpTopicView.vue'), props: true, meta: {public: true}},
            ...routenFuer('ausbilder', 'a'),
            ...routenFuer('trainee', 't'),
        ],
        scrollBehavior: (_to, _from, saved) => saved ?? {top: 0},
    })
    router.beforeEach(to => to.name !== 'helpTopic' || HELP_TOPICS.some(topic => topic.slug === to.params.slug) || {name: 'hilfe'})
    return router
}

/** How browsers word a view's code that could not be loaded. */
const STALE_CHUNK = /dynamically imported module|module script failed|Importing a module script/i

/**
 * Loads the target page anew when its view's code is gone. A tab left open across a deploy still
 * runs the old build, whose lazily loaded views no longer exist on the server; a full load brings
 * the current build instead of a navigation that silently does nothing. A page already at the
 * target is not loaded again, so a deploy missing its own chunks cannot start a reload loop.
 *
 * @param router the application's router
 */
export function reloadOnStaleChunk(router: Router): void {
    router.onError((error: unknown, to) => {
        const here = window.location.pathname + window.location.search + window.location.hash
        if (to.fullPath !== here && STALE_CHUNK.test(String((error as Error | undefined)?.message))) window.location.assign(to.fullPath)
    })
}
