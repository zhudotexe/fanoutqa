import { library } from '@fortawesome/fontawesome-svg-core'
import { faAngleLeft, faAngleRight, faFilter, faSort, faSortDown, faSortUp } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { createApp } from 'vue'
import App from './App.vue'

// ==== fontawesome ====
library.add(
  faAngleLeft,
  faAngleRight,
  faSort,
  faSortUp,
  faSortDown,
  faFilter
)

// ==== init ====
createApp(App).component('font-awesome-icon', FontAwesomeIcon).mount('#app')
