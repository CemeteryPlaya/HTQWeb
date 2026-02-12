import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Employee {
  id: number;
  full_name: string;
  username: string;
  email: string;
  position_title: string;
  department_name: string;
  phone: string;
  date_hired: string;
  status: string;
}

const HREmployees = () => {
  const { data: employees, isLoading, error } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: async () => {
      const res = await api.get<Employee[]>('hr/employees/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-1 container mx-auto px-4 py-8">
          <div className="text-center text-red-500">
            <h1 className="text-2xl font-bold mb-2">Error loading employees</h1>
            <p>{(error as any)?.message || 'Unknown error'}</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Employees</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Position</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Hired</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {employees?.map((emp) => (
                <TableRow key={emp.id}>
                  <TableCell className="font-medium">{emp.full_name}</TableCell>
                  <TableCell>{emp.email}</TableCell>
                  <TableCell>{emp.position_title || '—'}</TableCell>
                  <TableCell>{emp.department_name || '—'}</TableCell>
                  <TableCell>{emp.phone || '—'}</TableCell>
                  <TableCell>{emp.status}</TableCell>
                  <TableCell>{emp.date_hired ? new Date(emp.date_hired).toLocaleDateString() : '—'}</TableCell>
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

export default HREmployees;
