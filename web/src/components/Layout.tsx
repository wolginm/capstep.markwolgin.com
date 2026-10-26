/**
 * Page frame: skip link, header with navigation, main content, and the footer that
 * every page must carry (LLM disclosure and non-affiliation notice).
 *
 * @references
 *   [REACT-ROUTER-ROUTING] NavLink, Outlet, https://reactrouter.com/start/declarative/routing
 *   [WCAG-22] 2.4.1 Bypass Blocks (skip link), https://www.w3.org/TR/WCAG22/
 */

import type { MouseEvent } from 'react'
import { Link, NavLink, Outlet } from 'react-router'
import { LLM_FOOTER_TEXT, SITE_TITLE } from '../config'

const NAV = [
  { to: '/', label: 'Browse', end: true },
  { to: '/about', label: 'About' },
  { to: '/copyright', label: 'Copyright & takedown' },
  { to: '/bibliography', label: 'Bibliography' },
  { to: '/ai-disclosure', label: 'AI disclosure' },
]

/**
 * Footer shown on every page. Its first line is the developer-required statement that
 * the site was built primarily with an LLM, linking to the AI Disclosure page.
 *
 * @references
 *   None (wording from plan/PLAN.md §5, Phase 3, developer requirement 2026-10-25).
 */
export function Footer() {
  return (
    <footer className="site-footer">
      <p className="llm-notice">
        {LLM_FOOTER_TEXT} <Link to="/ai-disclosure">How this site was made</Link>
      </p>
      <p>
        Unofficial preservation index, not affiliated with the Capitol Steps. All rights belong to their holders.
        Audio streams directly from the Internet Archive’s Wayback Machine; this site hosts no recordings.{' '}
        <Link to="/copyright">Copyright &amp; takedown</Link>
      </p>
    </footer>
  )
}

/**
 * The shared layout route; pages render into the `<Outlet>`.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] layout routes and Outlet, https://reactrouter.com/start/declarative/routing
 *   [WCAG-22] 2.4.1 Bypass Blocks, https://www.w3.org/TR/WCAG22/
 */
export function Layout() {
  return (
    <>
      <a className="skip-link" href="#main" onClick={focusMain}>
        Skip to content
      </a>
      <header className="site-header">
        <Link to="/" className="site-title">
          {SITE_TITLE}
        </Link>
        <nav aria-label="Main">
          <ul>
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
      <Footer />
    </>
  )
}

/**
 * Move focus to the main region without changing the URL hash (which the router owns).
 *
 * @references
 *   [REACT-ROUTER-HASHROUTER] the hash holds the route, https://reactrouter.com/api/declarative-routers/HashRouter
 */
function focusMain(event: MouseEvent<HTMLAnchorElement>) {
  event.preventDefault()
  document.getElementById('main')?.focus()
}
