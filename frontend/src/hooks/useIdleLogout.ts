import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { useAuthStore } from '../stores/authStore';

/**
 * Idle 自动登出 Hook (PRD §17.3)
 * =====================================
 *
 * 默认 60 分钟无任何用户输入 (mousemove / keydown / click / scroll / touchstart) 触发登出.
 *
 * 设计要点:
 *   - 计时器: useRef, 不重渲染
 *   - 事件节流: 1 秒内重复触发不重置计时器 (避免高频 mousemove 反复创建定时器)
 *   - 未登录态直接返回, 不挂事件
 *   - 路由切换不重置 (只在 AppLayout 挂载一次, 整个 session 共用)
 *
 * 用法: 在 AppLayout 中调用一次 useIdleLogout().
 */
export interface UseIdleLogoutOptions {
  /** 空闲阈值, 毫秒. 默认 60 分钟. */
  idleMs?: number;
  /** 倒计时提示 (毫秒), 默认 60 秒前弹确认. 设为 0 关闭提示. */
  warnBeforeMs?: number;
}

export function useIdleLogout(options: UseIdleLogoutOptions = {}): void {
  const { idleMs = 60 * 60 * 1000, warnBeforeMs = 60 * 1000 } = options;
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuthStore();
  const timerRef = useRef<number | null>(null);
  const warnTimerRef = useRef<number | null>(null);
  const lastResetRef = useRef<number>(0);

  useEffect(() => {
    if (!isAuthenticated) {
      // 未登录清掉定时器
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (warnTimerRef.current !== null) {
        window.clearTimeout(warnTimerRef.current);
        warnTimerRef.current = null;
      }
      return;
    }

    const doLogout = (reason: 'idle' | 'warned') => {
      logout();
      if (reason === 'idle') {
        message.warning('您已超过 60 分钟无操作, 系统已自动登出');
      } else {
        message.info('已自动登出');
      }
      navigate('/login');
    };

    const resetTimer = () => {
      const now = Date.now();
      // 1 秒内重复事件忽略, 避免高频触发
      if (now - lastResetRef.current < 1000) return;
      lastResetRef.current = now;

      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      if (warnTimerRef.current !== null) window.clearTimeout(warnTimerRef.current);

      // 倒计时提示 (idleMs - warnBeforeMs 时弹确认, 当前实现直接登出, 简化)
      if (warnBeforeMs > 0) {
        warnTimerRef.current = window.setTimeout(() => {
          message.warning('60 秒后将自动登出, 请操作以继续保持登录');
        }, idleMs - warnBeforeMs);
      }

      timerRef.current = window.setTimeout(() => doLogout('idle'), idleMs);
    };

    const events: Array<keyof WindowEventMap> = [
      'mousemove',
      'mousedown',
      'keydown',
      'scroll',
      'touchstart',
      'click',
    ];

    events.forEach((e) => window.addEventListener(e, resetTimer, { passive: true }));
    resetTimer(); // 初始启动

    return () => {
      events.forEach((e) => window.removeEventListener(e, resetTimer));
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      if (warnTimerRef.current !== null) window.clearTimeout(warnTimerRef.current);
    };
  }, [isAuthenticated, idleMs, warnBeforeMs, logout, navigate]);
}

export default useIdleLogout;