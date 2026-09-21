import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api';

export default function NotificationBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const unread = useQuery({ queryKey: ['notifications', 'unread'], queryFn: api.unreadCount, refetchInterval: 60_000 });
  const list = useQuery({
    queryKey: ['notifications', 'recent'],
    queryFn: () => api.notifications('?page_size=10'),
    enabled: open,
  });

  async function markAll() {
    await api.markAllRead();
    await queryClient.invalidateQueries({ queryKey: ['notifications'] });
  }

  async function markOne(id: string) {
    await api.markNotificationRead(id);
    await queryClient.invalidateQueries({ queryKey: ['notifications'] });
  }

  return (
    <div className="bell">
      <button className="btn secondary btn-sm" type="button" aria-expanded={open}
        aria-label={`Notifications${unread.data?.unread ? `, ${unread.data.unread} unread` : ''}`}
        onClick={() => setOpen((v) => !v)}>
        🔔{unread.data && unread.data.unread > 0 ? ` ${unread.data.unread}` : ''}
      </button>
      {open && (
        <div className="bell-panel card" role="dialog" aria-label="Notifications">
          <div className="row-actions" style={{ justifyContent: 'space-between' }}>
            <strong>Notifications</strong>
            <button className="btn secondary btn-sm" type="button" onClick={markAll}>Mark all read</button>
          </div>
          {list.isPending && <p className="muted">Loading…</p>}
          {list.data && list.data.results.length === 0 && <p className="muted">No notifications.</p>}
          {list.data?.results.map((n) => (
            <p key={n.id} style={{ fontSize: 13, opacity: n.read ? 0.65 : 1 }}>
              <code>{n.kind}</code> — {n.title}{' '}
              {!n.read && <button className="btn secondary btn-sm" type="button" onClick={() => markOne(n.id)}>Mark read</button>}
            </p>
          ))}
          <p><Link to="/settings">Notification preferences</Link></p>
        </div>
      )}
    </div>
  );
}
