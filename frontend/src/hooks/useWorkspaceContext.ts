import { useOutletContext } from "react-router-dom";
import type { Workspace } from "../api/types";

export interface WorkspaceContext {
  workspace: Workspace;
  canWrite: boolean;
}

export function useWorkspaceContext(): WorkspaceContext {
  return useOutletContext<WorkspaceContext>();
}
