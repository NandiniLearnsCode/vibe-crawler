export type MatterStatus = 'Active' | 'At Risk' | 'Closed';
export type RiskSeverity = 'Critical' | 'High' | 'Medium' | 'Low';
export type MatterType = 'M&A Due Diligence' | 'Private Equity Roll-up' | 'Asset Sale';
export type MatterStage =
  | 'Initial Planning'
  | 'Confirmatory Diligence'
  | 'Negotiation'
  | 'Signing'
  | 'Closed';

export interface MatterMetrics {
  diligenceCompletion: number;
  highPriorityIssues: number;
  clientInputsNeeded: number;
  blockers: number;
  outstandingRequests: number;
  executiveSummaryRefreshed: string;
}

export interface MatterSummary {
  dealStatus: string;
  topRisks: string[];
  missingItems: string[];
  suggestedNextActions: string[];
}

export interface Matter {
  id: string;
  name: string;
  client: string;
  counterparty: string;
  matterType: MatterType;
  leadPartner: string;
  status: MatterStatus;
  stage: MatterStage;
  permissions: 'Internal only' | 'Restricted internal' | 'Client shared';
  teamMembers: string[];
  riskLevel: RiskSeverity;
  lastUpdated: string;
  metrics: MatterMetrics;
  summary: MatterSummary;
  workstreamIds: string[];
  riskIds: string[];
  artifactIds: string[];
  activityIds: string[];
  clientUpdateIds: string[];
  knowledgeAssetIds: string[];
}

export interface Workstream {
  id: string;
  matterId: string;
  name: 'Corporate' | 'IP' | 'Employment' | 'Regulatory' | 'Commercial Contracts';
  owner: string;
  collaborators: string[];
  completion: number;
  openIssues: number;
  flaggedRiskIds: string[];
  linkedArtifactIds: string[];
  linkedAIOutputs: string[];
  summary: string;
  checklist: {
    item: string;
    status: 'Complete' | 'In Progress' | 'Not Started' | 'Blocked';
  }[];
  matterImpactSynthesis: string;
}

export interface Risk {
  id: string;
  matterId: string;
  title: string;
  severity: RiskSeverity;
  workstreamIds: string[];
  affectedEntity: string;
  whyItMatters: string;
  evidenceArtifactIds: string[];
  aiExplanation: string;
  recommendedNextStep: string;
  clientInputNeeded: boolean;
}

export interface Artifact {
  id: string;
  matterId: string;
  workstreamId?: string;
  title: string;
  type: 'Document' | 'Agent Output' | 'Review Table' | 'Research Thread' | 'Memo';
  updatedAt: string;
  owner: string;
}

export interface ActivityEvent {
  id: string;
  matterId: string;
  workstreamId?: string;
  riskId?: string;
  actorType: 'AI Agent' | 'Associate' | 'Partner' | 'Client';
  actor: string;
  action: string;
  timestamp: string;
}

export interface ClientUpdate {
  id: string;
  matterId: string;
  title: string;
  detail: string;
  timestamp: string;
  visibility: 'client-safe';
}

export interface KnowledgeAsset {
  id: string;
  matterId: string;
  category:
    | 'Precedent'
    | 'Clause Language'
    | 'Checklist Template'
    | 'Memo Pattern'
    | 'Risk Pattern';
  title: string;
  description: string;
  confidentialityBoundary: string;
}
