/**
 * Vitest setup: jest-dom matchers (toBeInTheDocument, ...) and DOM cleanup.
 *
 * @references
 *   [JEST-DOM] `@testing-library/jest-dom/vitest`, https://github.com/testing-library/jest-dom
 *   [TESTING-LIBRARY-REACT] cleanup, https://testing-library.com/docs/react-testing-library/intro/
 */

import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())
