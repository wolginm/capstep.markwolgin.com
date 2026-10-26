/**
 * Render a {@link Loadable} value: a status message while loading or on error,
 * otherwise the children.
 *
 * @references
 *   [WCAG-22] 4.1.3 Status Messages (role="status"), https://www.w3.org/TR/WCAG22/
 */

import type { ReactNode } from 'react'
import type { Loadable } from '../lib/data'

/**
 * Show loading/error states, or call `children` with the loaded value.
 *
 * @references
 *   [WCAG-22] 4.1.3 Status Messages, https://www.w3.org/TR/WCAG22/
 */
export function Loading<T>({ data, children }: { data: Loadable<T>; children: (value: T) => ReactNode }) {
  if (data.status === 'loading') return <p role="status">Loading…</p>
  if (data.status === 'error') {
    return (
      <p role="alert" className="error">
        Could not load site data ({data.message}). Please try again later.
      </p>
    )
  }
  return <>{children(data.value)}</>
}
