import {emberboxEslint} from '@emberbox/lint'

/**
 * Which layer may not reach which: the domain model, the API clients, the catalogue and the call
 * phases stand on nothing of the interface, and components and composables stand on no view.
 */
const LAYERS = [
    {layer: 'modell', above: ['views', 'components', 'composables', 'phasen', 'api']},
    {layer: 'api', above: ['views', 'components', 'composables', 'phasen']},
    {layer: 'i18n', above: ['views', 'components', 'composables', 'phasen', 'api']},
    {layer: 'phasen', above: ['views', 'components', 'composables']},
    {layer: 'composables', above: ['views', 'components']},
    {layer: 'components', above: ['views']},
]

export default await emberboxEslint({catalogue: 'src/i18n/de.ts', layers: LAYERS})
