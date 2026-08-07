import { useMemo, useState } from 'react'
import type { Place } from '../../entities/place'
import { getPlaceContent } from '../../entities/place'
import { fixtureProjection } from '../../features/projection-query'
import { track } from '../../shared/analytics'
import { useI18n } from '../../shared/i18n'
import { Button, EmptyState, StatusNotice } from '../../shared/ui'
import { createPlacePath, navigate } from '../../app/router/navigation'
import { PrimaryNavigation, UtilityNavigation } from '../../widgets/app-chrome'

type SearchRecord = { type: 'place'; item: Place }

const searchablePlaces = await fixtureProjection.listPlaces('all')
const searchableStories = await fixtureProjection.listStories()

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const { locale } = useI18n()
  const results = useMemo<SearchRecord[]>(() => {
    const normalized = submittedQuery.trim().toLocaleLowerCase()
    if (!normalized) return []
    return searchablePlaces.filter((place) => {
      const content = getPlaceContent(place, locale)
      return [content.name, content.summary, content.whyItMatters, ...place.tags].join(' ').toLocaleLowerCase().includes(normalized)
    }).map((item) => ({ type: 'place', item }))
  }, [locale, submittedQuery])

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmittedQuery(query)
    track('search_submitted', { queryLength: query.trim().length, scope: 'fixture-place-index', ignoredStoryCount: searchableStories.length })
  }

  return <><main className="product-page"><UtilityNavigation /><header className="surface-header"><p className="eyebrow">SEARCH</p><h1>Projection search</h1><p>Search only matches strings supplied by the fixture projection. It does not classify or rank data.</p></header><form className="search-form" onSubmit={submit}><label><span className="visually-hidden">Search fixtures</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search fixture places" /></label><Button type="submit">Search</Button></form>{submittedQuery ? <StatusNotice state="UNAVAILABLE" title="Fixture index only">No PY search index is consumed. Results are direct string matches in the local fixture projection.</StatusNotice> : null}{submittedQuery && results.length === 0 ? <EmptyState title="No matching fixture" description="This is an empty result, not an inferred recommendation." /> : null}{results.map(({ item }) => <article className="place-preview" key={item.id}><h2>{getPlaceContent(item, locale).name}</h2><p>{getPlaceContent(item, locale).summary}</p><Button variant="secondary" onClick={() => navigate(createPlacePath(item.id))}>Open place</Button></article>)}</main><PrimaryNavigation /></>
}
