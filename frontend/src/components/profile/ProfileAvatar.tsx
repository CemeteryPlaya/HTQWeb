import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Camera } from "lucide-react";

interface ProfileAvatarProps {
    avatarUrl?: string;
    firstName?: string;
    onAvatarChange: (file: File) => void;
}

export const ProfileAvatar: React.FC<ProfileAvatarProps> = ({ avatarUrl, firstName, onAvatarChange }) => {
    const { t } = useTranslation();
    const [preview, setPreview] = useState<string | null>(avatarUrl || null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const objectUrl = URL.createObjectURL(file);
            setPreview(objectUrl);
            onAvatarChange(file);
        }
    };

    const triggerFileInput = () => {
        fileInputRef.current?.click();
    };

    const initials = firstName ? firstName.charAt(0).toUpperCase() : "U";

    // If avatarUrl comes from backend, it might need base URL if relative, 
    // but serializer usually returns full URL or we handle it in axios. 
    // Django Development server returns absolute URL usually? 
    // Actually our serializer code: `data['image'] = instance.image.url` returns relative `/media/...`
    // We should prepend API base if it's relative.

    const getFullUrl = (url: string | null) => {
        if (!url) return undefined;
        if (url.startsWith('http')) return url;
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        // remove /api/ if present in base url to get root? 
        // logic: MEDIA_URL is /media/. API_URL is /api/.
        // If we use 'http://localhost:8000/api/', we need 'http://localhost:8000'
        const rootUrl = baseUrl.replace('/api/', '');
        return `${rootUrl}${url}`;
    };

    return (
        <div className="flex flex-col items-center space-y-4">
            <div className="relative group cursor-pointer" onClick={triggerFileInput}>
                <Avatar className="w-32 h-32 border-4 border-background shadow-xl">
                    <AvatarImage src={preview?.startsWith('blob:') ? preview : getFullUrl(preview)} className="object-cover" />
                    <AvatarFallback className="text-4xl">{initials}</AvatarFallback>
                </Avatar>
                <div className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Camera className="text-white w-8 h-8" />
                </div>
            </div>
            <Input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/*"
                onChange={handleFileChange}
            />
            <Button variant="outline" size="sm" onClick={triggerFileInput}>
                {t('profile.changeAvatar')}
            </Button>
        </div>
    );
};
