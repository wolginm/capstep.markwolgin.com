/**
 * Fallback for unknown routes.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] catch-all `*` route, https://reactrouter.com/start/declarative/routing
 */

import { Link } from 'react-router'

/**
 * The `*` route.
 *
 * @references
 *   None.
 */
export function NotFoundPage() {
  return (
    <>
      <h1>Page not found</h1>
      <p>
        <Link to="/">Browse all recordings</Link>.
      </p>
    </>
  )
}
