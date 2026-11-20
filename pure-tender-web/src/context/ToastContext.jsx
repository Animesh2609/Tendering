import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { CircleAlert, CircleCheck, Info, X } from 'lucide-react';

const ToastContext = createContext(null);
let nextId = 1;

export function showToast(message, type = 'success') {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('pure-tender:toast', { detail: { message, type } }));
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const dismiss = useCallback(id => setToasts(items => items.filter(item => item.id !== id)), []);
  const push = useCallback(({ message, type = 'success' }) => {
    if (!message) return;
    const id = nextId++;
    setToasts(items => [...items.slice(-3), { id, message, type }]);
    window.setTimeout(() => dismiss(id), 4800);
  }, [dismiss]);

  useEffect(() => {
    const onToast = event => push(event.detail || {});
    window.addEventListener('pure-tender:toast', onToast);
    return () => window.removeEventListener('pure-tender:toast', onToast);
  }, [push]);

  const value = useMemo(() => ({ notify: (message, type) => showToast(message, type), dismiss }), [dismiss]);
  return <ToastContext.Provider value={value}>
    {children}
    <div className="toast-viewport" aria-live="polite" aria-relevant="additions text">
      {toasts.map(toast => {
        const Icon = toast.type === 'error' ? CircleAlert : toast.type === 'info' ? Info : CircleCheck;
        return <div className={`app-toast app-toast-${toast.type}`} key={toast.id} role={toast.type === 'error' ? 'alert' : 'status'}>
          <Icon size={20} aria-hidden="true"/><span>{toast.message}</span>
          <button type="button" onClick={() => dismiss(toast.id)} aria-label="Dismiss notification"><X size={17}/></button>
        </div>;
      })}
    </div>
  </ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
}
