import { useEffect, useState } from 'react'
import type { LiveSession } from '../../entities/live-session'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Skeleton, StatusNotice } from '../../shared/ui'
import { navigate } from '../../app/router/navigation'
import { PrimaryNavigation } from '../../widgets/app-chrome'
import { LiveCommerceHub } from '../../widgets/live-commerce-hub'

export function LivePage() {
  const [sessions, setSessions] = useState<LiveSession[] | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const { locale } = useI18n()

  useEffect(() => {
    let isCurrent = true
    fixtureProjection.listLiveSessions()
      .then((result) => { if (isCurrent) { setSessions(result); setError(null); track('live_home_viewed', { source: 'fixture' }) } })
      .catch((nextError: Error) => isCurrent && setError(nextError))
    return () => { isCurrent = false }
  }, [])

  return <><main className="product-page"><header className="surface-header"><p className="eyebrow">LIVE</p><h1>Session status, not simulated presence</h1><p>There are no live viewer counts, chat participants, inventory values, or partner transactions in this fixture.</p></header><StatusNotice state="UNAVAILABLE" title="No live provider is connected">Session cards expose only declared fixture status.</StatusNotice>{sessions === null && !error ? <Skeleton className="guide-skeleton" /> : null}{error ? <StatusNotice state="ERROR" title="Live fixture loading failed">{error.message}</StatusNotice> : null}{sessions ? <LiveCommerceHub sessions={sessions} locale={locale} onOpenSession={(session) => navigate(`/live/${encodeURIComponent(session.id)}`)} /> : null}</main><PrimaryNavigation /></>
}
