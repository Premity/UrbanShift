import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { BottomNav, NavTab } from '../components/shared/BottomNav';
import { FileText, Building2, Briefcase, LayoutList } from 'lucide-react';
import {
  PlanSummaryCard,
  SchemeCard,
  JobCard,
  HousingCard,
  ChecklistItem
} from '../components/results/Cards';
import { FilteredOutPanel, FilteredOutItem } from '../components/results/FilteredOutPanel';
import { Drawer } from '../components/shared/Drawer';
import { Header } from '../components/shared/Header';
import { useTranslation } from 'react-i18next';

// ── Strip markdown to plain text for display ────────────────────────────────

function stripMarkdown(md: string): string {
  return md
    .replace(/^#{1,6}\s+/gm, '')       // headings
    .replace(/\*\*(.+?)\*\*/g, '$1')   // bold
    .replace(/\*(.+?)\*/g, '$1')       // italic
    .replace(/^\s*[-*]\s+/gm, '• ')   // bullet lists
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links → label only
    .replace(/\n{3,}/g, '\n\n')        // collapse blank lines
    .trim();
}

// ── Format a source name from url domain as fallback ───────────────────────

function domainLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

// ── Plan shape from backend ──────────────────────────────────────────────────

interface BackendPlan {
  schemes: BackendScheme[];
  jobs: BackendJobMatch[];
  housing: BackendHousing[];
  checklist: BackendChecklistItem[];
  citations: BackendCitation[];
  filtered_out: BackendFilteredOut[];
}

interface BackendScheme {
  scheme_id?: string;
  id?: string;
  scheme_name?: string;
  name?: string;
  top_benefits?: string;
  benefits_summary?: string;
  citation?: string;
  source_url?: string;
  source_name?: string;
  apply_link?: string;
  eligibility_status?: { eligible: boolean; reasons?: string[]; reason?: string };
  docs_required?: string[];
  level?: string;
  category?: string[];
}

interface BackendJobMatch {
  job: {
    id: string;
    title: string;
    employer?: string;
    pay_min?: number;
    pay_max?: number;
    source_url?: string;
    source?: string;
    area?: string;
    required_skills?: string[];
    worker_band?: number;
    scheme_link_id?: string;
    description_md?: string;
  };
  match_score: number;
  match_reason?: string;
  scheme_link?: string | null;
  citation?: string;
}

interface BackendHousing {
  id: string;
  name: string;
  area?: string;
  price_min?: number;
  price_max?: number;
  occupancy?: string;
  amenities?: string[];
  source_url?: string;
  source_name?: string;
  commute_to_jobs?: Array<{ job_id: string; job_title: string; area: string; commute_minutes: number }>;
  type?: string;
}

interface BackendChecklistItem {
  step?: number;
  text: string;
  category?: string;
  item_id?: string | null;
  citation?: string;
}

interface BackendCitation {
  source_url: string;
  source_name: string;
}

interface BackendFilteredOut {
  item_id: string;
  category: 'scheme' | 'job' | 'housing';
  reasons: string[];
}

// ── Adapters: backend → UI card props ────────────────────────────────────────

function adaptScheme(s: BackendScheme, idx: number) {
  const eligStatus = s.eligibility_status;
  // Default to 'check' for safety: only mark eligible when backend explicitly says so.
  let eligibilityStatus: 'eligible' | 'check' | 'ineligible' = 'eligible';
  let eligibilityReasons: string[] = [];
  if (eligStatus) {
    if (eligStatus.eligible) {
      eligibilityStatus = 'eligible';
    } else {
      eligibilityStatus = 'check';
      eligibilityReasons = eligStatus.reasons || (eligStatus.reason ? [eligStatus.reason] : []);
    }
  }

  const rawBenefits = s.top_benefits || s.benefits_summary || '';
  const benefitsSummary = stripMarkdown(rawBenefits);
  const sourceUrl = s.citation || s.source_url || s.apply_link || '';

  return {
    id: s.scheme_id || s.id || `s${idx}`,
    name: s.scheme_name || s.name || 'Unknown scheme',
    eligibilityStatus,
    eligibilityReasons,
    benefitsSummary,
    sourceUrl,
    sourceName: s.source_name || (sourceUrl ? domainLabel(sourceUrl) : ''),
    eligibilityCriteria: s.docs_required || [],
    howToApply: s.apply_link ? `Apply at ${s.apply_link}` : undefined,
    benefit: benefitsSummary,
  };
}

function adaptJob(j: BackendJobMatch, idx: number) {
  const job = j.job || {} as BackendJobMatch['job'];
  const sourceUrl = j.citation || job.source_url || '';
  // job.source is a short key like "ncs" — use domain as display label fallback
  const sourceName = job.source
    ? job.source.toUpperCase()
    : (sourceUrl ? domainLabel(sourceUrl) : '');

  return {
    id: job.id || `j${idx}`,
    title: job.title || 'Job opportunity',
    employer: job.employer || '',
    matchScore: j.match_score ?? 0,
    payMin: job.pay_min ?? null,
    payMax: job.pay_max ?? null,
    schemeLink: j.scheme_link || undefined,
    commuteMinutes: undefined,
    sourceUrl,
    sourceName,
    requirements: job.required_skills || [],
    howToApply: sourceUrl ? `Apply via ${sourceName || sourceUrl}` : undefined,
    matchReason: j.match_reason,
  };
}

function adaptHousing(h: BackendHousing, idx: number) {
  const bestCommute = h.commute_to_jobs?.[0]?.commute_minutes;
  const sourceUrl = h.source_url || '';
  const sourceName = h.source_name || (sourceUrl ? domainLabel(sourceUrl) : '');
  return {
    id: h.id || `h${idx}`,
    name: h.name || 'Housing option',
    area: h.area || '',
    occupancy: h.occupancy || '',
    priceMin: h.price_min,
    commuteMinutes: bestCommute,
    sourceUrl,
    sourceName,
    amenities: h.amenities || [],
    deposit: h.price_min ? `₹${h.price_min.toLocaleString()} (1 month)` : undefined,
    contact: sourceUrl ? `Listed on ${sourceName} — no broker fee.` : undefined,
  };
}

function adaptChecklist(items: BackendChecklistItem[]) {
  return items.map((item, idx) => {
    const url = item.citation || '';
    const isRealUrl = url.startsWith('http');
    return {
      id: item.item_id || `c${idx}`,
      text: item.text,
      citations: isRealUrl
        ? [{ sourceName: domainLabel(url), url }]
        : [],
    };
  });
}

function adaptFilteredOut(
  items: BackendFilteredOut[],
  schemes: BackendScheme[],
  jobs: BackendJobMatch[],
  housing: BackendHousing[],
): FilteredOutItem[] {
  // Build id→name lookup for human-readable item names
  const nameMap: Record<string, string> = {};
  for (const s of schemes) {
    const id = s.scheme_id || s.id || '';
    if (id) nameMap[id] = s.scheme_name || s.name || id;
  }
  for (const j of jobs) {
    if (j.job?.id) nameMap[j.job.id] = j.job.title || j.job.id;
  }
  for (const h of housing) {
    if (h.id) nameMap[h.id] = h.name || h.id;
  }

  return items.map((f) => ({
    item: nameMap[f.item_id] || f.item_id,
    category: f.category,
    reasons: f.reasons,
  }));
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Results() {
  const { t } = useTranslation();
  const location = useLocation();

  // Pull real plan + profile from navigation state (set by processing.tsx)
  const locationState = location.state as { plan?: BackendPlan; profile?: Record<string, unknown> } | null;
  const plan: BackendPlan = locationState?.plan ?? { schemes: [], jobs: [], housing: [], checklist: [], citations: [], filtered_out: [] };
  const profile = locationState?.profile ?? {};
  const seekerType = (profile.seeker_type as string) || 'both';

  // Adapt backend data to UI card props
  const schemes = (plan.schemes || []).map(adaptScheme);
  const jobs = (plan.jobs || []).map(adaptJob);
  const housing = (plan.housing || []).map(adaptHousing);
  const checklist = adaptChecklist(plan.checklist || []);
  const filteredOut = adaptFilteredOut(
    plan.filtered_out || [],
    plan.schemes || [],
    plan.jobs || [],
    plan.housing || [],
  );

  const [activeTab, setActiveTab] = useState('plan');
  const [drawerItem, setDrawerItem] = useState<any | null>(null);
  const [checklistState, setChecklistState] = useState<Record<string, boolean>>({});

  const toggleChecklist = (id: string) => {
    setChecklistState(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const tabs: NavTab[] = [];
  tabs.push({ id: 'schemes', labelKey: 'results.tab_schemes', icon: FileText });
  if (seekerType === 'both' || seekerType === 'job') {
    tabs.push({ id: 'jobs', labelKey: 'results.tab_jobs', icon: Briefcase });
  }
  if (seekerType === 'both' || seekerType === 'housing') {
    tabs.push({ id: 'housing', labelKey: 'results.tab_housing', icon: Building2 });
  }
  tabs.push({ id: 'plan', labelKey: 'results.tab_plan', icon: LayoutList });

  const filteredOutForTab = filteredOut.filter(i =>
    (activeTab === 'schemes' && i.category === 'scheme') ||
    (activeTab === 'jobs' && i.category === 'job') ||
    (activeTab === 'housing' && i.category === 'housing')
  );

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <Header />
      <div className="max-w-[600px] mx-auto p-4 space-y-4">

        {activeTab === 'plan' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <PlanSummaryCard
              completed={Object.values(checklistState).filter(Boolean).length}
              total={checklist.length}
            />
            <div className="mt-6 space-y-3">
              <h3 className="font-semibold text-gray-900 mb-2">{t('results.next_steps', 'Next Steps')}</h3>
              {checklist.length === 0 ? (
                <p className="text-sm text-gray-500">{t('results.no_steps', 'No steps to show yet.')}</p>
              ) : checklist.map(item => (
                <ChecklistItem
                  key={item.id}
                  item={item}
                  checked={!!checklistState[item.id]}
                  onToggle={() => toggleChecklist(item.id)}
                />
              ))}
            </div>
          </div>
        )}

        {activeTab === 'schemes' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 space-y-4">
            <h2 className="text-xl font-bold text-gray-900">{t('results.recommended_schemes', 'Recommended Schemes')}</h2>
            {schemes.length === 0 ? (
              <p className="text-sm text-gray-500">{t('results.no_schemes', 'No matching schemes found.')}</p>
            ) : schemes.map(s => (
              <SchemeCard key={s.id} scheme={s} onClick={() => setDrawerItem({ type: 'Scheme', data: s })} />
            ))}
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 space-y-4">
            <h2 className="text-xl font-bold text-gray-900">{t('results.matched_jobs', 'Matched Jobs')}</h2>
            {jobs.length === 0 ? (
              <p className="text-sm text-gray-500">{t('results.no_jobs', 'No matching jobs found.')}</p>
            ) : jobs.map(j => (
              <JobCard key={j.id} job={j} onClick={() => setDrawerItem({ type: 'Job', data: j })} />
            ))}
          </div>
        )}

        {activeTab === 'housing' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 space-y-4">
            <h2 className="text-xl font-bold text-gray-900">{t('results.housing_options', 'Housing Options')}</h2>
            {housing.length === 0 ? (
              <p className="text-sm text-gray-500">{t('results.no_housing', 'No matching housing found.')}</p>
            ) : housing.map(h => (
              <HousingCard key={h.id} housing={h} onClick={() => setDrawerItem({ type: 'Housing', data: h })} />
            ))}
          </div>
        )}

        {(activeTab === 'schemes' || activeTab === 'jobs' || activeTab === 'housing') && (
          <FilteredOutPanel items={filteredOutForTab} />
        )}

      </div>

      <BottomNav
        tabs={tabs}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      <Drawer
        isOpen={!!drawerItem}
        onClose={() => setDrawerItem(null)}
        title={drawerItem?.data?.name || drawerItem?.data?.title || `${drawerItem?.type} Details`}
      >
        {drawerItem && (
          <div className="space-y-4 text-sm">
            {drawerItem.type === 'Scheme' && (
              <>
                {drawerItem.data.eligibilityStatus !== 'eligible' && drawerItem.data.eligibilityReasons?.length > 0 && (
                  <div className="space-y-1 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
                    <p className="text-xs font-semibold text-yellow-800 uppercase tracking-wide">
                      {t('results.drawer_why_not_eligible', 'Why this needs review')}
                    </p>
                    <ul className="list-disc list-inside space-y-0.5 text-yellow-900 text-xs">
                      {drawerItem.data.eligibilityReasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_benefit')}</p>
                  <p className="text-gray-700">{drawerItem.data.benefit || drawerItem.data.benefitsSummary}</p>
                </div>
                {drawerItem.data.eligibilityCriteria?.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_eligibility')}</p>
                    <ul className="list-disc list-inside space-y-0.5 text-gray-700">
                      {drawerItem.data.eligibilityCriteria.map((c: string, i: number) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}
                {drawerItem.data.howToApply && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_how_to_apply')}</p>
                    <p className="text-gray-700">{drawerItem.data.howToApply}</p>
                  </div>
                )}
                {drawerItem.data.sourceUrl && (
                  <a href={drawerItem.data.sourceUrl} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 underline text-xs pt-1">
                    {drawerItem.data.sourceName || drawerItem.data.sourceUrl} ↗
                  </a>
                )}
              </>
            )}
            {drawerItem.type === 'Job' && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_employer')}</p>
                    <p className="font-medium">{drawerItem.data.employer}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_pay')}</p>
                    <p className="font-medium">
                      {drawerItem.data.payMin != null && drawerItem.data.payMax != null
                        ? `₹${drawerItem.data.payMin.toLocaleString()} – ₹${drawerItem.data.payMax.toLocaleString()}`
                        : drawerItem.data.payMin != null
                          ? `₹${drawerItem.data.payMin.toLocaleString()}+`
                          : '—'}
                    </p>
                  </div>
                  {drawerItem.data.commuteMinutes != null && (
                    <div className="space-y-0.5">
                      <p className="text-xs text-gray-500">{t('results.drawer_commute')}</p>
                      <p className="font-medium">{drawerItem.data.commuteMinutes} min</p>
                    </div>
                  )}
                  {drawerItem.data.schemeLink && (
                    <div className="space-y-0.5">
                      <p className="text-xs text-gray-500">{t('results.drawer_linked_scheme')}</p>
                      <p className="font-medium">{drawerItem.data.schemeLink}</p>
                    </div>
                  )}
                </div>
                {drawerItem.data.requirements?.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_requirements')}</p>
                    <ul className="list-disc list-inside space-y-0.5 text-gray-700">
                      {drawerItem.data.requirements.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                {drawerItem.data.matchReason && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_match_reason', 'Why this match')}</p>
                    <p className="text-gray-700">{drawerItem.data.matchReason}</p>
                  </div>
                )}
                {drawerItem.data.howToApply && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_how_to_apply')}</p>
                    <p className="text-gray-700">{drawerItem.data.howToApply}</p>
                  </div>
                )}
                {drawerItem.data.sourceUrl && (
                  <a href={drawerItem.data.sourceUrl} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 underline text-xs pt-1">
                    {drawerItem.data.sourceName || drawerItem.data.sourceUrl} ↗
                  </a>
                )}
              </>
            )}
            {drawerItem.type === 'Housing' && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_area')}</p>
                    <p className="font-medium">{drawerItem.data.area}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_occupancy')}</p>
                    <p className="font-medium">{drawerItem.data.occupancy}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_price_from')}</p>
                    <p className="font-medium">₹{drawerItem.data.priceMin?.toLocaleString()}/mo</p>
                  </div>
                  {drawerItem.data.commuteMinutes != null && (
                    <div className="space-y-0.5">
                      <p className="text-xs text-gray-500">{t('results.drawer_commute')}</p>
                      <p className="font-medium">{drawerItem.data.commuteMinutes} min</p>
                    </div>
                  )}
                </div>
                {drawerItem.data.amenities?.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_amenities')}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {drawerItem.data.amenities.map((a: string, i: number) => (
                        <span key={i} className="bg-gray-100 text-gray-700 rounded px-2 py-0.5 text-xs">{a}</span>
                      ))}
                    </div>
                  </div>
                )}
                {drawerItem.data.deposit && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_deposit')}</p>
                    <p className="text-gray-700">{drawerItem.data.deposit}</p>
                  </div>
                )}
                {drawerItem.data.contact && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_contact')}</p>
                    <p className="text-gray-700">{drawerItem.data.contact}</p>
                  </div>
                )}
                {drawerItem.data.sourceUrl && (
                  <a href={drawerItem.data.sourceUrl} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 underline text-xs pt-1">
                    {drawerItem.data.sourceName || drawerItem.data.sourceUrl} ↗
                  </a>
                )}
              </>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}
