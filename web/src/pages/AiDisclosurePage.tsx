/**
 * AI Disclosure: which LLM built this site and how. The body is `docs/AI_USAGE.md`,
 * rendered as Markdown, so the page and the repository log never disagree.
 *
 * @references
 *   [REACT-MARKDOWN] react-markdown (no dangerouslySetInnerHTML), https://github.com/remarkjs/react-markdown
 *   [REMARK-GFM] tables, https://github.com/remarkjs/remark-gfm
 */

import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Loading } from '../components/Loading'
import { useSiteData } from '../lib/data'

/**
 * The `/ai-disclosure` route.
 *
 * @references
 *   [REACT-MARKDOWN] https://github.com/remarkjs/react-markdown
 *   [REMARK-GFM] https://github.com/remarkjs/remark-gfm
 */
export function AiDisclosurePage() {
  const { aiUsage } = useSiteData()
  return (
    <div className="prose">
      <Loading data={aiUsage}>
        {(markdown) => <Markdown remarkPlugins={[remarkGfm]}>{markdown}</Markdown>}
      </Loading>
    </div>
  )
}
