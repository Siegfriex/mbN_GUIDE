import type { LiveSession } from '../../entities/live-session'
import { getLiveContent } from '../../entities/live-session'
import { useI18n } from '../../shared/i18n'
import type { Locale } from '../../shared/i18n'
import { Button, EmptyState } from '../../shared/ui'

type LiveCommerceHubProps = {
  sessions: LiveSession[]
  locale: Locale
  onOpenSession: (session: LiveSession) => void
}

export function LiveCommerceHub({ sessions, locale, onOpenSession }: LiveCommerceHubProps) {
  const { t } = useI18n()
  if (sessions.length === 0) {
    return <EmptyState title={t('live.noSessionsTitle')} description={t('live.noSessionsDescription')} />
  }

  return (
    <section className="live-hub" aria-label={t('live.fixtureHub')}>
      {sessions.map((session) => {
        const content = getLiveContent(session, locale)
        return (
          <article className="live-card" key={session.id}>
            <div className="place-preview__meta"><span>{session.lifecycle.toUpperCase()}</span><span>{session.category}</span></div>
            <h2>{content.title}</h2>
            <p>{content.summary}</p>
            <p className="place-preview__provenance">{session.provenance.label[locale]}</p>
            <Button variant="secondary" onClick={() => onOpenSession(session)}>{t('common.openSession')}</Button>
          </article>
        )
      })}
    </section>
  )
}
