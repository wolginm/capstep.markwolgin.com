/**
 * Entry point. HashRouter keeps the route in the URL hash, so deep links work on
 * GitHub Pages and any static host without server rewrite rules.
 *
 * @references
 *   [REACT-DOM-CREATEROOT] https://react.dev/reference/react-dom/client/createRoot
 *   [REACT-ROUTER-HASHROUTER] https://reactrouter.com/api/declarative-routers/HashRouter
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router'
import { AppRoutes } from './App'
import { DataProvider } from './components/DataProvider'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <DataProvider>
        <AppRoutes />
      </DataProvider>
    </HashRouter>
  </StrictMode>,
)
