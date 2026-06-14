import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { toast } from '@/composables/useToast'
import 'vant/es/style/base.css'
import '@/styles/vant-theme.scss'
import '@/styles/global.scss'

const app = createApp(App)
app.use(router)
app.config.globalProperties.$toast = toast
app.mount('#app')
