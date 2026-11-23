import {describe, expect, it, vi} from 'vitest'
import {nextTick, ref} from 'vue'
import {leererEntwurf} from '../modell/szenarioentwurf'
import type {Szenario} from '../modell/szenario'
import {testgraph} from '../modell/testgraph.test-hilfe'
import {usePoolEditor} from './usePoolEditor'

const gespeichert: Szenario = {...leererEntwurf(0), id: 'a', titel: 'Alt', ziel: {knoten: 'p.e1', code: '17A01'}, anrufer: {name: 'A', rufnummerUnterdrueckt: false, rufnummer: '49301'}}
const MELDUNGEN = {gezogen: 'gezogen'}

/**
 * An editor over a pool holding one stored scenario.
 *
 * @param absicht the intent sender
 * @returns the editor and its pool
 */
function editor(absicht = vi.fn().mockResolvedValue({})) {
    const pool = ref<Szenario[] | undefined>([gespeichert])
    return {pool, absicht, ...usePoolEditor(pool, ref({a: [{art: 'warnung' as const, meldung: 'x'}]}), ref(testgraph()), absicht, MELDUNGEN)}
}

describe('usePoolEditor', () => {
    it('legt Neues an und ersetzt Bestehendes für den aktuellen Graphen', async () => {
        const e = editor()
        e.neu()
        expect(e.entwurf.value?.abfrageVersion).toBe(1)
        await e.speichern()
        expect(e.absicht.mock.calls[0]![0]).toBe('pool.hinzufuegen')
        expect(e.entwurf.value).toBeNull()
        e.bearbeiten('a')
        expect(e.befunde.value).toHaveLength(1)
        await e.speichern()
        expect(e.absicht).toHaveBeenLastCalledWith('pool.ersetzen', {szenario: expect.objectContaining({id: 'a', titel: 'Alt', abfrageVersion: 1}) as unknown})
    })

    it('lässt den Editor bei einer Ablehnung offen und zeigt den Grund dort', async () => {
        const e = editor(vi.fn().mockRejectedValue(new Error('ohne Unterdrückung ist eine Rufnummer Pflicht')))
        e.bearbeiten('a')
        await e.speichern()
        expect(e.entwurf.value?.id).toBe('a')
        expect(e.fehler.value).toContain('Pflicht')
        expect(e.listenFehler.value).toBe('')
    })

    it('zeigt abgelehnte Listenaktionen an der Liste', async () => {
        const e = editor(vi.fn().mockRejectedValue(new Error('Dieses Szenario gibt es nicht.')))
        await e.verschieben('a', 0)
        expect(e.listenFehler.value).toBe('Dieses Szenario gibt es nicht.')
        expect(e.fehler.value).toBe('')
    })

    it('schließt den Editor, wenn sein Szenario entfernt wird', async () => {
        const e = editor()
        e.bearbeiten('a')
        await e.entfernen('a')
        expect(e.absicht).toHaveBeenCalledWith('pool.entfernen', {szenarioId: 'a'})
        expect(e.entwurf.value).toBeNull()
    })

    it('legt ein inzwischen gezogenes Szenario beim Speichern neu an', async () => {
        const e = editor()
        e.bearbeiten('a')
        e.pool.value = []
        await nextTick()
        expect(e.entwurf.value?.id).toBeUndefined()
        expect(e.hinweis.value).toBe('gezogen')
        await e.speichern()
        expect(e.absicht.mock.calls[0]![0]).toBe('pool.hinzufuegen')
    })

    it('öffnet nichts über einen geänderten Entwurf', () => {
        const e = editor()
        e.neu()
        e.entwurf.value!.titel = 'getippt'
        expect(e.ungespeichert.value).toBe(true)
        e.bearbeiten('a')
        expect(e.entwurf.value?.titel).toBe('getippt')
    })
})
