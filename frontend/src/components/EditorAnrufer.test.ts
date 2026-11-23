import {mount} from '@vue/test-utils'
import {describe, expect, it} from 'vitest'
import {reactive} from 'vue'
import {i18n} from '../i18n'
import {leererEntwurf, type Entwurf} from '../modell/szenarioentwurf'
import EditorAnrufer from './EditorAnrufer.vue'

describe('EditorAnrufer', () => {
    it('vergisst die angezeigte Nummer, sobald sie unterdrückt ist', async () => {
        const entwurf = reactive(leererEntwurf(1))
        const ansicht = mount(EditorAnrufer, {
            props: {modelValue: entwurf, 'onUpdate:modelValue': (wert: Entwurf) => ansicht.setProps({modelValue: wert})},
            global: {plugins: [i18n]},
        })
        await ansicht.get('input[type=tel]').setValue('030 1234567')
        await ansicht.get('input[type=checkbox]').setValue(true)
        const anrufer = (ansicht.props('modelValue') as Entwurf).anrufer
        expect(anrufer).toMatchObject({rufnummerUnterdrueckt: true, rufnummer: ''})
        expect(ansicht.findAll('input[type=tel]')).toHaveLength(1)
    })
})
