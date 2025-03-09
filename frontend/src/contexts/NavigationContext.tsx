import React, { createContext, useState, useContext, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

interface BreadcrumbItem {
  title: string;
  path?: string;
}

interface NavigationContextProps {
  breadcrumbs: BreadcrumbItem[];
  setBreadcrumbs: (items: BreadcrumbItem[]) => void;
  navigateTo: (path: string) => void;
  navigateBack: () => void;
}

const NavigationContext = createContext<NavigationContextProps | undefined>(undefined);

interface NavigationProviderProps {
  children: ReactNode;
}

export const NavigationProvider: React.FC<NavigationProviderProps> = ({ children }) => {
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);
  const navigate = useNavigate();

  const navigateTo = (path: string) => {
    navigate(path);
  };

  const navigateBack = () => {
    navigate(-1);
  };

  return (
    <NavigationContext.Provider
      value={{
        breadcrumbs,
        setBreadcrumbs,
        navigateTo,
        navigateBack,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = (): NavigationContextProps => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};

export default NavigationContext; 