import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import dayjs from 'dayjs';

// 高级搜索条件接口
export interface AdvancedSearchParams {
  name?: string;
  description?: string;
  team?: string;
  template?: string;
  status?: string;
  approvalStatus?: string;
  createdBy?: string;
  createdAtRange?: [dayjs.Dayjs, dayjs.Dayjs] | null;
}

// Ledger list store interface
interface LedgerListStore {
  // Simple search
  searchText: string;
  setSearchText: (text: string) => void;

  // Advanced search
  advancedSearchParams: AdvancedSearchParams;
  setAdvancedSearchParams: (params: AdvancedSearchParams) => void;
  isAdvancedSearchActive: boolean;
  setIsAdvancedSearchActive: (active: boolean) => void;

  // Pagination
  currentPage: number;
  setCurrentPage: (page: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;

  // Actions
  resetAll: () => void;
  resetAdvancedSearch: () => void;

  // Store the last path for navigation tracking
  lastPath: string | null;
  setLastPath: (path: string | null) => void;
}

// Default advanced search parameters
const DEFAULT_ADVANCED_SEARCH_PARAMS: AdvancedSearchParams = {
  name: '',
  description: '',
  team: undefined,
  template: undefined,
  status: undefined,
  approvalStatus: undefined,
  createdBy: '',
  createdAtRange: undefined
};

export const useLedgerListStore = create<LedgerListStore>()(
  persist(
    (set, get) => ({
      // Simple search
      searchText: '',
      setSearchText: (text: string) => set({ searchText: text }),

      // Advanced search
      advancedSearchParams: DEFAULT_ADVANCED_SEARCH_PARAMS,
      setAdvancedSearchParams: (params) => set({ advancedSearchParams: params }),
      isAdvancedSearchActive: false,
      setIsAdvancedSearchActive: (active) => set({ isAdvancedSearchActive: active }),

      // Pagination
      currentPage: 1,
      setCurrentPage: (page) => set({ currentPage: page }),
      pageSize: 10,
      setPageSize: (size) => set({ pageSize: size }),

      // Store navigation state
      lastPath: null,
      setLastPath: (path) => set({ lastPath: path }),

      // Actions
      resetAll: () => set({
        searchText: '',
        advancedSearchParams: DEFAULT_ADVANCED_SEARCH_PARAMS,
        isAdvancedSearchActive: false,
        currentPage: 1,
        pageSize: 10,
        lastPath: null,
      }),

      resetAdvancedSearch: () => set({
        advancedSearchParams: DEFAULT_ADVANCED_SEARCH_PARAMS,
        isAdvancedSearchActive: false,
      }),
    }),
    {
      name: 'ledger-list-storage',
      partialize: (state) => ({
        searchText: state.searchText,
        advancedSearchParams: state.advancedSearchParams,
        isAdvancedSearchActive: state.isAdvancedSearchActive,
        currentPage: state.currentPage,
        pageSize: state.pageSize,
        lastPath: state.lastPath,
      }),
    }
  )
);