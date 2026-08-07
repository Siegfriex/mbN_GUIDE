import type { LiveSession } from '../../entities/live-session'
import { toLiveSessionViewModel } from '../../features/projection-query'
import { useI18n } from '../../shared/i18n'
import type { Locale } from '../../shared/i18n'
import { Button, EmptyState } from '../../shared/ui'
import './live.css'

type LiveCommerceHubProps = {
  sessions: LiveSession[]
  locale: Locale
  onOpenSession: (session: LiveSession) => void
}

export function LiveCommerceHub({ sessions, locale, onOpenSession }: LiveCommerceHubProps) {
  const { t } = useI18n()
  if (sessions.length === 0) return <EmptyState title={t('live.noSessionsTitle')} description={t('live.noSessionsDescription')} />
  const label = (session: LiveSession) => t(`label.live.lifecycle.${session.lifecycle}`)

  return (
    <div className="live-surface">
      <section className="live-surface__section" aria-labelledby="popular-live-title">
        <header className="live-surface__heading"><h2 id="popular-live-title">지금 인기 라이브</h2></header>
        <div className="live-session-rail" aria-label={t('live.featured')}>
          {sessions.map((session) => {
            const viewModel = toLiveSessionViewModel(session, locale)
            return <article className="live-visual-card" key={session.id}>
              <div className="live-visual-card__media"><span className="live-visual-card__badge">{label(session)}</span><span>연결된 영상 없음</span></div>
              <div className="live-visual-card__body"><h3>{viewModel.title}</h3><p>{session.hostName}</p><p>{viewModel.provenanceLabel}</p><Button size="sm" variant="ghost" onClick={() => onOpenSession(session)}>{t('common.openSession')}</Button></div>
            </article>
          })}
        </div>
      </section>
      {sessions.slice(1).length ? <section className="live-surface__section" aria-labelledby="session-list-title">
        <header className="live-surface__heading"><h2 id="session-list-title">{t('live.allSessions')}</h2></header>
        <div className="live-session-list" aria-label={t('live.allSessions')}>
          {sessions.slice(1).map((session) => {
            const viewModel = toLiveSessionViewModel(session, locale)
            return (
              <article className="live-card" key={session.id}>
                <div className="live-card__meta"><span className="live-lifecycle-badge">{label(session)}</span><span>{t('live.host')}: {session.hostName}</span></div>
                <h3>{viewModel.title}</h3>
                <p>{viewModel.summary}</p>
                <p className="place-preview__provenance">{viewModel.provenanceLabel}</p>
                <Button variant="secondary" onClick={() => onOpenSession(session)}>{t('common.openSession')}</Button>
              </article>
            )
          })}
        </div>
      </section> : null}
    </div>
  )
}
