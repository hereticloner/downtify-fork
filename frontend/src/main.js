import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index'
import { installRouteProgress } from './composables/useRouteProgress'
import { installViewTransitions } from './lib/viewTransitions'

import './index.css'
import './model/theme'

installRouteProgress(router)
installViewTransitions(router)

createApp(App).use(router).mount('#app')
