import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface ActionLog {
  id: number;
  user_name: string;
  action: string;
  target_type: string;
  target_repr: string;
  details: string;
  ip_address: string | null;
  created_at: string;
}

const HRLogs = () => {
  const { data: logs, isLoading, error } = useQuery({
    queryKey: ['hr-logs'],
    queryFn: async () => {
      const res = await api.get<ActionLog[]>('hr/logs/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading logs</div>;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">HR Action Logs</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs?.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                  <TableCell className="font-medium">{log.user_name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{log.action}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="text-xs text-muted-foreground">{log.target_type}</div>
                    <div>{log.target_repr}</div>
                  </TableCell>
                  <TableCell className="max-w-md truncate text-sm">{log.details}</TableCell>
                  <TableCell className="text-xs">{log.ip_address || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default HRLogs;
