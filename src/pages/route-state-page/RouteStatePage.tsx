import { PrimaryNavigation } from '../../widgets/app-chrome'
import { StatusNotice } from '../../shared/ui'

type RouteStatePageProps = {
  routeName: string
}

export function RouteStatePage({ routeName }: RouteStatePageProps) {
  return (
    <>
      <main className="product-page route-state-page">
        <p className="eyebrow">M-2 in progress</p>
        <h1>{routeName}</h1>
        <StatusNotice state="UNAVAILABLE" title="No fixture projection is connected yet.">
          This route is reserved by the DOCS contract but has no data-backed UI in the current vertical slice.
        </StatusNotice>
      </main>
      <PrimaryNavigation />
    </>
  )
}
