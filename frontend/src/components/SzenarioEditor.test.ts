import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {i18n} from '../i18n'
import {schwersteErreichbare} from '../modell/abfrageweg'
import {antwortenAusPfad, leererEntwurf, type Entwurf} from '../modell/szenarioentwurf'
import {BIS_SITUATION, testgraph} from '../modell/testgraph.test-hilfe'
import SzenarioEditor from './SzenarioEditor.vue'

vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))
vi.mock('./KarteLeaflet.vue', () => ({default: {template: '<div/>'}}))

const graph = testgraph()

/**
 * A complete draft whose path stops at the age input while its target is still set.
 *
 * @returns the draft
 */
function vollstaendig(): Entwurf {
    return {
        ...leererEntwurf(1), titel: 'Sturz',
        anrufer: {name: 'A', rufnummerUnterdrueckt: false, rufnummer: '030 1234567', rueckrufnummer: ''},
        antworten: antwortenAusPfad(graph, BIS_SITUATION.slice(0, 2)), ziel: {knoten: 'p.e1', code: '17A01'},
    }
}

/**
 * Mounts the editor for a draft.
 *
 * @param entwurf the draft
 * @param fehler the server's refusal
 * @returns the mounted editor
 */
function editor(entwurf: Entwurf, fehler = '') {
    const ansicht = mount(SzenarioEditor, {
        props: {graph, schwerste: schwersteErreichbare(graph), befunde: [], fehler, hinweis: '', modelValue: entwurf, 'onUpdate:modelValue': (wert: Entwurf) => ansicht.setProps({modelValue: wert})},
        global: {plugins: [i18n]},
        attachTo: document.body,
    })
    return ansicht
}

describe('SzenarioEditor', () => {
    it('speichert erst, wenn nichts mehr fehlt', async () => {
        const ansicht = editor(leererEntwurf(1))
        const speichern = ansicht.findAll('button').find(b => b.text() === 'Speichern')!
        expect(speichern.attributes('disabled')).toBeDefined()
        expect(ansicht.text()).toContain('Noch offen: Titel, Name des Anrufers, Rufnummer, Code')
        await ansicht.get('form').trigger('submit')
        expect(ansicht.emitted('speichern')).toBeUndefined()
        ansicht.unmount()
    })

    it('speichert nicht, wenn in der Eingabe oder der Code-Suche Enter gedrückt wird', async () => {
        const ansicht = editor(vollstaendig())
        await ansicht.get('input[aria-label="Alter?"]').trigger('keydown', {key: 'Enter'})
        await ansicht.get('input[type=search]').setValue('17A')
        await ansicht.get('input[type=search]').trigger('keydown', {key: 'Enter'})
        expect(ansicht.emitted('speichern')).toBeUndefined()
        expect(ansicht.props('modelValue').ziel).toEqual({knoten: 'p.e1', code: '17A01'})
        ansicht.unmount()
    })

    it('zeigt die Ablehnung des Servers', () => {
        const ansicht = editor(vollstaendig(), 'ohne Unterdrückung ist eine Rufnummer Pflicht')
        expect(ansicht.get('[role=alert]').text()).toContain('Pflicht')
        ansicht.unmount()
    })
})
