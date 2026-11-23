export type ApiErrorBody = {
  error: string;
  message: string;
  details?: { field: string; message: string }[];
};

export type ComponentStatus = { status: "ok" | "error"; detail: string };

export type HealthResponse = {
  status: "ok" | "degraded";
  app_name: string;
  version: string;
  environment: string;
  database: ComponentStatus;
  storage: ComponentStatus;
  exports: ComponentStatus;
};
