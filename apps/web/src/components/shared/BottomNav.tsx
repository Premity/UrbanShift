import React from 'react';
import { cn } from '../../lib/utils';
import { LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface NavTab {
  id: string;
  labelKey: string;
  icon: LucideIcon;
}

interface BottomNavProps {
  tabs: NavTab[];
  activeTab: string;
  onChange: (id: string) => void;
}

export function BottomNav({ tabs, activeTab, onChange }: BottomNavProps) {
  const { t } = useTranslation();
  
  return (
    <div className="fixed bottom-0 left-0 right-0 max-w-[600px] mx-auto bg-white border-t border-gray-200 pb-2 shadow-[0_-4px_6px_-1px_rgb(0,0,0,0.05)] z-40">
      <div className="flex justify-around items-center h-16 px-2">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={cn(
                "flex flex-col items-center justify-center w-full h-full space-y-1 transition-colors",
                isActive ? "text-teal-600" : "text-gray-500 hover:text-gray-900"
              )}
            >
              <Icon className="w-6 h-6" strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-[10px] font-medium leading-none">{t(tab.labelKey, tab.labelKey)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
