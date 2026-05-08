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
    detail: 'Full detail text here...'
  },
  {
    id: 's2',
    name: 'Karnataka Skill Connect',
    eligibilityStatus: 'check' as const,
    benefitsSummary: 'Free upskilling courses and guaranteed interview opportunities. Domicile check required.',
    sourceUrl: 'https://skillconnect.ka.gov.in',
    sourceName: 'skillconnect.ka.gov.in',
    detail: 'Full detail text here...'
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
    detail: 'Full detail text here...'
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
    detail: 'Full detail text here...'
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
    detail: 'Full detail text here...'
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
    detail: 'Full detail text here...'
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
  tabs.push({ id: 'schemes', labelKey: 'Schemes', icon: FileText });
  if (seekerType === 'both' || seekerType === 'job') {
    tabs.push({ id: 'jobs', labelKey: 'Jobs', icon: Briefcase });
  }
  if (seekerType === 'both' || seekerType === 'housing') {
    tabs.push({ id: 'housing', labelKey: 'Housing', icon: Building2 });
  }
  tabs.push({ id: 'plan', labelKey: 'Plan', icon: LayoutList });

  return (
    <div className="min-h-screen bg-gray-50 pb-20 pt-4">
      <div className="max-w-[600px] mx-auto p-4 space-y-4">
        
        {activeTab === 'plan' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <PlanSummaryCard />
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
        title={drawerItem ? `${drawerItem.type} Details` : ''}
      >
        {drawerItem && (
          <div className="space-y-4">
            <p className="text-gray-600">
              {drawerItem.data.detail || drawerItem.data.benefitsSummary || "More details will be rendered here."}
            </p>
            <div className="bg-gray-50 p-4 rounded-lg text-sm font-mono text-gray-500 overflow-x-auto">
              <pre>{JSON.stringify(drawerItem.data, null, 2)}</pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
