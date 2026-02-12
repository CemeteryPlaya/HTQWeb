import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface TimeRecord {
  id: number;
  employee_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: string;
  comment: string;
  approved_by_name: string | null;
}

const HRTimeTracking = () => {
  const { data: records, isLoading, error } = useQuery({
    queryKey: ['hr-timetracking'],
    queryFn: async () => {
      const res = await api.get<TimeRecord[]>('hr/time-tracking/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading time tracking</div>;

  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-500',
    approved: 'bg-green-500',
    rejected: 'bg-red-500',
    cancelled: 'bg-gray-500',
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Time Tracking</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Days</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Approved By</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records?.map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-medium">{record.employee_name}</TableCell>
                  <TableCell>{record.leave_type}</TableCell>
                  <TableCell>
                    {new Date(record.start_date).toLocaleDateString()} - {new Date(record.end_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>{record.duration_days}</TableCell>
                  <TableCell>
                    <Badge className={statusColors[record.status]}>{record.status}</Badge>
                  </TableCell>
                  <TableCell>{record.approved_by_name || '—'}</TableCell>
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

export default HRTimeTracking;
