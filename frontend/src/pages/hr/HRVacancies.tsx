import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface Vacancy {
  id: number;
  title: string;
  department_name: string;
  status: string;
  created_by_name: string;
  applications_count: number;
  salary_min: number | null;
  salary_max: number | null;
  created_at: string;
}

const HRVacancies = () => {
  const { data: vacancies, isLoading, error } = useQuery({
    queryKey: ['hr-vacancies'],
    queryFn: async () => {
      const res = await api.get<Vacancy[]>('hr/vacancies/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading vacancies</div>;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Vacancies</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Salary Range</TableHead>
                <TableHead>Applications</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {vacancies?.map((vacancy) => (
                <TableRow key={vacancy.id}>
                  <TableCell className="font-medium">{vacancy.title}</TableCell>
                  <TableCell>{vacancy.department_name || '—'}</TableCell>
                  <TableCell>
                    <Badge variant={vacancy.status === 'open' ? 'default' : 'secondary'}>{vacancy.status}</Badge>
                  </TableCell>
                  <TableCell>
                    {vacancy.salary_min && vacancy.salary_max
                      ? `$${vacancy.salary_min} - $${vacancy.salary_max}`
                      : '—'}
                  </TableCell>
                  <TableCell>{vacancy.applications_count || 0}</TableCell>
                  <TableCell>{new Date(vacancy.created_at).toLocaleDateString()}</TableCell>
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

export default HRVacancies;
