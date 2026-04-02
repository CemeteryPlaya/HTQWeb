import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { emailService, OAuthStatus } from '@/services/emailService';
import { toast } from 'sonner';
import { Settings, LogOut, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
} from "@/components/ui/dialog";

export function OAuthSettingsPanel() {
    const [status, setStatus] = useState<OAuthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [open, setOpen] = useState(false);

    const fetchStatus = async () => {
        try {
            const data = await emailService.getOAuthStatus();
            setStatus(data);
        } catch (error) {
            console.error("Failed to fetch OAuth status", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, []);

    const handleConnect = async (provider: 'google' | 'microsoft') => {
        setActionLoading(true);
        try {
            const { auth_url } = await emailService.initiateOAuth(provider);
            // Redirect to provider
            window.location.href = auth_url;
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Ошибка инициализации OAuth");
            setActionLoading(false);
        }
    };

    const handleDisconnect = async () => {
        setActionLoading(true);
        try {
            await emailService.disconnectOAuth();
            toast.success("Почта успешно отключена");
            setStatus({ connected: false, provider: null, email: null });
            setOpen(false);
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Ошибка при отключении");
        } finally {
            setActionLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Проверка почты...</span>
            </div>
        );
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <button className="flex items-center justify-between w-full px-4 py-3 rounded-xl transition-all hover:bg-accent text-muted-foreground hover:text-foreground font-medium group">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg transition-colors ${status?.connected ? 'bg-green-500/10 text-green-600' : 'bg-muted group-hover:bg-primary/10'}`}>
                            {status?.connected ? <CheckCircle2 className="h-4 w-4" /> : <Settings className="h-4 w-4" />}
                        </div>
                        <div className="flex flex-col items-start">
                            <span className="text-sm">Внешняя почта</span>
                            {status?.connected && (
                                <span className="text-[10px] opacity-70 truncate max-w-[120px]">
                                    {status.email}
                                </span>
                            )}
                        </div>
                    </div>
                </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Настройки внешней почты</DialogTitle>
                    <DialogDescription>
                        Подключите Google или Microsoft для отправки писем внешним клиентам.
                    </DialogDescription>
                </DialogHeader>

                <div className="py-6 space-y-6">
                    {status?.connected ? (
                        <div className="space-y-4">
                            <div className="flex items-center gap-4 p-4 rounded-xl bg-green-500/5 border border-green-500/10">
                                <div className="bg-green-500 text-white p-2 rounded-full">
                                    <CheckCircle2 className="h-5 w-5" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-semibold text-foreground">Подключено ({status.provider})</p>
                                    <p className="text-sm text-muted-foreground truncate">{status.email}</p>
                                </div>
                            </div>
                            
                            <div className="p-4 rounded-xl bg-orange-500/5 border border-orange-500/10 flex items-start gap-3">
                                <AlertCircle className="h-5 w-5 text-orange-500 shrink-0 mt-0.5" />
                                <p className="text-xs text-orange-700 leading-relaxed">
                                    Все внешние письма будут отправляться через этот аккаунт. 
                                    Internal DLP сканирование остается активным.
                                </p>
                            </div>

                            <Button 
                                variant="destructive" 
                                className="w-full gap-2" 
                                onClick={handleDisconnect}
                                disabled={actionLoading}
                            >
                                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogOut className="h-4 w-4" />}
                                Отключить почту
                            </Button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-3">
                            <Button 
                                variant="outline" 
                                className="h-14 justify-start gap-4 px-6 border-2 hover:border-primary/50 hover:bg-primary/5"
                                onClick={() => handleConnect('google')}
                                disabled={actionLoading}
                            >
                                <img src="https://www.google.com/favicon.ico" alt="Google" className="w-5 h-5" />
                                <div className="text-left">
                                    <div className="font-semibold">Google Workspace</div>
                                    <div className="text-[10px] text-muted-foreground leading-none mt-0.5">Gmail / Business Edition</div>
                                </div>
                            </Button>
                            
                            <Button 
                                variant="outline" 
                                className="h-14 justify-start gap-4 px-6 border-2 hover:border-primary/50 hover:bg-primary/5"
                                onClick={() => handleConnect('microsoft')}
                                disabled={actionLoading}
                            >
                                <img src="https://www.microsoft.com/favicon.ico" alt="Microsoft" className="w-5 h-5" />
                                <div className="text-left">
                                    <div className="font-semibold">Microsoft 365</div>
                                    <div className="text-[10px] text-muted-foreground leading-none mt-0.5">Outlook / Exchange Online</div>
                                </div>
                            </Button>
                            
                            {actionLoading && (
                                <div className="flex items-center justify-center pt-2">
                                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                                    <span className="ml-2 text-sm text-muted-foreground">Перенаправление...</span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
