import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { I18nProvider } from './i18n.jsx'
import { ProfilProvider } from './profilContext.jsx'

// Saqlangan tema (yorug'/qorong'u)
const tema = localStorage.getItem('tema')
if (tema) document.documentElement.dataset.theme = tema

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <I18nProvider>
      <ProfilProvider>
        <App />
      </ProfilProvider>
    </I18nProvider>
  </StrictMode>,
)
