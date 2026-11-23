import type {Abfragegraph, Anleitung, Wenn} from './abfragegraph'
import type {Schritteintrag} from './eintraege'

/** What the questioning so far has found out, as the instructions' conditions read it. */
interface Stand {
    fachrichtung?: string
    protokolle: Set<string>
    gegeben: Map<string, string | undefined>
    kategorie?: string
}

/**
 * The state of a questioning for the instructions: its Fachrichtung, the protocols chosen, the
 * answers given and the category reached.
 *
 * @param graph the graph
 * @param pfad the path
 * @param kategorie the category of the result so far, if any
 * @returns the state
 */
function standAus(graph: Abfragegraph, pfad: Schritteintrag[], kategorie?: string): Stand {
    const gegeben = new Map(pfad.map(schritt => [schritt.knoten, schritt.antwort]))
    const protokolle = new Set(pfad.flatMap(schritt => {
        const antwort = graph.knoten[schritt.knoten]?.antworten?.find(a => a.id === schritt.antwort)
        return antwort?.protokoll ? [antwort.protokoll] : []
    }))
    return {fachrichtung: gegeben.get(graph.meta.wurzel), protokolle, gegeben, kategorie}
}

/**
 * Whether one set of conditions holds.
 *
 * @param wenn the conditions
 * @param stand the state of the questioning
 * @returns true when every condition it names holds
 */
function gilt(wenn: Wenn, stand: Stand): boolean {
    return (!wenn.fachrichtung || wenn.fachrichtung === stand.fachrichtung)
        && (!wenn.protokolle?.length || wenn.protokolle.some(protokoll => stand.protokolle.has(protokoll)))
        && (wenn.antworten ?? []).every(antwort => stand.gegeben.get(antwort.knoten) === antwort.antwort)
        && !(wenn.nicht ?? []).some(antwort => stand.gegeben.get(antwort.knoten) === antwort.antwort)
        && (!wenn.kategorien?.length || wenn.kategorien.some(kategorie => stand.kategorie?.startsWith(kategorie)))
}

/**
 * The instructions due now: those one of whose sets of conditions holds, without those another due
 * instruction rules out, the ones that must be given first, each group in catalogue order. While
 * the caller is not on site, only instructions marked for that are due.
 *
 * @param graph the graph with its catalogue
 * @param pfad the trainee's path
 * @param kategorie the category of the result so far, if any
 * @returns the due instructions
 */
export function faellige(graph: Abfragegraph, pfad: Schritteintrag[], kategorie?: string): Anleitung[] {
    const stand = standAus(graph, pfad, kategorie)
    const abwesend = (graph.meta.abwesend ?? []).some(antwort => stand.gegeben.get(antwort.knoten) === antwort.antwort)
    const dran = (graph.anleitungen ?? []).filter(anleitung => (!abwesend || anleitung.auchOhneVorOrt) && anleitung.wenn.some(wenn => gilt(wenn, stand)))
    const ausgeschlossen = new Set(dran.flatMap(anleitung => anleitung.schliesstAus ?? []))
    const bleiben = dran.filter(anleitung => !ausgeschlossen.has(anleitung.id))
    return [...bleiben.filter(a => a.pflicht), ...bleiben.filter(a => !a.pflicht)]
}
