import { useSyncExternalStore } from 'react'
import { cn } from '../../shared/lib'
import { useI18n } from '../../shared/i18n'
import { navigate } from '../../app/router/navigation'

type NavigationItem = {
  href: '/guide' | '/discover' | '/live'
  labelKey: 'nav.guide' | 'nav.discover' | 'nav.live'
}

const navigationItems: NavigationItem[] = [
  { href: '/guide', labelKey: 'nav.guide' },
  { href: '/discover', labelKey: 'nav.discover' },
  { href: '/live', labelKey: 'nav.live' },
]

function subscribe(onStoreChange: () => void) {
  window.addEventListener('popstate', onStoreChange)
  return () => window.removeEventListener('popstate', onStoreChange)
}

function getPathname() {
  return window.location.pathname
}

export function PrimaryNavigation() {
  const pathname = useSyncExternalStore(subscribe, getPathname, () => '/guide')
  const { t } = useI18n()

  return (
    <nav className="primary-navigation" aria-label={t('nav.primary')}>
      {navigationItems.map((item) => {
        const isActive = pathname === item.href || (item.href === '/guide' && pathname.startsWith('/place/'))
        return (
          <button
            key={item.href}
            className={cn('primary-navigation__item', isActive && 'primary-navigation__item--active')}
            aria-current={isActive ? 'page' : undefined}
            onClick={() => navigate(item.href)}
          >
            {t(item.labelKey)}
          </button>
        )
      })}
    </nav>
  )
}
