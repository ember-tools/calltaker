import {mount} from '@vue/test-utils'
import {describe, expect, it, vi} from 'vitest'
import {sucheAdressen} from '../api/adressen'
import {i18n} from '../i18n'
import {BIS_SITUATION} from '../modell/testgraph.test-hilfe'
import {schwersteErreichbare} from '../modell/abfrageweg'
import {anrufMit, GRAPH, zustandMit} from '../modell/ausbilder.test-hilfe'
import LiveAnsicht from './LiveAnsicht.vue'

vi.mock('./KarteLeaflet.vue', () => ({default: {template: '<div/>'}}))
vi.mock('../api/adressen', () => ({adresslisteVerfuegbar: vi.fn().mockResolvedValue(true), sucheAdressen: vi.fn().mockResolvedValue([])}))
vi.mock('../api/orte', () => ({sucheOrte: vi.fn().mockResolvedValue([])}))

/**
 * Mounts the live view for a state.
 *
 * @param zustand the trainer's state
 * @returns the mounted view
 */
function live(zustand: ReturnType<typeof zustandMit>) {
    return mount(LiveAnsicht, {props: {zustand, graph: GRAPH, schwerste: schwersteErreichbare(GRAPH), absicht: vi.fn().mockResolvedValue({})}, global: {plugins: [i18n], stubs: {RouterLink: true}}})
}

describe('LiveAnsicht', () => {
    it('spiegelt das laufende Gespräch nur lesend, mit dem, was gerade getippt wird', async () => {
        vi.useFakeTimers()
        const gespraech = anrufMit('g')
        gespraech.eintraege.anrufer = {name: 'Mehmet', rufnummerBestaetigt: false, rueckrufnummer: '0151 2'}
        gespraech.eintraege.abfrage.pfad = BIS_SITUATION.slice(0, 2)
        const zustand = zustandMit([anrufMit('alt', 'beendet'), gespraech])
        zustand.spiegel = {suche: 'Werders', wert: '8', trotzdem: true}
        const ansicht = live(zustand)
        await ansicht.setProps({zustand: {...zustand, spiegel: {...zustand.spiegel, suche: 'Werderstr'}}})
        await vi.advanceTimersByTimeAsync(1000)
        vi.useRealTimers()
        expect(sucheAdressen).not.toHaveBeenCalled()
        const spiegel = ansicht.get('section[aria-label="Live-Spiegel"]')
        expect(spiegel.find('[inert]').exists()).toBe(true)
        expect((spiegel.findAll('input').find(i => (i.element as HTMLInputElement).value === 'Mehmet'))).toBeDefined()
        expect(spiegel.text()).toContain('Adresssuche: „Werderstr“')
        expect(spiegel.findAll('input').some(i => (i.element as HTMLInputElement).value === '8')).toBe(true)
        expect(spiegel.findAll('input').some(i => (i.element as HTMLInputElement).value === '0151 2')).toBe(true)
        expect(ansicht.get('section[aria-label="Wahrheit"]').text()).toContain('Sturz g')
    })

    it('zeigt einen gewählten Anruf aus dem Protokoll ohne Spiegel', async () => {
        const ansicht = live(zustandMit([anrufMit('alt', 'aufgelegt'), anrufMit('neu', 'beendet')]))
        expect(ansicht.get('section[aria-label="Wahrheit"]').text()).toContain('Sturz neu')
        expect(ansicht.text()).toContain('aufgelegt nach 1:40')
        await ansicht.findAll('button').find(b => b.text().includes('Sturz alt'))!.trigger('click')
        expect(ansicht.get('section[aria-label="Wahrheit"]').text()).toContain('Sturz alt')
        expect(ansicht.find('section[aria-label="Live-Spiegel"]').exists()).toBe(false)
    })

    it('wechselt zum neu angenommenen Gespräch, auch wenn ein alter Anruf gewählt war', async () => {
        const alt = anrufMit('alt', 'beendet')
        const ansicht = live(zustandMit([alt, anrufMit('mitte', 'beendet')]))
        await ansicht.findAll('button').find(b => b.text().includes('Sturz alt'))!.trigger('click')
        expect(ansicht.get('section[aria-label="Wahrheit"]').text()).toContain('Sturz alt')
        await ansicht.setProps({zustand: zustandMit([alt, anrufMit('mitte', 'beendet'), anrufMit('neu')])})
        expect(ansicht.get('section[aria-label="Wahrheit"]').text()).toContain('Sturz neu')
    })
})
