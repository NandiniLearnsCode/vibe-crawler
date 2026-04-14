import type {
  ActivityEvent,
  Artifact,
  ClientUpdate,
  KnowledgeAsset,
  Matter,
  Risk,
  Workstream,
} from '../types/matter';

export const matters: Matter[] = [
  {
    id: 'matter-falcon',
    name: 'Project Falcon Acquisition',
    client: 'NorthPeak Capital',
    counterparty: 'Silver Ridge Software',
    matterType: 'M&A Due Diligence',
    leadPartner: 'Sarah Chen',
    status: 'Active',
    stage: 'Confirmatory Diligence',
    permissions: 'Restricted internal',
    teamMembers: ['Sarah Chen', 'Michael Torres', 'Priya Nair', 'Daniel Kim', 'Emma Li'],
    riskLevel: 'High',
    lastUpdated: '10 minutes ago',
    metrics: {
      diligenceCompletion: 82,
      highPriorityIssues: 14,
      clientInputsNeeded: 3,
      blockers: 2,
      outstandingRequests: 9,
      executiveSummaryRefreshed: '2h ago',
    },
    summary: {
      dealStatus:
        'Confirmatory diligence remains on track for signing readiness pending targeted remediation on IP chain-of-title and customer contract consent exposures.',
      topRisks: [
        'Change-of-control consent triggers in top revenue contracts may delay close.',
        'Open-source license obligations create potential source code disclosure exposure.',
        'Employee invention assignment gaps create title uncertainty for two legacy modules.',
      ],
      missingItems: [
        'Signed invention assignment agreements for three senior engineers.',
        'Regulatory submission timeline confirmation from antitrust counsel.',
        'Executed customer consent waiver strategy for the top 12 accounts.',
      ],
      suggestedNextActions: [
        'Escalate customer consent workstream with client commercial lead this week.',
        'Prioritize remediation memo with outside IP specialist before investment committee review.',
        'Regenerate board-facing executive summary after blocker resolution.',
      ],
    },
    workstreamIds: [
      'ws-corporate',
      'ws-ip',
      'ws-employment',
      'ws-regulatory',
      'ws-commercial',
    ],
    riskIds: ['risk-coc-consent', 'risk-open-source', 'risk-ip-assignment', 'risk-reg-approval'],
    artifactIds: [
      'art-dd-request-list',
      'art-ip-diligence-memo',
      'art-commercial-review-table',
      'art-regulatory-thread',
      'art-exec-summary',
      'art-employment-gap-memo',
    ],
    activityIds: [
      'act-1',
      'act-2',
      'act-3',
      'act-4',
      'act-5',
      'act-6',
      'act-7',
      'act-8',
    ],
    clientUpdateIds: ['cu-1', 'cu-2', 'cu-3', 'cu-4'],
    knowledgeAssetIds: ['ka-1', 'ka-2', 'ka-3', 'ka-4', 'ka-5'],
  },
  {
    id: 'matter-orbit',
    name: 'Project Orbit Divestiture',
    client: 'Archer Industrial Group',
    counterparty: 'Helios Components',
    matterType: 'Asset Sale',
    leadPartner: 'Jonathan Reed',
    status: 'At Risk',
    stage: 'Negotiation',
    permissions: 'Internal only',
    teamMembers: ['Jonathan Reed', 'Lena Patel', 'Marcus Voss'],
    riskLevel: 'Medium',
    lastUpdated: '1 hour ago',
    metrics: {
      diligenceCompletion: 61,
      highPriorityIssues: 7,
      clientInputsNeeded: 4,
      blockers: 1,
      outstandingRequests: 11,
      executiveSummaryRefreshed: '6h ago',
    },
    summary: {
      dealStatus: 'Negotiation paused pending environmental disclosure reconciliation.',
      topRisks: ['Environmental indemnity carve-out remains unresolved.'],
      missingItems: ['Updated disclosure schedules from seller counsel.'],
      suggestedNextActions: ['Prepare fallback indemnity formulation for next draft.'],
    },
    workstreamIds: [],
    riskIds: [],
    artifactIds: [],
    activityIds: [],
    clientUpdateIds: [],
    knowledgeAssetIds: [],
  },
  {
    id: 'matter-summit',
    name: 'Summit Software Platform Roll-up',
    client: 'BlueHarbor Growth Partners',
    counterparty: 'Multiple Targets',
    matterType: 'Private Equity Roll-up',
    leadPartner: 'Alexandra Moss',
    status: 'Active',
    stage: 'Initial Planning',
    permissions: 'Restricted internal',
    teamMembers: ['Alexandra Moss', 'Noah Silva', 'Grace Miller'],
    riskLevel: 'Low',
    lastUpdated: '3 hours ago',
    metrics: {
      diligenceCompletion: 28,
      highPriorityIssues: 3,
      clientInputsNeeded: 5,
      blockers: 0,
      outstandingRequests: 18,
      executiveSummaryRefreshed: '4h ago',
    },
    summary: {
      dealStatus: 'Programmatic diligence playbook established for first two targets.',
      topRisks: ['Data room quality inconsistent across targets.'],
      missingItems: ['Target-specific compliance questionnaires.'],
      suggestedNextActions: ['Finalize unified request list and sequencing.'],
    },
    workstreamIds: [],
    riskIds: [],
    artifactIds: [],
    activityIds: [],
    clientUpdateIds: [],
    knowledgeAssetIds: [],
  },
];

export const workstreams: Workstream[] = [
  {
    id: 'ws-corporate',
    matterId: 'matter-falcon',
    name: 'Corporate',
    owner: 'Michael Torres',
    collaborators: ['Sarah Chen', 'Daniel Kim'],
    completion: 90,
    openIssues: 2,
    flaggedRiskIds: ['risk-coc-consent'],
    linkedArtifactIds: ['art-dd-request-list'],
    linkedAIOutputs: ['Corporate governance synthesis v6', 'Closing conditions tracker'],
    summary:
      'Cap table and governance records are largely reconciled; remaining issue is consent mechanics tied to control transfer provisions.',
    checklist: [
      { item: 'Charter and bylaws review', status: 'Complete' },
      { item: 'Board approvals mapping', status: 'Complete' },
      { item: 'Subsidiary minute books', status: 'In Progress' },
      { item: 'Intercompany obligations scan', status: 'Complete' },
    ],
    matterImpactSynthesis:
      'Corporate is mostly de-risked. Final consent mapping directly affects close certainty and signing timeline confidence.',
  },
  {
    id: 'ws-ip',
    matterId: 'matter-falcon',
    name: 'IP',
    owner: 'Priya Nair',
    collaborators: ['Daniel Kim', 'Emma Li'],
    completion: 76,
    openIssues: 5,
    flaggedRiskIds: ['risk-open-source', 'risk-ip-assignment'],
    linkedArtifactIds: ['art-ip-diligence-memo', 'art-employment-gap-memo'],
    linkedAIOutputs: ['IP diligence summary v9', 'Open-source obligations matrix'],
    summary:
      'Core codebase ownership is mostly documented, but licensing and assignment exceptions remain material before sign-off.',
    checklist: [
      { item: 'Code provenance mapping', status: 'Complete' },
      { item: 'Open-source dependency obligations', status: 'In Progress' },
      { item: 'Patent portfolio validity sweep', status: 'Complete' },
      { item: 'Employee invention assignment verification', status: 'Blocked' },
    ],
    matterImpactSynthesis:
      'IP findings are currently one of two principal blockers to deal certainty. Remediation path exists but requires client decision on indemnity posture.',
  },
  {
    id: 'ws-employment',
    matterId: 'matter-falcon',
    name: 'Employment',
    owner: 'Emma Li',
    collaborators: ['Priya Nair'],
    completion: 79,
    openIssues: 3,
    flaggedRiskIds: ['risk-ip-assignment'],
    linkedArtifactIds: ['art-employment-gap-memo'],
    linkedAIOutputs: ['Key employee retention risk snapshot'],
    summary:
      'Employee transfer package is stable; legacy invention assignment language creates overlap with IP ownership analysis.',
    checklist: [
      { item: 'Key personnel retention terms', status: 'In Progress' },
      { item: 'Invention assignment confirmation', status: 'Blocked' },
      { item: 'Compensation and benefits exposure', status: 'Complete' },
      { item: 'Litigation and claims review', status: 'Complete' },
    ],
    matterImpactSynthesis:
      'Employment issues are not independently deal-breaking but compound IP title risk if unresolved at signing.',
  },
  {
    id: 'ws-regulatory',
    matterId: 'matter-falcon',
    name: 'Regulatory',
    owner: 'Daniel Kim',
    collaborators: ['Sarah Chen'],
    completion: 68,
    openIssues: 2,
    flaggedRiskIds: ['risk-reg-approval'],
    linkedArtifactIds: ['art-regulatory-thread'],
    linkedAIOutputs: ['Regulatory dependency tracker v4'],
    summary:
      'No absolute prohibition identified; schedule risk remains due to unresolved filing dependency in one jurisdiction.',
    checklist: [
      { item: 'Antitrust filing threshold analysis', status: 'Complete' },
      { item: 'Sector-specific approvals map', status: 'In Progress' },
      { item: 'Cross-border transfer constraints', status: 'In Progress' },
      { item: 'Regulator engagement plan', status: 'Not Started' },
    ],
    matterImpactSynthesis:
      'Regulatory timing drives the outer bound for close date assumptions in the executive timeline and financing schedule.',
  },
  {
    id: 'ws-commercial',
    matterId: 'matter-falcon',
    name: 'Commercial Contracts',
    owner: 'Daniel Kim',
    collaborators: ['Michael Torres', 'Priya Nair'],
    completion: 85,
    openIssues: 2,
    flaggedRiskIds: ['risk-coc-consent'],
    linkedArtifactIds: ['art-commercial-review-table'],
    linkedAIOutputs: ['Customer contract consent digest'],
    summary:
      'Revenue concentration contracts are reviewed; consent triggers concentrated in top enterprise accounts require coordinated outreach strategy.',
    checklist: [
      { item: 'Top 25 revenue contract extraction', status: 'Complete' },
      { item: 'Change-of-control clause analysis', status: 'Complete' },
      { item: 'Assignment and anti-transfer provisions', status: 'In Progress' },
      { item: 'Consent outreach playbook', status: 'Not Started' },
    ],
    matterImpactSynthesis:
      'Commercial consent risk is directly linked to transaction certainty and may require repricing or condition precedent adjustment.',
  },
];

export const risks: Risk[] = [
  {
    id: 'risk-coc-consent',
    matterId: 'matter-falcon',
    title: 'Change-of-control clauses may trigger third-party consent requirements',
    severity: 'High',
    workstreamIds: ['ws-commercial', 'ws-corporate'],
    affectedEntity: 'Top 12 enterprise customer agreements',
    whyItMatters:
      'Failure to secure required consents before close could create immediate post-close breach exposure and revenue disruption.',
    evidenceArtifactIds: ['art-commercial-review-table', 'art-dd-request-list'],
    aiExplanation:
      'Review table extraction shows 7 contracts with strict anti-assignment language and no deemed-consent fallback. Combined annual contract value exceeds 42% of recurring revenue.',
    recommendedNextStep:
      'Run a client-approved consent outreach sequence and align fallback covenant language in the purchase agreement.',
    clientInputNeeded: true,
  },
  {
    id: 'risk-open-source',
    matterId: 'matter-falcon',
    title: 'Open-source licensing exposure in distributed product modules',
    severity: 'High',
    workstreamIds: ['ws-ip'],
    affectedEntity: 'Silver Ridge core orchestration engine',
    whyItMatters:
      'Copyleft obligations may require source code disclosure for derivative components if current architecture assumptions are incorrect.',
    evidenceArtifactIds: ['art-ip-diligence-memo'],
    aiExplanation:
      'Dependency scan identified AGPL components integrated into customer-facing deployment path without current segregation memo from engineering.',
    recommendedNextStep:
      'Obtain architecture confirmation from CTO and produce remediation carve-out language for reps and warranties.',
    clientInputNeeded: false,
  },
  {
    id: 'risk-ip-assignment',
    matterId: 'matter-falcon',
    title: 'Employee IP assignment gaps for legacy engineering hires',
    severity: 'Medium',
    workstreamIds: ['ws-ip', 'ws-employment'],
    affectedEntity: 'Legacy product modules from 2019-2020 development cycles',
    whyItMatters:
      'Missing assignment documentation can weaken title chain and reduce enforceability in a dispute scenario.',
    evidenceArtifactIds: ['art-employment-gap-memo', 'art-ip-diligence-memo'],
    aiExplanation:
      'Three former and current engineers lack fully executed invention assignment agreements for repositories tied to core product functionality.',
    recommendedNextStep:
      'Secure ratification agreements where possible and map residual exposure into indemnity package.',
    clientInputNeeded: true,
  },
  {
    id: 'risk-reg-approval',
    matterId: 'matter-falcon',
    title: 'Unresolved regulatory approval dependency may compress closing timeline',
    severity: 'Medium',
    workstreamIds: ['ws-regulatory'],
    affectedEntity: 'Data transfer authorization for one cross-border subsidiary',
    whyItMatters:
      'Delay in approval could shift financing and signing mechanics if long-stop date is not adjusted.',
    evidenceArtifactIds: ['art-regulatory-thread'],
    aiExplanation:
      'Counsel thread indicates submission packet remains incomplete pending target-side technical documentation.',
    recommendedNextStep:
      'Escalate submission readiness checklist with target counsel and align revised timing assumptions in transaction timeline.',
    clientInputNeeded: true,
  },
];

export const artifacts: Artifact[] = [
  {
    id: 'art-dd-request-list',
    matterId: 'matter-falcon',
    workstreamId: 'ws-corporate',
    title: 'Confirmatory diligence request list v12',
    type: 'Document',
    updatedAt: '35m ago',
    owner: 'Michael Torres',
  },
  {
    id: 'art-ip-diligence-memo',
    matterId: 'matter-falcon',
    workstreamId: 'ws-ip',
    title: 'IP diligence memo - ownership and licensing',
    type: 'Memo',
    updatedAt: '48m ago',
    owner: 'Priya Nair',
  },
  {
    id: 'art-commercial-review-table',
    matterId: 'matter-falcon',
    workstreamId: 'ws-commercial',
    title: 'Commercial contract review table - change of control',
    type: 'Review Table',
    updatedAt: '20m ago',
    owner: 'Daniel Kim',
  },
  {
    id: 'art-regulatory-thread',
    matterId: 'matter-falcon',
    workstreamId: 'ws-regulatory',
    title: 'Regulatory dependency research thread',
    type: 'Research Thread',
    updatedAt: '1h ago',
    owner: 'Daniel Kim',
  },
  {
    id: 'art-exec-summary',
    matterId: 'matter-falcon',
    title: 'Executive synthesis - matter status refresh',
    type: 'Agent Output',
    updatedAt: '2h ago',
    owner: 'Harvey Deal Synthesis Agent',
  },
  {
    id: 'art-employment-gap-memo',
    matterId: 'matter-falcon',
    workstreamId: 'ws-employment',
    title: 'Employee assignment gap analysis',
    type: 'Memo',
    updatedAt: '1h ago',
    owner: 'Emma Li',
  },
];

export const activities: ActivityEvent[] = [
  {
    id: 'act-1',
    matterId: 'matter-falcon',
    workstreamId: 'ws-ip',
    actorType: 'AI Agent',
    actor: 'IP Diligence Agent',
    action: 'Updated IP diligence summary with licensing exception analysis',
    timestamp: '12m ago',
  },
  {
    id: 'act-2',
    matterId: 'matter-falcon',
    workstreamId: 'ws-commercial',
    actorType: 'AI Agent',
    actor: 'Review Table Agent',
    action: 'Flagged change-of-control clause concentration in top 12 contracts',
    timestamp: '20m ago',
  },
  {
    id: 'act-3',
    matterId: 'matter-falcon',
    actorType: 'Associate',
    actor: 'Emma Li',
    action: 'Uploaded employee assignment gap memo to matter artifacts',
    timestamp: '58m ago',
  },
  {
    id: 'act-4',
    matterId: 'matter-falcon',
    actorType: 'Client',
    actor: 'NorthPeak Capital',
    action: 'Uploaded customer concentration worksheet to shared space',
    timestamp: '1h ago',
  },
  {
    id: 'act-5',
    matterId: 'matter-falcon',
    actorType: 'AI Agent',
    actor: 'Matter Synthesis Agent',
    action: 'Regenerated executive summary and risk ranking',
    timestamp: '2h ago',
  },
  {
    id: 'act-6',
    matterId: 'matter-falcon',
    workstreamId: 'ws-regulatory',
    actorType: 'Partner',
    actor: 'Sarah Chen',
    action: 'Marked regulatory filing dependency as blocker for close readiness',
    timestamp: '3h ago',
  },
  {
    id: 'act-7',
    matterId: 'matter-falcon',
    workstreamId: 'ws-corporate',
    actorType: 'Associate',
    actor: 'Michael Torres',
    action: 'Completed board approvals mapping checklist item',
    timestamp: '4h ago',
  },
  {
    id: 'act-8',
    matterId: 'matter-falcon',
    actorType: 'AI Agent',
    actor: 'Request Tracker Agent',
    action: 'Detected 9 unresolved diligence requests across workstreams',
    timestamp: '5h ago',
  },
];

export const clientUpdates: ClientUpdate[] = [
  {
    id: 'cu-1',
    matterId: 'matter-falcon',
    title: 'Diligence progress update',
    detail: 'Overall diligence is 82% complete and aligned to confirmatory timeline.',
    timestamp: '2h ago',
    visibility: 'client-safe',
  },
  {
    id: 'cu-2',
    matterId: 'matter-falcon',
    title: 'Client input required: contract consent strategy',
    detail:
      'Please confirm preferred outreach approach for counterparties requiring change-of-control consent.',
    timestamp: '90m ago',
    visibility: 'client-safe',
  },
  {
    id: 'cu-3',
    matterId: 'matter-falcon',
    title: 'Requested document',
    detail: 'Upload final CTO architecture memo supporting open-source segregation assumptions.',
    timestamp: '55m ago',
    visibility: 'client-safe',
  },
  {
    id: 'cu-4',
    matterId: 'matter-falcon',
    title: 'Timeline note',
    detail: 'Regulatory filing dependency may shift expected close window by 1-2 weeks.',
    timestamp: '40m ago',
    visibility: 'client-safe',
  },
];

export const knowledgeAssets: KnowledgeAsset[] = [
  {
    id: 'ka-1',
    matterId: 'matter-falcon',
    category: 'Precedent',
    title: 'Software acquisition consent escalation precedent',
    description:
      'Reusable transaction pathway for concentrated customer-consent risks in SaaS acquisitions.',
    confidentialityBoundary:
      'Firm-scoped abstracted pattern. No client-identifying contract terms are retained.',
  },
  {
    id: 'ka-2',
    matterId: 'matter-falcon',
    category: 'Clause Language',
    title: 'Open-source disclosure and remediation covenant package',
    description:
      'Preferred clause language for license exposure allocation and remediation obligations.',
    confidentialityBoundary:
      'Clause template captures legal pattern only and excludes client-specific negotiation context.',
  },
  {
    id: 'ka-3',
    matterId: 'matter-falcon',
    category: 'Checklist Template',
    title: 'Confirmatory diligence checklist - software target',
    description:
      'Refined checklist sequence for IP title, OSS obligations, and consent-critical contract diligence.',
    confidentialityBoundary:
      'Checklist logic retained at workflow level under ethical wall and matter-scoped controls.',
  },
  {
    id: 'ka-4',
    matterId: 'matter-falcon',
    category: 'Memo Pattern',
    title: 'Executive risk synthesis memo pattern',
    description:
      'Board-ready formatting pattern for translating multi-workstream legal findings into deal guidance.',
    confidentialityBoundary:
      'Format and structure only; factual deal details are excluded from reusable artifact.',
  },
  {
    id: 'ka-5',
    matterId: 'matter-falcon',
    category: 'Risk Pattern',
    title: 'Cross-workstream IP ownership + employment gap pattern',
    description:
      'Abstracted risk signature linking assignment gaps to ownership uncertainty in software M&A matters.',
    confidentialityBoundary:
      'Pattern-level metadata retained with firm-scoped learning enabled and strict client confidentiality boundaries.',
  },
];

export const getMatterById = (matterId: string) => matters.find((matter) => matter.id === matterId);

export const getWorkstreamsForMatter = (matterId: string) =>
  workstreams.filter((workstream) => workstream.matterId === matterId);

export const getRisksForMatter = (matterId: string) => risks.filter((risk) => risk.matterId === matterId);

export const getArtifactsForMatter = (matterId: string) =>
  artifacts.filter((artifact) => artifact.matterId === matterId);

export const getActivitiesForMatter = (matterId: string) =>
  activities.filter((activity) => activity.matterId === matterId);

export const getClientUpdatesForMatter = (matterId: string) =>
  clientUpdates.filter((update) => update.matterId === matterId);

export const getKnowledgeAssetsForMatter = (matterId: string) =>
  knowledgeAssets.filter((asset) => asset.matterId === matterId);
