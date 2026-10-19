export const CEPIO_V1_OPERATIONS = {
  getHealth: ["GET", "/api/v1/health"] as const,
  listObjects: ["GET", "/api/v1/objects"] as const,
  getObject: ["GET", "/api/v1/objects/{object_id}"] as const,
  upsertObject: ["PUT", "/api/v1/objects/{object_id}"] as const,
  queryObjects: ["POST", "/api/v1/query/objects"] as const,
  addRelationship: ["POST", "/api/v1/relationships"] as const,
  getNeighbors: ["GET", "/api/v1/objects/{object_id}/neighbors"] as const,
  getGraphBackend: ["GET", "/api/v1/graph/backend"] as const,
  getGraphCentrality: ["GET", "/api/v1/graph/centrality"] as const,
  getBlastRadius: ["GET", "/api/v1/graph/blast-radius/{object_id}"] as const,
  getGraphCommunities: ["GET", "/api/v1/graph/communities"] as const,
  recordEvent: ["POST", "/api/v1/events"] as const,
  listObjectEvents: ["GET", "/api/v1/objects/{object_id}/events"] as const,
  evaluateSkill: ["POST", "/api/v1/skills/evaluate"] as const,
  executeAction: ["POST", "/api/v1/actions"] as const,
  callFunction: ["POST", "/api/v1/functions/{name}"] as const,
  saveDecision: ["POST", "/api/v1/decisions"] as const,
  getDecision: ["GET", "/api/v1/decisions/{decision_id}"] as const,
  listAudit: ["GET", "/api/v1/audit"] as const,
};

export interface ObjectRef {
  id: string;
  type: string;
}

export interface OntologyObject {
  id: string;
  type: string;
  name: string;
  properties?: Record<string, unknown>;
  interfaces?: string[];
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Relationship {
  id?: string;
  type: string;
  source: ObjectRef;
  target: ObjectRef;
  properties?: Record<string, unknown>;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface OperationalEvent {
  id?: string;
  type: string;
  subject: ObjectRef;
  occurred_at?: string;
  severity?: string | null;
  properties?: Record<string, unknown>;
  source_system?: string | null;
}

export interface ObjectQueryResult {
  items: OntologyObject[];
  total: number | null;
  offset: number;
  limit: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface ActionRequest {
  action_type: string;
  target: ObjectRef;
  parameters?: Record<string, unknown>;
  correlation_id?: string | null;
  decision_id?: string | null;
}

export type EvidenceRole = "supporting" | "contradicting" | "contextual" | "assumption";

export interface EvidenceReference {
  object_ref: ObjectRef;
  role?: EvidenceRole;
  provenance_ref?: string | null;
}

export interface ContractMetadata {
  contract_version?: "0.2.0";
  correlation_id?: string | null;
}

export interface SkillInvocation {
  skill_id: string;
  subject: ObjectRef;
  parameters?: Record<string, unknown>;
  evidence?: EvidenceReference[];
  assessment_refs?: ObjectRef[];
  metadata?: ContractMetadata;
}

export interface SkillDecision {
  id: string;
  decision_type?: string | null;
  subject: ObjectRef;
  problem: string;
  observations?: string[];
  recommendation: string;
  recommended_action?: string | null;
  confidence?: number | null;
  created_by?: string | null;
}

export interface SkillEvaluation {
  skill_id: string;
  subject: ObjectRef;
  status: "completed" | "blocked" | "failed";
  recommendation?: string | null;
  outputs: Record<string, unknown>;
  evidence: EvidenceReference[];
  assessment_refs: ObjectRef[];
  decision?: SkillDecision | null;
  messages: string[];
  metadata: ContractMetadata;
}

export interface CEPIOClientOptions {
  accessToken?: string;
  devActor?: string;
  devRoles?: string[];
  fetchImpl?: typeof fetch;
}

export class CEPIOClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly fetchImpl: typeof fetch;

  constructor(baseUrl: string, options: CEPIOClientOptions = {}) {
    if (options.accessToken && (options.devActor || options.devRoles?.length)) {
      throw new Error("Use either an Entra access token or development identity headers, not both");
    }
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.headers = { Accept: "application/json" };
    if (options.accessToken) this.headers.Authorization = `Bearer ${options.accessToken}`;
    if (options.devActor) this.headers["X-CEPIO-Dev-Actor"] = options.devActor;
    if (options.devRoles?.length) this.headers["X-CEPIO-Dev-Roles"] = [...options.devRoles].sort().join(",");
  }

  private path(operationId: keyof typeof CEPIO_V1_OPERATIONS, params: Record<string, string> = {}): string {
    let value: string = CEPIO_V1_OPERATIONS[operationId][1];
    for (const [key, replacement] of Object.entries(params)) {
      value = value.replace(`{${key}}`, encodeURIComponent(replacement));
    }
    return value;
  }

  private async request<T>(
    operationId: keyof typeof CEPIO_V1_OPERATIONS,
    init: RequestInit = {},
    pathParams: Record<string, string> = {},
    query?: URLSearchParams,
  ): Promise<{ data: T; response: Response }> {
    const path = this.path(operationId, pathParams);
    const url = `${this.baseUrl}${path}${query && query.size ? `?${query.toString()}` : ""}`;
    const response = await this.fetchImpl(url, {
      ...init,
      headers: { ...this.headers, ...(init.headers ?? {}) },
    });
    if (!response.ok) {
      let detail: unknown;
      try { detail = await response.json(); } catch { detail = await response.text(); }
      throw new Error(`CEPIO ${response.status}: ${JSON.stringify(detail)}`);
    }
    const data = (await response.json()) as T;
    return { data, response };
  }

  async health(): Promise<Record<string, unknown>> {
    return (await this.request<Record<string, unknown>>("getHealth")).data;
  }

  async getObject(objectId: string): Promise<{ object: OntologyObject; etag: string | null }> {
    const { data, response } = await this.request<OntologyObject>("getObject", {}, { object_id: objectId });
    return { object: data, etag: response.headers.get("ETag") };
  }

  async upsertObject(object: OntologyObject, expectedVersion?: number): Promise<OntologyObject> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (expectedVersion !== undefined) headers["If-Match"] = `"${expectedVersion}"`;
    return (await this.request<OntologyObject>(
      "upsertObject",
      { method: "PUT", headers, body: JSON.stringify(object) },
      { object_id: object.id },
    )).data;
  }

  async listObjects(objectType?: string): Promise<OntologyObject[]> {
    const query = new URLSearchParams();
    if (objectType) query.set("object_type", objectType);
    return (await this.request<OntologyObject[]>("listObjects", {}, {}, query)).data;
  }

  async queryObjects(queryBody: Record<string, unknown>): Promise<ObjectQueryResult> {
    return (await this.request<ObjectQueryResult>("queryObjects", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(queryBody),
    })).data;
  }

  async addRelationship(relationship: Relationship): Promise<Relationship> {
    return (await this.request<Relationship>("addRelationship", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(relationship),
    })).data;
  }

  async neighbors(objectId: string, relationshipType?: string): Promise<OntologyObject[]> {
    const query = new URLSearchParams();
    if (relationshipType) query.set("relationship_type", relationshipType);
    return (await this.request<OntologyObject[]>("getNeighbors", {}, { object_id: objectId }, query)).data;
  }

  async graphBackend(): Promise<Record<string, unknown>> {
    return (await this.request<Record<string, unknown>>("getGraphBackend")).data;
  }

  async graphCentrality(params: Record<string, string | number> = {}): Promise<Record<string, unknown>> {
    const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
    return (await this.request<Record<string, unknown>>("getGraphCentrality", {}, {}, query)).data;
  }

  async blastRadius(objectId: string, params: Record<string, string | number> = {}): Promise<Record<string, unknown>> {
    const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
    return (await this.request<Record<string, unknown>>("getBlastRadius", {}, { object_id: objectId }, query)).data;
  }

  async graphCommunities(params: Record<string, string> = {}): Promise<Record<string, unknown>> {
    const query = new URLSearchParams(Object.entries(params));
    return (await this.request<Record<string, unknown>>("getGraphCommunities", {}, {}, query)).data;
  }

  async recordEvent(event: OperationalEvent): Promise<OperationalEvent> {
    return (await this.request<OperationalEvent>("recordEvent", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(event),
    })).data;
  }

  async eventsFor(objectId: string): Promise<OperationalEvent[]> {
    return (await this.request<OperationalEvent[]>("listObjectEvents", {}, { object_id: objectId })).data;
  }

  async evaluateSkill(invocation: SkillInvocation): Promise<SkillEvaluation> {
    return (await this.request<SkillEvaluation>("evaluateSkill", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(invocation),
    })).data;
  }

  async executeAction(action: ActionRequest, idempotencyKey?: string): Promise<Record<string, unknown>> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return (await this.request<Record<string, unknown>>("executeAction", {
      method: "POST", headers, body: JSON.stringify(action),
    })).data;
  }

  async callFunction(name: string, argumentsBody: Record<string, unknown>): Promise<unknown> {
    const result = (await this.request<{ result: unknown }>("callFunction", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ arguments: argumentsBody }),
    }, { name })).data;
    return result.result;
  }

  async saveDecision(decision: Record<string, unknown>): Promise<Record<string, unknown>> {
    return (await this.request<Record<string, unknown>>("saveDecision", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(decision),
    })).data;
  }

  async getDecision(decisionId: string): Promise<Record<string, unknown>> {
    return (await this.request<Record<string, unknown>>("getDecision", {}, { decision_id: decisionId })).data;
  }

  async audit(params: Record<string, string> = {}): Promise<Record<string, unknown>[]> {
    const query = new URLSearchParams(Object.entries(params));
    return (await this.request<Record<string, unknown>[]>("listAudit", {}, {}, query)).data;
  }
}
