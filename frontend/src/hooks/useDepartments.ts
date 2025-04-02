import { useState, useEffect } from 'react';
import { 
  getAllDepartments, 
  getDepartmentOptions, 
  getDepartmentFilters, 
  Department 
} from '../utils/DepartmentGroups';

export const useDepartments = () => {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [options, setOptions] = useState<Array<{value: string, label: string}>>([]);
  const [filters, setFilters] = useState<Array<{text: string, value: string}>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 模拟从服务器获取部门数据
    setLoading(true);
    try {
      // 从 DepartmentGroups 获取数据
      const depts = getAllDepartments();
      setDepartments(depts);
      
      // 获取部门选项（用于Select组件）
      setOptions(getDepartmentOptions());
      
      // 获取部门过滤项（用于Table组件的filters）
      setFilters(getDepartmentFilters());
    } catch (error) {
      console.error('获取部门数据失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    departments,
    options,
    filters,
    loading
  };
};

export default useDepartments; 