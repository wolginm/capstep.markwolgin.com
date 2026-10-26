/**
 * Render the app (or any element) at a route, with fixed data instead of fetch.
 *
 * @references
 *   [TESTING-LIBRARY-REACT] render, https://testing-library.com/docs/react-testing-library/intro/
 *   [REACT-ROUTER-ROUTING] MemoryRouter for tests, https://reactrouter.com/start/declarative/routing
 */

import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { AppRoutes } from '../App'
import { StaticDataProvider } from '../components/DataProvider'
import { AI_USAGE, CATALOG, REFERENCES } from './fixtures'

/**
 * Render the full route table at `path` with the test catalog.
 *
 * @references
 *   [TESTING-LIBRARY-REACT] https://testing-library.com/docs/react-testing-library/intro/
 */
export function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <StaticDataProvider
        value={{
          catalog: { status: 'ready', value: CATALOG },
          references: { status: 'ready', value: REFERENCES },
          aiUsage: { status: 'ready', value: AI_USAGE },
        }}
      >
        <AppRoutes />
      </StaticDataProvider>
    </MemoryRouter>,
  )
}
