import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import ChatApp from './new/ChatApp'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChatApp />
  </React.StrictMode>
)
