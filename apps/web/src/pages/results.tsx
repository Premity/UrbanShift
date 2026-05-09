import React, { useState } from 'react';
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

// --- MOCK DATA ---
const MOCK_SCHEMES = [
  {
    id: 's1',
    name: 'PM Vishwakarma Yojana',
    eligibilityStatus: 'eligible' as const,
    benefitsSummary: 'Collateral free credit up to ₹1 Lakh, stipend of ₹500/day during training.',
    sourceUrl: 'https://pmvishwakarma.gov.in',
    sourceName: 'pmvishwakarma.gov.in',
    eligibilityCriteria: ['Age 18–60', 'Self-employed artisan or craftsperson', 'Not enrolled in PMEGP/PM SVANidhi'],
    howToApply: 'Register at your nearest Common Service Centre (CSC) with Aadhaar and trade proof.',
    benefit: '₹500/day training stipend + collateral-free credit up to ₹1 Lakh at 5% interest.'
  },
  {
    id: 's2',
    name: 'Karnataka Skill Connect',
    eligibilityStatus: 'check' as const,
    benefitsSummary: 'Free upskilling courses and guaranteed interview opportunities. Domicile check required.',
    sourceUrl: 'https://skillconnect.ka.gov.in',
    sourceName: 'skillconnect.ka.gov.in',
    eligibilityCriteria: ['Karnataka domicile (verify required)', 'Age 18–45', 'Class 10 pass or above'],
    howToApply: 'Apply online at skillconnect.ka.gov.in with domicile certificate and education proof.',
    benefit: 'Free skill training + guaranteed job interview with partner employers.'
  }
];

const MOCK_JOBS = [
  {
    id: 'j1',
    title: 'Delivery Executive',
    employer: 'Zomato',
    matchScore: 92,
    payMin: 18000,
    payMax: 22000,
    schemeLink: 'PMKVY Linked',
    commuteMinutes: 15,
    sourceUrl: 'https://ncs.gov.in',
    sourceName: 'NCS Portal',
    requirements: ['Two-wheeler license', 'Own smartphone', 'Age 18–40'],
    perks: 'Weekly pay, accident insurance, fuel incentive up to ₹3,000/month.',
    howToApply: 'Apply via NCS Portal or walk-in at Zomato onboarding center, Bellandur.'
  },
  {
    id: 'j2',
    title: 'Warehouse Staff',
    employer: 'Amazon Fulfilment',
    matchScore: 78,
    payMin: 15000,
    payMax: 18000,
    commuteMinutes: 45,
    sourceUrl: 'https://apna.co',
    sourceName: 'Apna',
    requirements: ['Class 8 pass', 'Physical fitness', 'Willing to work rotational shifts'],
    perks: 'PF/ESI, canteen subsidy, overtime pay.',
    howToApply: 'Apply via Apna app or directly at Amazon FC, Doddaballapur Road.'
  }
];

const MOCK_HOUSING = [
  {
    id: 'h1',
    name: 'Shree Sai PG for Men',
    area: 'Marathahalli',
    occupancy: 'Double Sharing',
    priceMin: 6500,
    commuteMinutes: 15,
    sourceUrl: 'https://nobroker.in',
    sourceName: 'NoBroker',
    amenities: ['WiFi', 'Meals included', 'Laundry', 'CCTV'],
    deposit: '₹6,500 (1 month)',
    contact: 'Listed on NoBroker — no broker fee.'
  },
  {
    id: 'h2',
    name: 'BTM Layout Colive',
    area: 'BTM Layout',
    occupancy: 'Single',
    priceMin: 9000,
    commuteMinutes: 50,
    sourceUrl: 'https://nobroker.in',
    sourceName: 'NoBroker',
    amenities: ['AC', 'Attached bath', 'Power backup', 'Security'],
    deposit: '₹18,000 (2 months)',
    contact: 'Listed on NoBroker — no broker fee.'
  }
];

const MOCK_PLAN = [
  {
    id: 'p1',
    text: 'Register for PM Vishwakarma Yojana to receive training stipend.',
    citations: [{ sourceName: 'PM Vishwakarma', url: 'https://pmvishwakarma.gov.in' }]
  },
  {
    id: 'p2',
    text: 'Apply for Delivery Executive position at Zomato.',
    citations: [{ sourceName: 'NCS Portal', url: 'https://ncs.gov.in' }]
  },
  {
    id: 'p3',
    text: 'Contact Shree Sai PG and schedule a visit.',
    citations: [{ sourceName: 'NoBroker', url: 'https://nobroker.in' }]
  }
];

const MOCK_FILTERED_OUT: FilteredOutItem[] = [
  {
    item: 'E-Shram Card',
    category: 'scheme',
    reasons: ['Age must be between 16 and 59']
  },
  {
    item: 'Software Developer - TCS',
    category: 'job',
    reasons: ['Worker band mismatch (Level 5 vs Level 2)']
  }
];

export default function Results() {
  const { t } = useTranslation();
  // We can toggle this to test conditional rendering
  const [seekerType] = useState<'both' | 'job' | 'housing'>('both');
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

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <Header />
      <div className="max-w-[600px] mx-auto p-4 space-y-4">
        
        {activeTab === 'plan' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <PlanSummaryCard
              completed={Object.values(checklistState).filter(Boolean).length}
              total={MOCK_PLAN.length}
            />
            <div className="mt-6 space-y-3">
              <h3 className="font-semibold text-gray-900 mb-2">{t('results.next_steps', 'Next Steps')}</h3>
              {MOCK_PLAN.map(item => (
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
            {MOCK_SCHEMES.map(s => (
              <SchemeCard key={s.id} scheme={s} onClick={() => setDrawerItem({ type: 'Scheme', data: s })} />
            ))}
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 space-y-4">
            <h2 className="text-xl font-bold text-gray-900">{t('results.matched_jobs', 'Matched Jobs')}</h2>
            {MOCK_JOBS.map(j => (
              <JobCard key={j.id} job={j} onClick={() => setDrawerItem({ type: 'Job', data: j })} />
            ))}
          </div>
        )}

        {activeTab === 'housing' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 space-y-4">
            <h2 className="text-xl font-bold text-gray-900">{t('results.housing_options', 'Housing Options')}</h2>
            {MOCK_HOUSING.map(h => (
              <HousingCard key={h.id} housing={h} onClick={() => setDrawerItem({ type: 'Housing', data: h })} />
            ))}
          </div>
        )}

        {(activeTab === 'schemes' || activeTab === 'jobs' || activeTab === 'housing') && (
          <FilteredOutPanel items={MOCK_FILTERED_OUT.filter(i => 
            (activeTab === 'schemes' && i.category === 'scheme') ||
            (activeTab === 'jobs' && i.category === 'job') ||
            (activeTab === 'housing' && i.category === 'housing')
          )} />
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
                    <p className="font-medium">₹{drawerItem.data.payMin?.toLocaleString()} – ₹{drawerItem.data.payMax?.toLocaleString()}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_commute')}</p>
                    <p className="font-medium">{drawerItem.data.commuteMinutes} min</p>
                  </div>
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
                {drawerItem.data.perks && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('results.drawer_perks')}</p>
                    <p className="text-gray-700">{drawerItem.data.perks}</p>
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
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">{t('results.drawer_commute')}</p>
                    <p className="font-medium">{drawerItem.data.commuteMinutes} min</p>
                  </div>
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
