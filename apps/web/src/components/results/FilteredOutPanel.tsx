import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface FilteredOutItem {
  item: string;
  category: 'scheme' | 'job' | 'housing';
  reasons: string[];
}

export function FilteredOutPanel({ items }: { items: FilteredOutItem[] }) {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();

  if (!items || items.length === 0) return null;

  return (
    <div className="mt-8 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2 text-gray-600">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium text-sm">
            {items.length} {t('results.filtered_items', 'items filtered out')}
          </span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </button>
      
      {isOpen && (
        <div className="p-4 border-t border-gray-200 divide-y divide-gray-100">
          {items.map((item, idx) => (
            <div key={idx} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold uppercase text-gray-500 tracking-wider">
                  {item.category}
                </span>
                <span className="font-medium text-sm text-gray-900">{item.item}</span>
              </div>
              <ul className="list-disc list-inside text-xs text-red-600 ml-1 space-y-0.5">
                {item.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
