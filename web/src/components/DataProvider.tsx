/**
 * Providers for the shared site data: `DataProvider` fetches the files once;
 * `StaticDataProvider` supplies fixed data for tests.
 *
 * @references
 *   [REACT-DOCS] Context providers, https://react.dev/reference/react/createContext
 *   [MDN-FETCH] Fetch API, https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
 */

import type { ReactNode } from 'react'
import { DataContext, useDataFile, type SiteData } from '../lib/data'
import type { Catalog, Reference } from '../lib/types'

const asJson = (response: Response) => response.json()
const asText = (response: Response) => response.text()

/**
 * Provide catalog, references and the AI-usage log to the app.
 *
 * @references
 *   [REACT-DOCS] Context providers, https://react.dev/reference/react/createContext
 */
export function DataProvider({ children }: { children: ReactNode }) {
  const catalog = useDataFile<Catalog>('catalog.json', asJson)
  const references = useDataFile<Reference[]>('references.json', asJson)
  const aiUsage = useDataFile<string>('AI_USAGE.md', asText)
  return <DataContext.Provider value={{ catalog, references, aiUsage }}>{children}</DataContext.Provider>
}

/**
 * Provide fixed data (for tests), skipping the network.
 *
 * @references
 *   [REACT-DOCS] Context providers, https://react.dev/reference/react/createContext
 */
export function StaticDataProvider({ value, children }: { value: SiteData; children: ReactNode }) {
  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

