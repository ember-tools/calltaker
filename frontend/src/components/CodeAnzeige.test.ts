import {flushPromises, mount} from '@vue/test-utils'
import {afterEach, describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import CodeAnzeige from './CodeAnzeige.vue'

describe('CodeAnzeige', () => {
    afterEach(() => {
        vi.useRealTimers()
        vi.unstubAllGlobals()
    })

    it('zeigt kurz, dass der Code kopiert wurde', async () => {
        vi.useFakeTimers()
        const writeText = vi.fn().mockResolvedValue(undefined)
        vi.stubGlobal('navigator', {clipboard: {writeText}})
        const ansicht = mount(CodeAnzeige, {props: {titel: 'Trainee-Code', code: 'T-1'}, global: {plugins: [i18n]}})
        await ansicht.get('button').trigger('click')
        await flushPromises()
        expect(writeText).toHaveBeenCalledWith('T-1')
        expect(ansicht.get('button').text()).toBe('Kopiert')
        expect(ansicht.get('[role=status]').text()).toBe('Kopiert')
        vi.advanceTimersByTime(1500)
        await flushPromises()
        expect(ansicht.get('button').text()).toBe('')
    })

    it('sagt, wenn das Kopieren nicht ging', async () => {
        vi.stubGlobal('navigator', {clipboard: {writeText: vi.fn().mockRejectedValue(new Error('verweigert'))}})
        const ansicht = mount(CodeAnzeige, {props: {titel: 'Trainee-Code', code: 'T-1'}, global: {plugins: [i18n]}})
        await ansicht.get('button').trigger('click')
        await flushPromises()
        expect(ansicht.get('button').text()).toBe('Nicht kopiert')
    })
})
