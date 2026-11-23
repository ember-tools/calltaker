import type {Abfragegraph} from '../modell/abfragegraph'
import type {Szenario} from '../modell/szenario'
import {sichtVon, type Anruf, type AnrufSicht} from '../modell/uebung'
import {debrief, zeitenVon, type Gespraechszeiten} from './debrief'
import type {Bewertung, Urteil} from './typen'
import type {Zielzeiten} from './zeitbewertung'

/** An ended call with its truth, as the debrief and the overview take it. */
export interface Ausgewertet {
    anruf: AnrufSicht
    szenario: Szenario
    /** The target times to judge it by; the defaults when not given. */
    ziele?: Zielzeiten
}

/** One line of the overview: the call and how its main entries compare with the truth. */
export interface Uebersichtszeile {
    id: string
    titel: string
    code?: Bewertung
    adresse?: Bewertung
    punkt?: Bewertung
    rueckrufnummer?: Bewertung
    reanimation?: Bewertung
    uebergabe?: Bewertung
    /** The required instructions to the caller as given of due, judged by the worst of them. */
    anleitung?: Bewertung
    zeiten: Gespraechszeiten
    fehlend: number
}

/** The whole exercise in numbers. */
export interface Gesamt {
    anrufe: number
    beendet: number
    aufgelegt: number
    codeExakt: number
    codeNah: number
    /** Mean seconds from accepting to a code, over the calls that reached one. */
    mittelBisCode?: number
    /** Mean seconds from accepting to the handover, over the calls handed over. */
    mittelBisUebergabe?: number
}

const RANG: Record<Urteil, number> = {falsch: 4, offen: 3, teilweise: 2, richtig: 1, hinweis: 0}

/**
 * Several comparisons as one cell: the given text, judged by the worst verdict among them.
 *
 * @param feld the catalogue key the cell stands for
 * @param bewertungen the comparisons
 * @param ist the text to show
 * @returns the cell, or nothing without comparisons
 */
function zusammengefasst(feld: string, bewertungen: Bewertung[], ist: string): Bewertung | undefined {
    if (!bewertungen.length) return undefined
    const urteil = bewertungen.map(b => b.urteil).reduce((a, b) => (RANG[b] > RANG[a] ? b : a))
    return {feld, soll: '', ist, urteil}
}

/**
 * The instructions to the caller as one cell: required ones given of due, judged by the worst.
 *
 * @param bewertungen the instruction comparisons, corrections applied
 * @returns the cell, or nothing when none was due or given
 */
function anleitungen(bewertungen: Bewertung[]): Bewertung | undefined {
    const pflicht = bewertungen.filter(b => b.soll)
    const gegeben = pflicht.filter(b => b.urteil === 'richtig').length
    return zusammengefasst('bewertung.anleitung', bewertungen, `${gegeben}/${pflicht.length}`)
}

/**
 * One line of the overview for an ended call.
 *
 * @param graph the graph
 * @param eintrag the call with its truth
 * @returns the line
 */
export function zeileVon(graph: Abfragegraph, eintrag: Ausgewertet): Uebersichtszeile {
    const ergebnis = debrief(graph, eintrag.anruf, eintrag.szenario, eintrag.ziele)
    const alle = ergebnis.phasen.flatMap(p => p.bewertungen)
    const feld = (name: string) => alle.find(b => b.feld === `bewertung.${name}`)
    return {
        id: eintrag.anruf.id,
        titel: eintrag.szenario.titel,
        code: feld('code'),
        adresse: feld('adresse') ?? feld('objekt'),
        punkt: feld('punkt'),
        rueckrufnummer: feld('rueckrufnummer'),
        reanimation: feld('reanimation'),
        uebergabe: zusammengefasst('bewertung.uebergabe', alle.filter(b => b.feld.startsWith('bewertung.uebergabe')), feld('uebergabe')?.ist ?? ''),
        anleitung: anleitungen(alle.filter(b => b.feld === 'bewertung.anleitung')),
        zeiten: ergebnis.zeiten,
        fehlend: ergebnis.fehlend.length,
    }
}

/**
 * The exercise in numbers: calls, how they ended, how close the codes came, and the mean times
 * to a code and to the handover.
 *
 * @param anrufe every call of the exercise, as the role sees them
 * @param zeilen the overview lines of the ended calls
 * @returns the totals
 */
export function gesamtVon(anrufe: {zustand: string}[], zeilen: Uebersichtszeile[]): Gesamt {
    const mittel = (werte: (number | undefined)[]) => {
        const da = werte.filter((s): s is number => s !== undefined)
        return da.length ? Math.round(da.reduce((a, b) => a + b, 0) / da.length) : undefined
    }
    return {
        anrufe: anrufe.length,
        beendet: anrufe.filter(a => a.zustand === 'beendet').length,
        aufgelegt: anrufe.filter(a => a.zustand === 'aufgelegt').length,
        codeExakt: zeilen.filter(z => z.code?.stufe === 'exakt').length,
        codeNah: zeilen.filter(z => z.code?.stufe === 'protokoll' || z.code?.stufe === 'kategorie').length,
        mittelBisCode: mittel(zeilen.map(z => z.zeiten.code)),
        mittelBisUebergabe: mittel(zeilen.map(z => z.zeiten.uebergabe)),
    }
}

/**
 * The protocol of an exercise for download: every call with its truth, entries, times and, for
 * ended calls, the comparison with the truth.
 *
 * @param graph the graph
 * @param anrufe the trainer's calls
 * @param erstellt when the protocol is made
 * @param ziele the target times the calls are judged by
 * @returns the protocol as a plain object
 */
export function protokoll(graph: Abfragegraph, anrufe: Anruf[], erstellt: Date, ziele?: Zielzeiten) {
    return {
        format: 'calltaker-protokoll',
        version: 1,
        erstellt: erstellt.toISOString(),
        abfrageVersion: graph.meta.version,
        anrufe: anrufe.map(anruf => {
            const ansicht = sichtVon(anruf)
            const ausgewertet = anruf.zustand === 'beendet' ? debrief(graph, ansicht, anruf.szenario, ziele) : undefined
            return {
                ...anruf,
                zeiten: zeitenVon(ansicht),
                bewertung: ausgewertet?.phasen.map(p => ({phase: p.phase.id, bewertungen: p.bewertungen})),
                abzweigung: ausgewertet?.pfad.abzweigung,
                fehlend: ausgewertet?.fehlend,
            }
        }),
    }
}
