/**
 * Site data context and hooks. The files are copied into `public/data/` by
 * `scripts/sync-data.ts`, loaded once by `<DataProvider>`, and read with `useSiteData()`.
 *
 * @references
 *   [MDN-FETCH] Fetch API, https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
 *   [VITE-ENV] import.meta.env.BASE_URL, https://vite.dev/guide/env-and-mode.html
 *   [REACT-DOCS] createContext, useContext, useEffect, useState, https://react.dev/reference/react
 */

import { createContext, useContext, useEffect, useState } from 'react'
import type { Catalog, Reference } from './types'

/** A value being loaded: still loading, loaded, or failed with a message. */
export type Loadable<T> = { status: 'loading' } | { status: 'ready'; value: T } | { status: 'error'; message: string }

export interface SiteData {
  catalog: Loadable<Catalog>
  references: Loadable<Reference[]>
  aiUsage: Loadable<string>
}

export const DataContext = createContext<SiteData | null>(null)

/**
 * URL of a file in `public/data/`, relative to the deployed base path.
 *
 * @references
 *   [VITE-ENV] BASE_URL, https://vite.dev/guide/env-and-mode.html
 *   [VITE-CONFIG] base, https://vite.dev/config/shared-options.html
 */
export function dataUrl(name: string): string {
  return `${import.meta.env.BASE_URL}data/${name}`
}

/**
 * Fetch one data file and track its loading state.
 *
 * @param name - File name in `public/data/`.
 * @param parse - Turns the response into the value (JSON or text).
 *
 * @references
 *   [MDN-FETCH] fetch, Response.ok, https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
 *   [REACT-DOCS] useEffect cleanup to ignore stale results, https://react.dev/reference/react/useEffect
 */
export function useDataFile<T>(name: string, parse: (response: Response) => Promise<T>): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ status: 'loading' })
  useEffect(() => {
    let active = true
    fetch(dataUrl(name))
      .then((response) => {
        if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`)
        return parse(response)
      })
      .then((value) => active && setState({ status: 'ready', value }))
      .catch((error: unknown) => active && setState({ status: 'error', message: String(error) }))
    return () => {
      active = false
    }
  }, [name, parse])
  return state
}

/**
 * Read the shared site data. Must be used inside a provider.
 *
 * @references
 *   [REACT-DOCS] useContext, https://react.dev/reference/react/useContext
 */
export function useSiteData(): SiteData {
  const data = useContext(DataContext)
  if (!data) throw new Error('useSiteData must be used inside <DataProvider>')
  return data
}
