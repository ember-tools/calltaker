import {createI18n} from 'vue-i18n'
import {de} from './de'

/** The single German catalogue; the application has no other language. */
export const i18n = createI18n({
    legacy: false,
    locale: 'de',
    fallbackLocale: 'de',
    messages: {de},
})
