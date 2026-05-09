import { EligibilityBadge, MatchScore, CommuteChip, SchemeLinkedBadge, CitationLink } from './Badges';
import { Building2, CheckSquare, Square, ChevronRight, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

function BaseCard({ children, className, onClick }: CardProps) {
  return (
    <div 
      onClick={onClick}
      className={cn(
        "bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden", 
        onClick ? "cursor-pointer hover:shadow-md transition-shadow" : "",
        className
      )}
    >
      {children}
    </div>
  );
}

export function PlanSummaryCard({ completed = 0, total = 0 }: { completed?: number; total?: number }) {
  const { t } = useTranslation();
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  return (
    <BaseCard className="bg-gradient-to-br from-teal-500 to-teal-700 text-white border-transparent p-5">
      <h2 className="text-xl font-bold mb-2">{t('results.plan_title', 'Your Transition Plan')}</h2>
      <p className="text-teal-50 text-sm mb-4">
        {t('results.plan_desc', 'We matched you with schemes, jobs, and housing that fit your profile.')}
      </p>
      <div className="w-full bg-teal-800/50 rounded-lg p-3 text-sm flex items-center justify-between">
        <span>{t('results.plan_progress', '{{completed}} of {{total}} steps completed', { completed, total })}</span>
        <span className="font-semibold text-teal-100">{pct}%</span>
      </div>
    </BaseCard>
  );
}

export function SchemeCard({ scheme, onClick }: { scheme: any; onClick: () => void }) {
  const { t } = useTranslation();
  return (
    <BaseCard onClick={onClick}>
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-gray-900 leading-tight">{scheme.name}</h3>
          <EligibilityBadge status={scheme.eligibilityStatus} />
        </div>
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{scheme.benefitsSummary}</p>
        <div className="flex justify-between items-center">
          <CitationLink url={scheme.sourceUrl} sourceName={scheme.sourceName} />
          <span className="text-teal-600 text-sm font-medium flex items-center">
            {t('results.view_details', 'View details')} <ChevronRight className="w-4 h-4 ml-1" />
          </span>
        </div>
      </div>
    </BaseCard>
  );
}

export function JobCard({ job, onClick }: { job: any; onClick: () => void }) {
  return (
    <BaseCard onClick={onClick}>
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <div>
            <h3 className="font-semibold text-gray-900 leading-tight">{job.title}</h3>
            <p className="text-sm text-gray-500">{job.employer}</p>
          </div>
          <MatchScore score={job.matchScore} />
        </div>
        
        <div className="flex flex-wrap gap-2 mt-3 mb-3">
          {(job.payMin != null || job.payMax != null) && (
            <div className="text-sm font-medium text-gray-900 bg-gray-100 px-2.5 py-1 rounded-md">
              {job.payMin != null && job.payMax != null
                ? `₹${job.payMin.toLocaleString()} – ₹${job.payMax.toLocaleString()}`
                : job.payMin != null
                ? `₹${job.payMin.toLocaleString()}+`
                : `Up to ₹${job.payMax!.toLocaleString()}`}
            </div>
          )}
          {job.schemeLink && <SchemeLinkedBadge label={job.schemeLink} />}
          {job.commuteMinutes && <CommuteChip minutes={job.commuteMinutes} />}
        </div>

        <div className="flex justify-between items-center">
          <CitationLink url={job.sourceUrl} sourceName={job.sourceName} />
          <span className="text-teal-600 text-sm font-medium flex items-center">
            View details <ChevronRight className="w-4 h-4 ml-1" />
          </span>
        </div>
      </div>
    </BaseCard>
  );
}

export function HousingCard({ housing, onClick }: { housing: any; onClick: () => void }) {
  return (
    <BaseCard onClick={onClick}>
      <div className="p-4 flex gap-4">
        <div className="w-20 h-20 bg-gray-200 rounded-lg flex-shrink-0 overflow-hidden flex items-center justify-center">
           <Building2 className="w-8 h-8 text-gray-400" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 leading-tight mb-1">{housing.name}</h3>
          <p className="text-sm text-gray-500 mb-2">{housing.area} • {housing.occupancy}</p>
          
          <div className="flex justify-between items-end">
            <div>
              <span className="text-lg font-bold text-gray-900">₹{housing.priceMin}</span>
              <span className="text-xs text-gray-500">/mo</span>
            </div>
            {housing.commuteMinutes && <CommuteChip minutes={housing.commuteMinutes} />}
          </div>
        </div>
      </div>
      <div className="px-4 pb-3 pt-0 flex justify-between items-center">
        <CitationLink url={housing.sourceUrl} sourceName={housing.sourceName} />
        <span className="text-teal-600 text-sm font-medium flex items-center">
          View details <ChevronRight className="w-4 h-4 ml-1" />
        </span>
      </div>
    </BaseCard>
  );
}

export function ChecklistItem({ item, checked, onToggle }: { item: any, checked: boolean, onToggle: () => void }) {
  return (
    <div 
      className={cn(
        "flex gap-3 p-3 rounded-lg border transition-colors cursor-pointer",
        checked ? "bg-gray-50 border-gray-200 opacity-75" : "bg-white border-gray-300 hover:border-teal-500"
      )}
      onClick={onToggle}
    >
      <div className="pt-0.5 text-teal-600">
        {checked ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />}
      </div>
      <div>
        <p className={cn("text-sm font-medium text-gray-900 leading-snug", checked && "line-through text-gray-500")}>
          {item.text}
        </p>
        {item.citations && item.citations.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-2">
            {item.citations.map((cit: any, i: number) => (
              <a 
                key={i} 
                href={cit.url} 
                target="_blank" 
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-xs text-teal-600 hover:underline inline-flex items-center"
              >
                {cit.sourceName} <ExternalLink className="w-3 h-3 ml-0.5" />
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
