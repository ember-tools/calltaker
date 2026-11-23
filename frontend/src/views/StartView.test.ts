import {describe, expect, it} from 'vitest'
import {mount} from '@vue/test-utils'
import {i18n} from '../i18n'
import StartView from './StartView.vue'

describe('StartView', () => {
    it('zeigt den Namen der Anwendung', () => {
        const ansicht = mount(StartView, {global: {plugins: [i18n]}})
        expect(ansicht.text()).toContain('Calltaker')
    })
})
