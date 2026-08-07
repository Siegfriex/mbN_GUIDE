import type { PropsWithChildren } from 'react'
import { PageContainer, VisuallyHidden } from '../../shared/ui'

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <PageContainer as="main" id="main-content" className="app-shell__content" tabIndex={-1}>
        <VisuallyHidden>Application foundation</VisuallyHidden>
        {children}
      </PageContainer>
    </div>
  )
}
