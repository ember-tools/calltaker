/**
 * The topics of the help center in reading order: the slug of each page and the catalogue key below
 * `hilfe.topics` that holds its title and description. `vite.config.ts` prerenders a page per slug.
 */
export const HELP_TOPICS = [
    {slug: 'erste-schritte', key: 'firstSteps'},
    {slug: 'notrufe-annehmen', key: 'takingCalls'},
    {slug: 'notrufabfrage', key: 'structuredQuery'},
    {slug: 'telefonreanimation', key: 'telephoneCpr'},
    {slug: 'ausbilder', key: 'trainer'},
    {slug: 'anrufer-spielen', key: 'playingTheCaller'},
    {slug: 'auswertung', key: 'debrief'},
    {slug: 'tipps', key: 'tips'},
] as const

/** The slug of a help topic. */
export type HelpSlug = (typeof HELP_TOPICS)[number]['slug']
