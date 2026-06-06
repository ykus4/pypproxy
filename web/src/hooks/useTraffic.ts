import { useState, useEffect, useRef, useCallback } from 'react'
import type { Entry, Filter } from '../types'

interface UseTrafficResult {
  entries: Entry[]
  total: number
  loading: boolean
  error: string | null
  clear: () => Promise<void>
  filter: Filter
  setFilter: (filter: Filter) => void
}

function buildQueryString(filter: Filter): string {
  const params = new URLSearchParams({ limit: '200' })
  if (filter.method) params.set('method', filter.method)
  if (filter.host) params.set('host', filter.host)
  if (filter.search) params.set('search', filter.search)
  if (filter.protocol) params.set('protocol', filter.protocol)
  return params.toString()
}

function getWsUrl(): string {
  if (import.meta.env.DEV) {
    return 'ws://localhost:8081/ws'
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

export function useTraffic(): UseTrafficResult {
  const [entries, setEntries] = useState<Entry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>({})

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const fetchEntries = useCallback(async (currentFilter: Filter) => {
    setLoading(true)
    setError(null)
    try {
      const qs = buildQueryString(currentFilter)
      const res = await fetch(`/api/traffic?${qs}`)
      if (!res.ok) {
        throw new Error(`Failed to fetch traffic: ${res.status} ${res.statusText}`)
      }
      const data: { entries: Entry[]; total: number } = await res.json()
      if (mountedRef.current) {
        setEntries(data.entries ?? [])
        setTotal(data.total ?? 0)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Unknown error fetching traffic')
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  // Fetch whenever filter changes
  useEffect(() => {
    fetchEntries(filter)
  }, [filter, fetchEntries])

  // WebSocket connection (independent of filter — server sends all new entries)
  useEffect(() => {
    mountedRef.current = true

    function connect() {
      if (!mountedRef.current) return

      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return
        try {
          const entry: Entry = JSON.parse(event.data as string)
          setEntries((prev) => [entry, ...prev])
          setTotal((prev) => prev + 1)
        } catch {
          // ignore malformed messages
        }
      }

      ws.onerror = () => {
        if (!mountedRef.current) return
        setError('WebSocket error — live updates unavailable')
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        // Reconnect after 3 seconds
        reconnectTimerRef.current = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent reconnect on intentional close
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  const clear = useCallback(async () => {
    try {
      const res = await fetch('/api/clear', { method: 'POST' })
      if (!res.ok) {
        throw new Error(`Failed to clear traffic: ${res.status} ${res.statusText}`)
      }
      setEntries([])
      setTotal(0)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error clearing traffic')
    }
  }, [])

  return { entries, total, loading, error, clear, filter, setFilter }
}
