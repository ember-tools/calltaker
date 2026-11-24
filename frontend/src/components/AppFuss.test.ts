import {mount, RouterLinkStub} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {i18n} from '../i18n'
import AppFuss from './AppFuss.vue'

describe('AppFuss', () => {
    it('nennt Quelle, Urheber, Lizenz und die gebaute Fassung', () => {
        const ansicht = mount(AppFuss, {global: {plugins: [i18n], stubs: {RouterLink: RouterLinkStub}}})
        expect(ansicht.get('a').attributes('href')).toBe('https://github.com/rainbowdashlabs/calltaker')
        expect(ansicht.text()).toContain('© 2026 RainbowDashLabs and Contributor')
        expect(ansicht.text()).toContain('Licensed under AGPL-3.0')
        expect(ansicht.text()).toMatch(/Calltaker \S+ · built /)
        expect(ansicht.getComponent(RouterLinkStub).props('to')).toEqual({name: 'hilfe'})
    })
})
