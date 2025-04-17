// 定义部门接口
export interface Department {
  key: string;
  name: string;
  description: string;
  color: string;
}

// 获取所有部门列表
export const getAllDepartments = (): Department[] => {
  return [
    // { key: 'finance', name: '交易处理一', description: '负责公司财务管理', color: 'blue' },
    { key: 'production', name: '审核处理', description: '审核处理团队', color: 'green' },
    // { key: 'customer_service', name: '生产管理', description: '负责客户服务', color: 'purple' },
    // { key: 'equipment', name: '账务服务', description: '负责设备管理和维护', color: 'orange' },
    // { key: 'test', name: '综合管理', description: '负责设备管理和维护', color: 'red' },
  ];
};

// 获取部门选择选项（用于Select组件）
export const getDepartmentOptions = () => {
  const departments = getAllDepartments();
  return departments.map(dept => ({
    value: dept.name,
    label: dept.name,
  }));
};

// 获取部门名称列表（纯字符串数组）
export const getDepartmentNames = (): string[] => {
  return getAllDepartments().map(dept => dept.name);
};

// 根据部门key获取部门信息
export const getDepartmentByKey = (key: string): Department | undefined => {
  return getAllDepartments().find(d => d.key === key);
};

// 根据部门名称获取部门信息
export const getDepartmentByName = (name: string): Department | undefined => {
  return getAllDepartments().find(d => d.name === name);
};

// 根据部门key获取部门名称
export const getDepartmentNameByKey = (key: string): string | undefined => {
  const dept = getDepartmentByKey(key);
  return dept?.name;
};

// 根据部门名称获取部门颜色
export const getDepartmentColorByName = (name: string): string => {
  const dept = getDepartmentByName(name);
  return dept?.color || 'default';
};

// 获取部门过滤选项（用于Table组件的filters）
export const getDepartmentFilters = () => {
  return getAllDepartments().map(dept => ({
    text: dept.name,
    value: dept.name,
  }));
}; 