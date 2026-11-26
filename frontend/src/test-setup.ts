import {emberboxUi} from '@emberbox/ui'
import {createHead} from '@unhead/vue/client'
import {config} from '@vue/test-utils'

/** Tooltips need the provider of the app shell; a mounted component on its own shows their content plainly. */
const PLAIN_TOOLTIP = {template: '<slot/>'}

config.global.plugins.push(emberboxUi, createHead())
config.global.stubs = {...config.global.stubs, Tooltip: PLAIN_TOOLTIP, UTooltip: PLAIN_TOOLTIP}
