/**
 * Routes. Pages render inside the shared {@link Layout} (header, footer).
 *
 * @references
 *   [REACT-ROUTER-ROUTING] Routes, Route, layout routes, https://reactrouter.com/start/declarative/routing
 */

import { Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { AboutPage } from './pages/AboutPage'
import { AiDisclosurePage } from './pages/AiDisclosurePage'
import { BibliographyPage } from './pages/BibliographyPage'
import { BrowsePage } from './pages/BrowsePage'
import { CopyrightPage } from './pages/CopyrightPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SongPage } from './pages/SongPage'

/**
 * The route table (the router itself is created in `main.tsx`, or by tests).
 *
 * @references
 *   [REACT-ROUTER-ROUTING] https://reactrouter.com/start/declarative/routing
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<BrowsePage />} />
        <Route path="song/:id" element={<SongPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="copyright" element={<CopyrightPage />} />
        <Route path="bibliography" element={<BibliographyPage />} />
        <Route path="ai-disclosure" element={<AiDisclosurePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
