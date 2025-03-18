import { useAuthStore } from '../stores/authStore';

/**
 * 检查当前用户是否拥有指定的权限
 * @param permissions 需要检查的权限数组
 * @param requireAll 是否要求用户拥有所有指定权限，默认为false(拥有任一权限即可)
 * @returns 是否拥有权限
 */
export const checkPermission = (permissions: string[], requireAll: boolean = false): boolean => {
  const { user } = useAuthStore.getState();
  
  if (!user || !user.permissions || user.permissions.length === 0) {
    return false;
  }
  
  // 超级管理员拥有所有权限
  if (user.roles?.includes('admin')) {
    return true;
  }
  
  // 拥有 '*:*' 权限的用户拥有所有权限
  if (user.permissions.includes('*:*')) {
    return true;
  }
  
  if (requireAll) {
    return permissions.every(permission => user.permissions?.includes(permission));
  } else {
    return permissions.some(permission => user.permissions?.includes(permission));
  }
};

/**
 * 过滤出用户拥有权限的项目
 * @param items 带权限要求的项目数组
 * @returns 过滤后的项目数组
 */
export const filterByPermission = <T extends { permission?: string | string[] }>(items: T[]): T[] => {
  return items.filter(item => {
    if (!item.permission) return true;
    
    const permissions = Array.isArray(item.permission) ? item.permission : [item.permission];
    return checkPermission(permissions);
  });
}; 