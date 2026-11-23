import type {Abfragegraph} from '../modell/abfragegraph'
import type {Szenario} from '../modell/szenario'
import {sichtVon, type Anruf, type AnrufSicht} from '../modell/uebung'
import {debrief, zeitenVon, type Gespraechszeiten} from './debrief'
import type {Bewertung} from './typen'

/** An ended call with its truth, as the debrief and the overview take it. */
export interface Ausgewertet {
    anruf: AnrufSicht
    szenario: Szenario
}

/** One line of the overview: the call and how its main entries compare with the truth. */
export interface Uebersichtszeile {
    id: string
    titel: string
    code?: Bewertung
    adresse?: Bewertung
    punkt?: Bewertung
    rueckrufnummer?: Bewertung
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
}

/**
 * One line of the overview for an ended call.
 *
 * @param graph the graph
 * @param eintrag the call with its truth
 * @returns the line
 */
export function zeileVon(graph: Abfragegraph, eintrag: Ausgewertet): Uebersichtszeile {
    const ergebnis = debrief(graph, eintrag.anruf, eintrag.szenario)
    const alle = ergebnis.phasen.flatMap(p => p.bewertungen)
    const feld = (name: string) => alle.find(b => b.feld === `bewertung.${name}`)
    return {
        id: eintrag.anruf.id,
        titel: eintrag.szenario.titel,
        code: feld('code'),
        adresse: feld('adresse') ?? feld('objekt'),
        punkt: feld('punkt'),
        rueckrufnummer: feld('rueckrufnummer'),
        zeiten: ergebnis.zeiten,
        fehlend: ergebnis.fehlend.length,
    }
}

/**
 * The exercise in numbers: calls, how they ended, how close the codes came, and the mean time
 * to a code.
 *
 * @param anrufe every call of the exercise, as the role sees them
 * @param zeilen the overview lines of the ended calls
 * @returns the totals
 */
export function gesamtVon(anrufe: {zustand: string}[], zeilen: Uebersichtszeile[]): Gesamt {
    const bisCode = zeilen.map(z => z.zeiten.code).filter((s): s is number => s !== undefined)
    return {
        anrufe: anrufe.length,
        beendet: anrufe.filter(a => a.zustand === 'beendet').length,
        aufgelegt: anrufe.filter(a => a.zustand === 'aufgelegt').length,
        codeExakt: zeilen.filter(z => z.code?.stufe === 'exakt').length,
        codeNah: zeilen.filter(z => z.code?.stufe === 'protokoll' || z.code?.stufe === 'kategorie').length,
        mittelBisCode: bisCode.length ? Math.round(bisCode.reduce((a, b) => a + b, 0) / bisCode.length) : undefined,
    }
}

/**
 * The protocol of an exercise for download: every call with its truth, entries, times and, for
 * ended calls, the comparison with the truth.
 *
 * @param graph the graph
 * @param anrufe the trainer's calls
 * @param erstellt when the protocol is made
 * @returns the protocol as a plain object
 */
export function protokoll(graph: Abfragegraph, anrufe: Anruf[], erstellt: Date) {
    return {
        format: 'calltaker-protokoll',
        version: 1,
        erstellt: erstellt.toISOString(),
        abfrageVersion: graph.meta.version,
        anrufe: anrufe.map(anruf => {
            const ansicht = sichtVon(anruf)
            const ausgewertet = anruf.zustand === 'beendet' ? debrief(graph, ansicht, anruf.szenario) : undefined
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
