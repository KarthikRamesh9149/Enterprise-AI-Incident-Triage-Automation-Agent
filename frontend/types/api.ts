export type Role = "admin" | "incident_commander" | "engineer" | "viewer";

export type ApiRow = Record<string, string | number | boolean | null | object | object[]>;

export type User = {
  id: string;
  email: string;
  role: Role;
};

export type Incident = {
  id: string;
  title: string;
  description: string;
  service_id: string;
  severity: string;
  status: string;
  source: string;
  created_at: string;
  service?: ApiRow;
};

export type Tool = {
  id: string;
  name: string;
  description: string;
  permission_level: Role;
  risk_level: string;
  requires_approval: boolean;
  is_enabled: boolean;
};

