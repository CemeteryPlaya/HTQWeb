import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Document {
  id: number;
  employee_name: string;
  title: string;
  doc_type: string;
  file: string;
  uploaded_by_name: string;
  created_at: string;
}

const HRDocuments = () => {
  const { data: documents, isLoading, error } = useQuery({
    queryKey: ['hr-documents'],
    queryFn: async () => {
      const res = await api.get<Document[]>('hr/documents/');
      return res.data;
    },
  });

  if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading documents</div>;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">HR Documents</h1>
        <div className="bg-card rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Document</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Uploaded By</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents?.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="font-medium">{doc.employee_name}</TableCell>
                  <TableCell>{doc.title}</TableCell>
                  <TableCell>{doc.doc_type}</TableCell>
                  <TableCell>{doc.uploaded_by_name || '—'}</TableCell>
                  <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <a href={doc.file} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      Download
                    </a>
                  </TableCell>
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

export default HRDocuments;
