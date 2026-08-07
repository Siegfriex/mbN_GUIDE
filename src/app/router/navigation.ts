export function navigate(to: string, options: { replace?: boolean } = {}) {
  const method = options.replace ? 'replaceState' : 'pushState'
  window.history[method](null, '', to)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function createPlacePath(placeId: string) {
  return `/place/${encodeURIComponent(placeId)}`
}
