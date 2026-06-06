export interface Entry {
  id: number
  created_at: string
  method: string
  scheme: string
  host: string
  path: string
  query?: string
  req_header?: Record<string, string[]>
  req_body?: string  // base64
  status_code?: number
  resp_header?: Record<string, string[]>
  resp_body?: string  // base64
  duration_ms?: number
  protocol: string
  tags?: string[]
  modified?: boolean
}

export interface Filter {
  method?: string
  host?: string
  search?: string
  protocol?: string
}

export interface Rule {
  id: number
  name: string
  enabled: boolean
  priority: number
  conditions: Condition[]
  action: 'passthrough' | 'modify' | 'block' | 'redirect'
  modifications?: Modification[]
  redirect_url?: string
}

export interface Condition {
  field: 'host' | 'path' | 'method' | 'header' | 'body'
  op: 'equals' | 'contains' | 'prefix' | 'regex'
  value: string
  negate?: boolean
}

export interface Modification {
  target: 'req_header' | 'resp_header' | 'req_body' | 'resp_body'
  key?: string
  value?: string
  operation: 'set' | 'delete' | 'replace' | 'append' | 'find_replace'
  find?: string
  replace?: string
}

export interface ReplayResult {
  entry_id: number
  status_code: number
  body?: string
  duration_ms: number
  error?: string
}
