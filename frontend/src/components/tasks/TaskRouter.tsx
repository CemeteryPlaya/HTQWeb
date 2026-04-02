import React from 'react';
import { Loader2 } from 'lucide-react';
import { useActiveProfile } from '@/hooks/useActiveProfile';
import { hasElevatedAccess } from '@/lib/auth/roles';

import HRTasks from '@/pages/hr/HRTasks';
import EmployeeTasks from '@/pages/hr/EmployeeTasks';

export const TaskRouter: React.FC = () => {
    const { activeProfile, isLoading } = useActiveProfile();

    if (isLoading) {
        return (
            <div className="flex justify-center items-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const isRegularEmployee = Boolean(activeProfile && !hasElevatedAccess(activeProfile));

    if (isRegularEmployee) {
        return <EmployeeTasks profile={activeProfile} />;
    }

    return <HRTasks />;
};
