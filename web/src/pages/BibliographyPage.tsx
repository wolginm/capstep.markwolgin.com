/**
 * Bibliography: every source cited anywhere in the project, from
 * `references/references.yaml` (converted to JSON by `scripts/sync-data.ts`).
 * `?ref=ID` highlights and scrolls to one entry.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useSearchParams, https://reactrouter.com/start/declarative/routing
 *   [REACT-DOCS] useEffect, https://react.dev/reference/react/useEffect
 */

import { useEffect } from 'react'
import { useSearchParams } from 'react-router'
import { Loading } from '../components/Loading'
import { useSiteData } from '../lib/data'
import type { Reference } from '../lib/types'

/**
 * The `/bibliography` route.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useSearchParams, https://reactrouter.com/start/declarative/routing
 */
export function BibliographyPage() {
  const { references } = useSiteData()
  const [params] = useSearchParams()
  return (
    <>
      <h1>Bibliography</h1>
      <p className="lede">
        Every source this project uses or cites. In the code, each function’s documentation lists the sources it relies
        on by these IDs.
      </p>
      <Loading data={references}>{(refs) => <ReferenceList refs={refs} highlight={params.get('ref') ?? ''} />}</Loading>
    </>
  )
}

/**
 * The list of references, sorted by ID; the highlighted entry is scrolled into view.
 *
 * @references
 *   [REACT-DOCS] useEffect, https://react.dev/reference/react/useEffect
 */
function ReferenceList({ refs, highlight }: { refs: Reference[]; highlight: string }) {
  useEffect(() => {
    if (highlight) document.getElementById(`ref-${highlight}`)?.scrollIntoView?.({ block: 'center' })
  }, [highlight])
  const sorted = [...refs].sort((a, b) => a.id.localeCompare(b.id))
  return (
    <ol className="references">
      {sorted.map((ref) => (
        <li key={ref.id} id={`ref-${ref.id}`} className={ref.id === highlight ? 'highlight' : undefined}>
          <span className="ref-id">[{ref.id}]</span> {ref.author && <>{ref.author}. </>}
          <a href={ref.url}>{ref.title}</a>
          {ref.publisher && <>. {ref.publisher}</>}. Accessed {ref.accessed}.
          {ref.note && <span className="ref-note"> {ref.note}</span>}
        </li>
      ))}
    </ol>
  )
}
