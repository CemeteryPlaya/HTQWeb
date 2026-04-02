import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { emailService, OAuthStatus } from '@/services/emailService';
import api from '@/api/client';
import { toast } from 'sonner';
import JoditEditor from 'jodit-react';
import { Search, X, Mail, Paperclip, FileIcon, Globe, AlertCircle, CheckCircle2, User } from 'lucide-react';

type RecipientOption = {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    email: string;
};

interface EmailComposeModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: () => void;
}

export function EmailComposeModal({ open, onOpenChange, onSuccess }: EmailComposeModalProps) {
    const editor = useRef(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [recipientIds, setRecipientIds] = useState<number[]>([]);
    const [externalEmails, setExternalEmails] = useState<string[]>([]);
    const [externalInput, setExternalInput] = useState('');
    const [externalError, setExternalError] = useState('');
    const [files, setFiles] = useState<File[]>([]);
    const [submitting, setSubmitting] = useState(false);

    const [searchQuery, setSearchQuery] = useState('');
    const [availableUsers, setAvailableUsers] = useState<RecipientOption[]>([]);
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);

    const config = useMemo(() => ({
        readonly: false,
        placeholder: 'Напишите текст письма...',
        height: 400,
        style: {
            fontFamily: 'inherit',
        },
        buttons: [
            'bold', 'italic', 'underline', 'strikethrough', '|',
            'ul', 'ol', '|',
            'font', 'fontsize', 'paragraph', '|',
            'align', 'undo', 'redo', '|',
            'hr', 'link'
        ],
        toolbarAdaptive: false,
        showCharsCounter: false,
        showWordsCounter: false,
        showXPathInStatusbar: false
    }), []);

    useEffect(() => {
        if (!open) return;
        
        let active = true;
        setLoadingUsers(true);
        api.get('/hr/employees/users/')
            .then(res => {
                if (active) {
                    const users = Array.isArray(res.data) ? res.data : res.data.results || [];
                    setAvailableUsers(users);
                }
            })
            .catch(err => {
                console.error("Failed to load users", err);
            })
            .finally(() => {
                if (active) setLoadingUsers(false);
            });

        // Fetch OAuth status
        emailService.getOAuthStatus()
            .then(status => {
                if (active) setOauthStatus(status);
            })
            .catch(err => console.error("Failed to fetch OAuth status in modal", err));

        return () => { active = false; };
    }, [open]);

    const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    const addExternalEmail = () => {
        const email = externalInput.trim().toLowerCase();
        if (!email) return;
        if (!isValidEmail(email)) {
            setExternalError('Некорректный формат email');
            return;
        }
        if (externalEmails.includes(email)) {
            setExternalError('Этот email уже добавлен');
            return;
        }
        setExternalEmails(prev => [...prev, email]);
        setExternalInput('');
        setExternalError('');
    };

    const removeExternalEmail = (email: string) => {
        setExternalEmails(prev => prev.filter(e => e !== email));
    };

    const handleExternalKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addExternalEmail();
        }
    };

    const handleClose = () => {
        onOpenChange(false);
        setTimeout(() => {
            setSubject('');
            setBody('');
            setRecipientIds([]);
            setExternalEmails([]);
            setExternalInput('');
            setExternalError('');
            setFiles([]);
            setSearchQuery('');
        }, 200);
    };

    const toggleRecipient = (userId: number) => {
        setRecipientIds(prev => 
            prev.includes(userId) 
                ? prev.filter(id => id !== userId)
                : [...prev, userId]
        );
        setSearchQuery(''); 
    };

    const removeRecipient = (userId: number, e: React.MouseEvent) => {
        e.stopPropagation();
        setRecipientIds(prev => prev.filter(id => id !== userId));
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const newFiles = Array.from(e.target.files);
            setFiles(prev => [...prev, ...newFiles]);
        }
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleSend = async () => {
        if (!subject.trim()) {
            toast.error("Укажите тему письма");
            return;
        }
        if (recipientIds.length === 0 && externalEmails.length === 0) {
            toast.error("Выберите хотя бы одного получателя (внутреннего или внешнего)");
            return;
        }
        if (!body.trim() || body === '<p><br></p>') {
            toast.error("Письмо не может быть пустым");
            return;
        }

        setSubmitting(true);
        try {
            const formData = new FormData();
            formData.append('subject', subject);
            formData.append('body', body);
            formData.append('recipients', JSON.stringify(recipientIds));
            if (externalEmails.length > 0) {
                formData.append('external_recipients', JSON.stringify(externalEmails));
            }
            
            files.forEach(file => {
                formData.append('attachments', file);
            });

            await emailService.sendEmail(formData);
            toast.success("Письмо успешно отправлено!");
            if (onSuccess) onSuccess();
            handleClose();
        } catch (error: any) {
            console.error("Failed to send email", error);
            toast.error(error.response?.data?.error || "Ошибка при отправке письма");
        } finally {
            setSubmitting(false);
        }
    };

    const handleSaveDraft = async () => {
        if (!subject.trim()) {
            toast.error("Укажите тему для черновика");
            return;
        }

        setSubmitting(true);
        try {
            await emailService.saveDraft({
                subject,
                body
            });
            toast.success("Черновик сохранен");
            if (onSuccess) onSuccess();
            handleClose();
        } catch (error: any) {
            console.error("Failed to save draft", error);
            toast.error(error.response?.data?.error || "Ошибка при сохранении черновика");
        } finally {
            setSubmitting(false);
        }
    };

    const filteredUsers = availableUsers.filter(u => 
        !recipientIds.includes(u.id) && ( 
            u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (u.first_name && u.first_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
            (u.last_name && u.last_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
            (u.email && u.email.toLowerCase().includes(searchQuery.toLowerCase()))
        )
    );

    const selectedUsers = availableUsers.filter(u => recipientIds.includes(u.id));

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[900px] h-[90vh] flex flex-col p-0 gap-0 overflow-hidden bg-background border-border shadow-2xl">
                <DialogHeader className="px-6 py-4 border-b bg-muted/30">
                    <DialogTitle className="text-2xl font-semibold flex items-center gap-2">
                        <Mail className="h-6 w-6 text-primary" />
                        Новое сообщение
                    </DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Sender Identity Section */}
                    {oauthStatus && (
                        <div className="bg-muted/30 border border-muted-foreground/10 rounded-xl p-4 flex items-center gap-4 animate-in fade-in slide-in-from-top-2">
                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                                <User className="h-5 w-5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold mb-0.5">Отправитель</p>
                                <div className="flex items-center gap-2">
                                    <span className="font-semibold text-sm truncate">
                                        {oauthStatus.connected ? oauthStatus.email : oauthStatus.primary_email}
                                    </span>
                                    {oauthStatus.connected ? (
                                        <span className="flex items-center gap-1 text-[10px] bg-green-500/10 text-green-600 px-1.5 py-0.5 rounded-md font-bold border border-green-500/20 whitespace-nowrap">
                                            <CheckCircle2 className="h-3 w-3" />
                                            {oauthStatus.provider === 'google' ? 'Google' : 'Microsoft'}
                                        </span>
                                    ) : (
                                        <span className="text-[10px] bg-primary/5 text-primary/60 px-1.5 py-0.5 rounded-md font-bold border border-primary/10 whitespace-nowrap">
                                            Внутренняя почта
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Recipients Section */}
                    <div className="space-y-3">
                        <Label className="text-base font-semibold">Кому</Label>
                        
                        {selectedUsers.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2 p-3 bg-accent/20 border rounded-md">
                                {selectedUsers.map(user => (
                                    <div key={`sel-${user.id}`} className="flex items-center gap-1 bg-primary text-primary-foreground px-2 py-1 rounded-full text-sm shadow-sm">
                                        <span>{user.first_name || user.username} {user.last_name}</span>
                                        <button 
                                            onClick={(e) => removeRecipient(user.id, e)}
                                            className="hover:bg-primary/80 rounded-full p-0.5 transition-colors"
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input 
                                placeholder="Поиск получателей (по имени или email)..." 
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 h-11 text-base"
                            />
                            
                            {searchQuery.length > 0 && (
                                <div className="absolute z-10 w-full mt-1 bg-popover text-popover-foreground border rounded-md shadow-lg max-h-48 overflow-y-auto top-full">
                                    {loadingUsers ? (
                                        <div className="p-4 text-center text-sm text-muted-foreground">Поиск...</div>
                                    ) : filteredUsers.length === 0 ? (
                                        <div className="p-4 text-center text-sm text-muted-foreground">Пользователи не найдены</div>
                                    ) : (
                                        filteredUsers.map(user => (
                                            <div 
                                                key={`opt-${user.id}`}
                                                onClick={() => toggleRecipient(user.id)}
                                                className="px-4 py-3 hover:bg-accent hover:text-accent-foreground cursor-pointer flex flex-col justify-center border-b last:border-0 transition-colors"
                                            >
                                                <span className="font-medium text-sm">
                                                    {user.first_name || user.username} {user.last_name}
                                                </span>
                                                <span className="text-xs text-muted-foreground">
                                                    {user.email || 'Нет email'}
                                                </span>
                                            </div>
                                        ))
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* External Recipients Section */}
                    <div className="space-y-3">
                        <Label className="text-base font-semibold flex items-center gap-2">
                            <Globe className="h-4 w-4 text-orange-500" />
                            Внешние получатели (email)
                        </Label>

                        {!oauthStatus?.connected && externalEmails.length > 0 && (
                            <div className="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-md animate-in fade-in slide-in-from-top-1">
                                <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                                <div className="space-y-1">
                                    <p className="text-sm font-semibold text-red-700">Внешняя почта не подключена</p>
                                    <p className="text-xs text-red-600 leading-relaxed">
                                        Для отправки на внешние адреса необходимо подключить аккаунт Google или Microsoft в настройках (сайдбар слева).
                                    </p>
                                </div>
                            </div>
                        )}

                        {oauthStatus?.connected && (
                            <div className="flex items-center gap-2 p-2 px-3 bg-green-500/5 border border-green-500/10 rounded-md text-[11px] text-green-700 font-medium">
                                <CheckCircle2 className="h-3.5 w-3.5" />
                                <span>Отправка через {oauthStatus.provider} ({oauthStatus.email})</span>
                            </div>
                        )}

                        {externalEmails.length > 0 && (
                            <div className="flex flex-wrap gap-2 p-3 bg-orange-500/10 border border-orange-500/20 rounded-md">
                                {externalEmails.map(email => (
                                    <div key={`ext-${email}`} className="flex items-center gap-1 bg-orange-500 text-white px-2 py-1 rounded-full text-sm shadow-sm">
                                        <span>{email}</span>
                                        <button
                                            onClick={() => removeExternalEmail(email)}
                                            className="hover:bg-orange-600 rounded-full p-0.5 transition-colors"
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="flex gap-2">
                            <div className="flex-1">
                                <Input
                                    placeholder="Введите email и нажмите Enter (например, user@gmail.com)"
                                    value={externalInput}
                                    onChange={(e) => {
                                        setExternalInput(e.target.value);
                                        setExternalError('');
                                    }}
                                    onKeyDown={handleExternalKeyDown}
                                    className={`h-11 text-base ${externalError ? 'border-destructive' : ''}`}
                                />
                                {externalError && (
                                    <p className="text-sm text-destructive mt-1">{externalError}</p>
                                )}
                            </div>
                            <Button
                                type="button"
                                variant="outline"
                                size="default"
                                onClick={addExternalEmail}
                                disabled={!externalInput.trim()}
                                className="h-11 px-4"
                            >
                                Добавить
                            </Button>
                        </div>
                    </div>

                    {/* Subject */}
                    <div className="space-y-3">
                        <Label className="text-base font-semibold">Тема</Label>
                        <Input 
                            placeholder="Введите тему сообщения" 
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                            className="h-11 text-base font-medium"
                        />
                    </div>

                    {/* Body */}
                    <div className="space-y-3 flex flex-col flex-1 pb-2">
                        <Label className="text-base font-semibold">Сообщение</Label>
                        <div className="flex-1 rounded-md overflow-hidden border">
                            <JoditEditor
                                ref={editor}
                                value={body}
                                config={config}
                                onBlur={newContent => setBody(newContent)}
                            />
                        </div>
                    </div>

                    {/* Attachments UI */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <Label className="text-base font-semibold">Вложения</Label>
                            <Button 
                                type="button" 
                                variant="outline" 
                                size="sm" 
                                onClick={() => fileInputRef.current?.click()}
                                className="gap-2"
                            >
                                <Paperclip className="h-4 w-4" />
                                Прикрепить файл
                            </Button>
                            <input 
                                type="file" 
                                ref={fileInputRef} 
                                className="hidden" 
                                multiple 
                                onChange={handleFileChange}
                            />
                        </div>

                        {files.length > 0 && (
                            <div className="space-y-2 bg-muted/20 p-4 rounded-lg border border-dashed">
                                {files.map((file, idx) => (
                                    <div key={`file-${idx}`} className="flex items-center justify-between bg-background p-2 rounded border shadow-sm group">
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <FileIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                            <div className="flex flex-col truncate">
                                                <span className="text-sm font-medium truncate">{file.name}</span>
                                                <span className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</span>
                                            </div>
                                        </div>
                                        <button 
                                            onClick={() => removeFile(idx)}
                                            className="p-1 hover:bg-destructive/10 hover:text-destructive rounded text-muted-foreground transition-colors"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <DialogFooter className="px-6 py-4 bg-muted/30 border-t flex sm:justify-between items-center gap-4">
                    <Button variant="outline" size="lg" onClick={handleClose} disabled={submitting}>
                        Отмена
                    </Button>
                    <div className="flex gap-3">
                        <Button variant="secondary" size="lg" onClick={handleSaveDraft} disabled={submitting}>
                            Сохранить черновик
                        </Button>
                        <Button size="lg" onClick={handleSend} disabled={submitting} className="min-w-[140px] font-semibold">
                            {submitting ? (
                                <span className="flex items-center gap-2">
                                    <span className="animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full"></span>
                                    Отправка...
                                </span>
                            ) : 'Отправить письмо'}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
