/** The target times in seconds from answering, to CPR guidance and to a fire or rescue handover. */
export interface Zielzeiten {
    reanimation: number
    uebergabe: number
}

/**
 * A duration as minutes and seconds.
 *
 * @param sekunden the duration
 * @returns "m:ss", or "h:mm:ss" from an hour on
 */
export function dauer(sekunden: number): string {
    const ganz = Math.max(0, Math.floor(sekunden))
    const stunden = Math.floor(ganz / 3600)
    const minuten = Math.floor((ganz % 3600) / 60)
    const rest = String(ganz % 60).padStart(2, '0')
    return stunden ? `${stunden}:${String(minuten).padStart(2, '0')}:${rest}` : `${minuten}:${rest}`
}
