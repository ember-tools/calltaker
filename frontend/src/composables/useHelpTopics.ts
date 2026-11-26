import type {HelpTopicInfo} from '@emberbox/ui'
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {HELP_TOPICS} from '../helpTopics'

/**
 * The help topics with their titles and descriptions from the catalogue.
 *
 * @returns the topics in reading order
 */
export function useHelpTopics() {
    const {t} = useI18n()
    return computed<HelpTopicInfo[]>(() => HELP_TOPICS.map(topic => ({
        slug: topic.slug,
        title: t(`hilfe.topics.${topic.key}.title`),
        description: t(`hilfe.topics.${topic.key}.description`),
    })))
}

/**
 * Reads several help texts at once, by their catalogue keys below `hilfe`.
 *
 * @returns a function from keys to texts
 */
export function useHelpTexts() {
    const {t} = useI18n()
    return (...keys: string[]): string[] => keys.map(key => t(`hilfe.${key}`))
}
