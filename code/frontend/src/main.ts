import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// md-editor-v3 样式（markdown 编辑器与预览，确认决策 D7）
import 'md-editor-v3/lib/style.css'
import 'md-editor-v3/lib/preview.css'
import '@/styles/theme.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
