import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import {zustandMit} from '../modell/ausbilder.test-hilfe'
import EngineParameterForm from './EngineParameterForm.vue'

describe('EngineParameterForm', () => {
    it('schickt geänderte Parameter und zeigt Ablehnungen', async () => {
        const absicht = vi.fn().mockRejectedValue(new Error('Die Geduld braucht min ≤ max.'))
        const ansicht = mount(EngineParameterForm, {props: {parameter: zustandMit([]).engine.parameter, absicht}, global: {plugins: [i18n]}})
        const feld = ansicht.findAll('input[type=number]').at(-1)!
        await feld.setValue(30)
        await feld.trigger('change')
        expect(absicht.mock.calls[0]![1]).toMatchObject({parameter: {geduldMax: 30}})
        await new Promise(r => setTimeout(r, 0))
        expect(ansicht.get('[role=alert]').text()).toContain('Geduld')
    })
})
