import React from 'react';
import { cn } from '../../lib/utils';
import { ExternalLink, CheckCircle2, AlertTriangle, XCircle, MapPin, Briefcase } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export function EligibilityBadge({ status }: { status: 'eligible' | 'check' | 'ineligible' }) {
  const { t } = useTranslation();
  const styles = {
    eligible: "bg-green-100 text-green-800 border-green-200",
    check: "bg-yellow-100 text-yellow-800 border-yellow-200",
    ineligible: "bg-red-100 text-red-800 border-red-200",
  };
  const icons = {
    eligible: CheckCircle2,
    check: AlertTriangle,
    ineligible: XCircle,
  };
  const labels = {
    eligible: "eligible",
    check: "check_req",
    ineligible: "not_eligible",
  };
  const Icon = icons[status];
  
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", styles[status])}>
      <Icon className="w-3.5 h-3.5" />
      {t(`badges.${labels[status]}`, labels[status])}
    </span>
  );
}

export function MatchScore({ score }: { score: number }) {
  let color = "text-green-600 bg-green-50 border-green-200";
  if (score < 60) color = "text-red-600 bg-red-50 border-red-200";
  else if (score < 80) color = "text-yellow-600 bg-yellow-50 border-yellow-200";

  return (
    <span className={cn("inline-flex items-center justify-center px-2 py-1 rounded-md text-xs font-bold border", color)}>
      {score}% Match
    </span>
  );
}

export function CommuteChip({ minutes, onClick }: { minutes: number; onClick?: () => void }) {
  const { t } = useTranslation();
  return (
    <button 
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors text-xs font-medium border border-blue-200"
    >
      <MapPin className="w-3.5 h-3.5" />
      {minutes} {t('badges.min_commute', 'min commute')}
    </button>
  );
}

export function SchemeLinkedBadge({ label, onClick }: { label: string; onClick?: () => void }) {
  return (
    <button 
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors text-xs font-medium border border-teal-200"
    >
      <Briefcase className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

export function CitationLink({ url, sourceName }: { url: string; sourceName: string }) {
  const { t } = useTranslation();
  return (
    <a 
      href={url} 
      target="_blank" 
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-teal-600 transition-colors mt-2"
    >
      {t('badges.source', 'Source:')} {sourceName}
      <ExternalLink className="w-3 h-3" />
    </a>
  );
}
