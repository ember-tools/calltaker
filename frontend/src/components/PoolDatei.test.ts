import {flushPromises, mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import PoolDatei from './PoolDatei.vue'

/**
 * Uploads a file through the component's file field.
 *
 * @param ansicht the mounted component
 * @param inhalt the file's text
 */
async function hochladen(ansicht: ReturnType<typeof mount>, inhalt: string): Promise<void> {
    const feld = ansicht.get('input[type=file]')
    Object.defineProperty(feld.element, 'files', {value: [new File([inhalt], 'pool.json')], configurable: true})
    await feld.trigger('change')
    await flushPromises()
}

describe('PoolDatei', () => {
    it('lädt eine Pooldatei hoch und fasst das Ergebnis zusammen', async () => {
        const absicht = vi.fn().mockResolvedValue({befunde: {a: [], b: [{art: 'fehler'}]}})
        const ansicht = mount(PoolDatei, {props: {code: 'A-ABCDEF', absicht}, global: {plugins: [i18n]}})
        await ansicht.get('select').setValue('ersetzen')
        await hochladen(ansicht, '{"format": "calltaker-pool"}')
        expect(absicht).toHaveBeenCalledWith('pool.importieren', {datei: {format: 'calltaker-pool'}, modus: 'ersetzen'})
        expect(ansicht.get('[role=status]').text()).toBe('2 Szenarien übernommen. Davon mit Hinweisen zur Korrektur: 1.')
    })

    it('lehnt eine Datei ab, die kein JSON ist', async () => {
        const absicht = vi.fn()
        const ansicht = mount(PoolDatei, {props: {code: 'A-ABCDEF', absicht}, global: {plugins: [i18n]}})
        await hochladen(ansicht, 'kein json')
        expect(absicht).not.toHaveBeenCalled()
        expect(ansicht.get('[role=alert]').text()).toBe('Die Datei ist kein JSON.')
    })

    it('bietet den Pool zum Herunterladen an', () => {
        const ansicht = mount(PoolDatei, {props: {code: 'A-ABCDEF', absicht: vi.fn()}, global: {plugins: [i18n]}})
        expect(ansicht.get('a').attributes('href')).toBe('/api/uebung/A-ABCDEF/pool')
    })
})

describe('PoolDatei bei einem Szenario', () => {
    it('spricht von einem Szenario in der Einzahl', async () => {
        const absicht = vi.fn().mockResolvedValue({befunde: {a: []}})
        const ansicht = mount(PoolDatei, {props: {code: 'A-ABCDEFGH', absicht}, global: {plugins: [i18n]}})
        await hochladen(ansicht, '{}')
        expect(ansicht.get('[role=status]').text()).toBe('Ein Szenario übernommen.')
    })
})
