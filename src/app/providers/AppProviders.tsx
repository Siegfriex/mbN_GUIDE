import type { PropsWithChildren } from 'react'
import { I18nProvider } from '../../shared/i18n'
import { ToastProvider } from '../../shared/ui'
import { AppErrorBoundary } from '../errors/AppErrorBoundary'
import { messages } from '../i18n/catalog'

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <AppErrorBoundary>
      <I18nProvider catalog={messages}>
        <ToastProvider>{children}</ToastProvider>
      </I18nProvider>
    </AppErrorBoundary>
  )
}
