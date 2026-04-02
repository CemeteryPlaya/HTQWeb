import { Navigate, useLocation } from "react-router-dom";
import { ForcePasswordChange } from "./ForcePasswordChange";
import { Loader2 } from "lucide-react";
import { useActiveProfile } from "@/hooks/useActiveProfile";

const RequireAuth = ({ children }: { children: JSX.Element }) => {
    const location = useLocation();
    const { activeProfile, isLoading, error, isLoggedIn, clearAuthStorage } = useActiveProfile({
        retry: false,
    });

    if (!isLoggedIn || error) {
        if (error) {
            clearAuthStorage();
        }
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (isLoading && !activeProfile) {
        return (
            <div className="min-h-screen bg-background flex flex-col items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary opacity-50" />
            </div>
        );
    }

    if (activeProfile?.must_change_password) {
        return <ForcePasswordChange />;
    }

    return children;
};

export default RequireAuth;
