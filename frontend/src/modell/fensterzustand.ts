/** What the questioning window holds that is not an entry yet, so the trainer's mirror can show it. */
export interface Fensterzustand {
    /** The value being typed at an input node. */
    wert: string
    /** Whether the questioning was started before the location was set. */
    trotzdem: boolean
    /** Which toolbar panel is open. */
    offen: 'hilfe' | 'aufwertung' | 'abbruch' | null
    /** The reason being typed for cancelling. */
    grund: string
    /** The text typed into the search over many answers. */
    kachelsuche: string
    /** Whether the answers that do not fit the situation are shown too. */
    weitere: boolean
}

/**
 * The window's state before anything was typed.
 *
 * @returns the empty state
 */
export function leererFensterzustand(): Fensterzustand {
    return {wert: '', trotzdem: false, offen: null, grund: '', kachelsuche: '', weitere: false}
}
