import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Position {
  id: number;
  title: string;
  department: number | null;
  department_name: string;
}

const HRPositions = () => {
  const { data: positions, isLoading, error } = useQuery({
    queryKey: ['hr-positions'],
    queryFn: async () => {
      const res = await api.get<Position[]>('hr/positions/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading positions</div>;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Positions</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Position Title</TableHead>
                <TableHead>Department</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions?.map((pos) => (
                <TableRow key={pos.id}>
                  <TableCell className="font-medium">{pos.title}</TableCell>
                  <TableCell>{pos.department_name || '—'}</TableCell>
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

export default HRPositions;
