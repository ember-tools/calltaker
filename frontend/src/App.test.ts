import {useHead} from '@unhead/vue'
import {flushPromises, mount} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
import {createMemoryHistory, createRouter} from 'vue-router'
import App from './App.vue'
import {i18n} from './i18n'

/** A public page that titles itself, as `usePage` does on the start and help pages. */
const PUBLIC_PAGE = {
    setup() {
        useHead({title: 'Set by the page'})
        return () => null
    },
}

/** An exercise page, which leaves its title to the shell. */
const EXERCISE_PAGE = {render: () => null}

/**
 * Mounts the application shell on one page. The new-build check finds no server and stays quiet.
 *
 * @param isPublic whether the page is one of the prerendered public pages
 * @returns the mounted shell
 */
async function shell(isPublic: boolean) {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
    const page = isPublic ? PUBLIC_PAGE : EXERCISE_PAGE
    const router = createRouter({history: createMemoryHistory(), routes: [{path: '/', component: page, meta: {public: isPublic}}]})
    await router.push('/')
    const app = mount(App, {global: {plugins: [i18n, router]}})
    await flushPromises()
    return app
}

/** The robots instruction the document carries right now, if any. */
function robots(): string | null | undefined {
    return document.querySelector('meta[name=robots]')?.getAttribute('content')
}

describe('App', () => {
    afterEach(() => vi.unstubAllGlobals())

    it('keeps an exercise page out of search engines and titles it with the application name', async () => {
        const app = await shell(false)
        await vi.waitFor(() => expect(robots()).toBe('noindex, nofollow'))
        expect(document.title).toBe('Calltaker')
        app.unmount()
        await vi.waitFor(() => expect(robots()).toBeUndefined())
    })

    it('leaves robots and the title of a public page to the page itself', async () => {
        const app = await shell(true)
        await vi.waitFor(() => expect(document.title).toBe('Set by the page'))
        expect(robots()).toBeUndefined()
        app.unmount()
    })
})
