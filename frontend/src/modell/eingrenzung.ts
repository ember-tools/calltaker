import type {Abfragegraph, Antwort} from './abfragegraph'
import {aktuellerKnoten} from './abfrageweg'
import type {Schritteintrag} from './eintraege'

/** At most this many questions in a row are answered on their own. */
const MAX_AUTOMATIK = 20

/** What the opening found out about the person: the age, whether it is unknown, the sex. */
export interface Personangaben {
    alter?: number
    alterUnbekannt: boolean
    geschlecht?: 'w' | 'm'
}

/** A node's answers in the order offered: those that fit first, the rest under "weitere". */
export interface Ordnung {
    vorn: Antwort[]
    weitere: Antwort[]
}

/**
 * An age in years read from what was typed: the first number in it, "ungefähr 60" as 60, and an
 * age in months, weeks or days as 0, since babies count as under one year.
 *
 * @param text what was typed
 * @returns the age in years, or undefined when the text holds no number
 */
export function alterAus(text: string): number | undefined {
    const zahl = /(\d+)/.exec(text)
    if (!zahl) return undefined
    return /\b(monat|woche|tag)/i.test(text) ? 0 : Number(zahl[1])
}

/**
 * The person as the path so far describes them. The age is unknown only when its question was
 * answered with "unknown", that is left empty; a text without a number rules nothing out.
 *
 * @param graph the graph
 * @param pfad the path
 * @returns the age and sex found
 */
export function personAus(graph: Abfragegraph, pfad: Schritteintrag[]): Personangaben {
    const person = graph.meta.person
    if (!person) return {alterUnbekannt: false}
    const alter = pfad.find(schritt => schritt.knoten === person.alter_knoten)
    const geschlecht = pfad.find(schritt => schritt.knoten === person.geschlecht_knoten)?.antwort
    return {
        alter: alter?.wert ? alterAus(alter.wert) : undefined,
        alterUnbekannt: Boolean(alter) && !alter?.wert?.trim(),
        geschlecht: geschlecht ? person.geschlecht[geschlecht] : undefined,
    }
}

/**
 * Whether an answer fits the person: its age bounds hold the age, it is the "age unknown" answer
 * when the age is unknown, and its sex matches. What the path has not told yet does not count
 * against an answer.
 *
 * @param antwort the answer
 * @param person the person
 * @returns true when nothing known speaks against it
 */
export function passtZurPerson(antwort: Antwort, person: Personangaben): boolean {
    const grenze = antwort.alter
    if (grenze?.unbekannt && person.alter !== undefined) return false
    if (grenze && !grenze.unbekannt) {
        if (person.alterUnbekannt) return false
        if (person.alter !== undefined && ((grenze.min ?? 0) > person.alter || (grenze.max ?? Infinity) < person.alter)) return false
    }
    return !(antwort.geschlecht && person.geschlecht && antwort.geschlecht !== person.geschlecht)
}

/**
 * The answers of a node in the order the situation suggests. Rules of the graph put the answers
 * the earlier answers point to first, in their order; answers that do not fit the person move
 * under "weitere". Nothing is ever dropped, and if nothing would stay in front, all do.
 *
 * @param graph the graph
 * @param knotenId the node
 * @param pfad the path so far
 * @returns the answers in front and the further ones
 */
export function ordnen(graph: Abfragegraph, knotenId: string, pfad: Schritteintrag[]): Ordnung {
    const antworten = graph.knoten[knotenId]?.antworten ?? []
    const gegeben = new Map(pfad.map(schritt => [schritt.knoten, schritt.antwort]))
    const regeln = (graph.meta.eingrenzung ?? []).filter(regel => regel.knoten === knotenId
        && regel.wenn.every(bedingung => bedingung.antworten.includes(gegeben.get(bedingung.knoten) ?? '')))
    const namen = [...new Set(regeln.flatMap(regel => regel.zuerst))]
    const rang = (antwort: Antwort) => namen.findIndex(name => name === antwort.id || name === antwort.protokoll)
    const zuerst = regeln.length ? antworten.filter(a => rang(a) >= 0).sort((a, b) => rang(a) - rang(b)) : antworten
    const person = personAus(graph, pfad)
    const passend = zuerst.filter(antwort => passtZurPerson(antwort, person))
    const vorn = passend.length ? passend : zuerst.length ? zuerst : antworten
    return {vorn, weitere: antworten.filter(antwort => !vorn.includes(antwort))}
}

/**
 * The answer the person decides on their own: the only one left once age and sex have ruled out
 * the others. Nodes where the person rules nothing out, or leaves several answers, are asked.
 *
 * @param graph the graph
 * @param knotenId the node
 * @param pfad the path so far
 * @returns the answer's id, or undefined when the node has to be asked
 */
export function vonSelbst(graph: Abfragegraph, knotenId: string, pfad: Schritteintrag[]): string | undefined {
    const antworten = graph.knoten[knotenId]?.antworten ?? []
    const person = personAus(graph, pfad)
    const passend = antworten.filter(antwort => passtZurPerson(antwort, person))
    return passend.length === 1 && antworten.length > 1 ? passend[0]!.id : undefined
}

/**
 * A path continued by every question the person decides on their own, each marked as automatic.
 *
 * @param graph the graph
 * @param pfad the path so far
 * @returns the path with the automatic steps added
 */
export function mitAutomatik(graph: Abfragegraph, pfad: Schritteintrag[]): Schritteintrag[] {
    const weiter = [...pfad]
    for (let schritte = 0; schritte < MAX_AUTOMATIK; schritte++) {
        const knoten = aktuellerKnoten(graph, weiter).knoten
        const antwort = vonSelbst(graph, knoten, weiter)
        if (!antwort) break
        weiter.push({knoten, antwort, automatisch: true})
    }
    return weiter
}

/**
 * A path one step back: the automatic steps at its end go with the last step the trainee took.
 *
 * @param pfad the path
 * @returns the shorter path
 */
export function einenZurueck(pfad: Schritteintrag[]): Schritteintrag[] {
    let ende = pfad.length
    while (ende > 0 && pfad[ende - 1]!.automatisch) ende--
    return pfad.slice(0, Math.max(0, ende - 1))
}
