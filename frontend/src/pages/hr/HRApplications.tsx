import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface Application {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  vacancy_title: string;
  status: string;
  created_at: string;
}

const HRApplications = () => {
  const { data: applications, isLoading, error } = useQuery({
    queryKey: ['hr-applications'],
    queryFn: async () => {
      const res = await api.get<Application[]>('hr/applications/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading applications</div>;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Job Applications</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Applicant</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Vacancy</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Applied</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {applications?.map((app) => (
                <TableRow key={app.id}>
                  <TableCell className="font-medium">{app.first_name} {app.last_name}</TableCell>
                  <TableCell>{app.email}</TableCell>
                  <TableCell>{app.phone || '—'}</TableCell>
                  <TableCell>{app.vacancy_title}</TableCell>
                  <TableCell>
                    <Badge>{app.status}</Badge>
                  </TableCell>
                  <TableCell>{new Date(app.created_at).toLocaleDateString()}</TableCell>
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

export default HRApplications;
