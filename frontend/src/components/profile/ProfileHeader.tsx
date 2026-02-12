import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { UserProfile } from '../../types/userProfile';

interface ProfileHeaderProps {
    profile: UserProfile;
}

export const ProfileHeader: React.FC<ProfileHeaderProps> = ({ profile }) => {
    const { t } = useTranslation();
    const initials = (profile.firstName?.charAt(0) || profile.display_name?.charAt(0) || "U").toUpperCase();

    const getFullUrl = (url?: string) => {
        if (!url) return undefined;
        if (url.startsWith('http')) return url;
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const rootUrl = baseUrl.replace('/api/', '');
        return `${rootUrl}${url}`;
    };

    return (
        <Card className="mb-6">
            <CardContent className="pt-6 flex flex-col md:flex-row items-center gap-6">
                <Avatar className="w-24 h-24 border-4 border-background shadow-md">
                    <AvatarImage src={getFullUrl(profile.avatarUrl)} className="object-cover" />
                    <AvatarFallback className="text-2xl">{initials}</AvatarFallback>
                </Avatar>
                <div className="text-center md:text-left flex-1">
                    <h2 className="text-2xl font-bold">{profile.display_name || profile.email}</h2>
                    <p className="text-muted-foreground">{profile.firstName} {profile.lastName}</p>
                    <div className="flex flex-wrap gap-2 mt-2 justify-center md:justify-start">
                        {profile.roles.map(role => (
                            <Badge key={role} variant="secondary">{role}</Badge>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
