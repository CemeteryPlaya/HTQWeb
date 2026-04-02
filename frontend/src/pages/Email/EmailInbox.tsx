import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { emailService, EmailRecipientStatus, EmailMessage } from '@/services/emailService';
import { Mail, Send, FileText, Trash2, ArrowLeft, MoreVertical, Archive, Trash, User, ChevronLeft, Download, FileIcon, Globe, Paperclip } from 'lucide-react';
import { EmailComposeModal } from './EmailComposeModal';
import { OAuthSettingsPanel } from './OAuthSettingsPanel';
import { format, isToday, isYesterday } from 'date-fns';
import { ru } from 'date-fns/locale';

type Folder = 'inbox' | 'sent' | 'drafts' | 'trash';

type DisplayEmail = {
    id: number;
    message_id: number;
    subject: string;
    body: string;
    sender: any;
    created_at: string;
    is_read: boolean;
    folder: Folder;
    original_item: any; 
    attachments: any[];
    external_recipients: string[];
};

// Utils for UI
const stripHtml = (html: string) => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || "";
};

const getInitials = (first: string, last: string, username: string) => {
    if (first && last) return `${first[0]}${last[0]}`.toUpperCase();
    if (first) return first[0].toUpperCase();
    if (username) return username.slice(0, 2).toUpperCase();
    return 'U';
};

const formatEmailDate = (dateString: string) => {
    const date = new Date(dateString);
    if (isToday(date)) return format(date, 'HH:mm');
    if (isYesterday(date)) return 'Вчера';
    return format(date, 'd MMM', { locale: ru });
};

const formatFullDate = (dateString: string) => {
    return format(new Date(dateString), 'd MMMM yyyy, HH:mm', { locale: ru });
};

export default function EmailInbox() {
    const navigate = useNavigate();
    const [emails, setEmails] = useState<DisplayEmail[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentFolder, setCurrentFolder] = useState<Folder>('inbox');
    const [selectedEmail, setSelectedEmail] = useState<DisplayEmail | null>(null);
    const [composeOpen, setComposeOpen] = useState(false);

    useEffect(() => {
        fetchFolder(currentFolder);
    }, [currentFolder]);

    const normalizeEmails = (data: any[], folder: Folder): DisplayEmail[] => {
        if (folder === 'inbox' || folder === 'trash') {
            return (data as EmailRecipientStatus[]).map(item => ({
                id: item.id,
                message_id: item.message.id,
                subject: item.message.subject,
                body: item.message.body,
                sender: item.message.sender,
                created_at: item.message.created_at,
                is_read: item.is_read,
                folder,
                original_item: item,
                attachments: item.message.attachments || [],
                external_recipients: item.message.external_recipients || []
            }));
        } else {
            return (data as EmailMessage[]).map(item => ({
                id: item.id,
                message_id: item.id,
                subject: item.subject,
                body: item.body,
                sender: item.sender,
                created_at: item.created_at,
                is_read: true, 
                folder,
                original_item: item,
                attachments: item.attachments || [],
                external_recipients: item.external_recipients || []
            }));
        }
    };

    const fetchFolder = async (folder: Folder) => {
        setLoading(true);
        setSelectedEmail(null);
        try {
            let data: any[] = [];
            switch (folder) {
                case 'inbox': data = await emailService.getInbox(); break;
                case 'sent': data = await emailService.getSent(); break;
                case 'drafts': data = await emailService.getDrafts(); break;
                case 'trash': data = await emailService.getTrash(); break;
            }
            setEmails(normalizeEmails(data, folder));
        } catch (error) {
            console.error(`Failed to fetch ${folder}`, error);
        } finally {
            setLoading(false);
        }
    };

    const handleEmailClick = async (item: DisplayEmail) => {
        setSelectedEmail(item);
        if (!item.is_read && (item.folder === 'inbox' || item.folder === 'trash')) {
            try {
                await emailService.markAsRead(item.id, true);
                setEmails(prev => prev.map(m => m.id === item.id ? { ...m, is_read: true } : m));
            } catch (e) {
                console.error("Failed to mark as read", e);
            }
        }
    };

    const getFolderTitle = () => {
        switch (currentFolder) {
            case 'inbox': return 'Входящие';
            case 'sent': return 'Отправленные пиcьма';
            case 'drafts': return 'Черновики';
            case 'trash': return 'Корзина';
        }
    }

    const getSenderName = (item: DisplayEmail) => {
        if (currentFolder === 'sent') return 'Моя рассылка';
        if (currentFolder === 'drafts') return 'Черновик';
        return `${item.sender.first_name || item.sender.username} ${item.sender.last_name}`;
    }

    const getFileName = (url: string) => {
        try {
            const parts = url.split('/');
            return parts[parts.length - 1];
        } catch (e) {
            return 'Вложение';
        }
    };

    return (
        <div className="flex h-[calc(100vh-64px)] overflow-hidden relative bg-muted/20">
            {/* Sidebar */}
            <div className="w-64 border-r border-border bg-background p-4 flex flex-col h-full">
                <button 
                    onClick={() => setComposeOpen(true)}
                    className="w-full bg-primary text-primary-foreground hover:bg-primary/90 rounded-xl px-4 py-3 font-semibold mb-6 shadow-sm transition-all hover:shadow-md flex items-center justify-center gap-2"
                >
                    <Mail className="h-5 w-5" />
                    Написать
                </button>
                <div className="flex flex-col gap-1 flex-1">
                    {[
                        { id: 'inbox', icon: Mail, label: 'Входящие' },
                        { id: 'sent', icon: Send, label: 'Отправленные' },
                        { id: 'drafts', icon: FileText, label: 'Черновики' },
                        { id: 'trash', icon: Trash2, label: 'Корзина' }
                    ].map(f => {
                        const Icon = f.icon;
                        const isActive = currentFolder === f.id;
                        return (
                            <button 
                                key={f.id}
                                onClick={() => setCurrentFolder(f.id as Folder)}
                                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors text-sm ${isActive ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-accent text-muted-foreground font-medium'}`}
                            >
                                <Icon className={`h-4 w-4 ${isActive ? 'text-primary' : ''}`} /> {f.label}
                            </button>
                        );
                    })}
                </div>

                <div className="mt-auto pt-4 border-t space-y-1">
                    <OAuthSettingsPanel />
                    <button 
                        onClick={() => navigate('/myprofile')}
                        className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-accent text-muted-foreground hover:text-foreground font-medium w-full group"
                    >
                        <div className="bg-muted group-hover:bg-primary/10 p-2 rounded-lg transition-colors">
                            <ChevronLeft className="h-4 w-4 group-hover:text-primary" />
                        </div>
                        <span>В профиль</span>
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto p-0 md:p-6 lg:p-8 flex justify-center">
                <div className="w-full max-w-5xl h-full flex flex-col">
                    {selectedEmail ? (
                        <div className="flex flex-col h-full animate-in fade-in slide-in-from-right-4 duration-200">
                            {/* Toolbar */}
                            <div className="flex items-center justify-between mb-4 sticky top-0 bg-background/80 backdrop-blur-md z-10 p-2 md:p-0">
                                <button 
                                    onClick={() => setSelectedEmail(null)}
                                    className="p-2.5 hover:bg-accent hover:text-accent-foreground rounded-full transition-colors flex items-center gap-2 text-sm font-medium"
                                >
                                    <ArrowLeft className="h-5 w-5" />
                                    <span className="sr-only md:not-sr-only">Назад</span>
                                </button>
                                <div className="flex gap-1">
                                    <button className="p-2.5 hover:bg-accent rounded-full text-muted-foreground" title="В архив">
                                        <Archive className="h-4 w-4" />
                                    </button>
                                    <button className="p-2.5 hover:bg-accent rounded-full text-muted-foreground" title="Удалить">
                                        <Trash className="h-4 w-4" />
                                    </button>
                                    <button className="p-2.5 hover:bg-accent rounded-full text-muted-foreground">
                                        <MoreVertical className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>

                            {/* Email Details View */}
                            <div className="bg-background border rounded-2xl shadow-sm flex-1 overflow-hidden flex flex-col">
                                <div className="p-6 sm:p-8 lg:p-10 border-b">
                                    <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-8 leading-tight">
                                        {selectedEmail.subject || '(Без темы)'}
                                    </h1>
                                    <div className="flex justify-between items-start sm:items-center flex-col sm:flex-row gap-4">
                                        <div className="flex items-center gap-4">
                                            <div className="h-12 w-12 rounded-full bg-primary/15 text-primary flex justify-center items-center text-lg font-bold">
                                                {getInitials(selectedEmail.sender.first_name, selectedEmail.sender.last_name, selectedEmail.sender.username)}
                                            </div>
                                            <div>
                                                <p className="font-semibold text-foreground text-base">
                                                    {getSenderName(selectedEmail)}
                                                </p>
                                                <p className="text-sm text-muted-foreground">
                                                    кому: {currentFolder === 'sent' || currentFolder === 'drafts' ? 'Неизвестно' : 'мне'}
                                                </p>
                                                {selectedEmail.external_recipients && selectedEmail.external_recipients.length > 0 && (
                                                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                                                        <Globe className="h-3.5 w-3.5 text-orange-500 mt-0.5" />
                                                        {selectedEmail.external_recipients.map(email => (
                                                            <span key={email} className="text-xs bg-orange-500/10 text-orange-600 dark:text-orange-400 px-2 py-0.5 rounded-full border border-orange-500/20">
                                                                {email}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        <span className="text-sm text-muted-foreground font-medium">
                                            {formatFullDate(selectedEmail.created_at)}
                                        </span>
                                    </div>
                                </div>
                                
                                <div className="flex-1 overflow-y-auto">
                                    <div 
                                        className="p-6 sm:p-8 lg:p-10 prose dark:prose-invert max-w-none text-foreground/90 leading-relaxed"
                                        dangerouslySetInnerHTML={{ __html: selectedEmail.body || '<i>(Пустое сообщение)</i>' }}
                                    />

                                    {/* Attachments Display */}
                                    {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
                                        <div className="p-6 sm:p-8 lg:p-10 border-t bg-muted/5">
                                            <div className="flex items-center gap-2 mb-4">
                                                <Paperclip className="h-4 w-4 text-primary" />
                                                <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">
                                                    Вложения ({selectedEmail.attachments.length})
                                                </h3>
                                            </div>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                                {selectedEmail.attachments.map((file, idx) => (
                                                    <a 
                                                        key={`attach-${file.id}`}
                                                        href={file.file}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="flex items-center justify-between p-3 bg-background border rounded-xl hover:shadow-md hover:border-primary/30 transition-all group"
                                                    >
                                                        <div className="flex items-center gap-3 overflow-hidden">
                                                            <div className="bg-primary/10 p-2 rounded-lg group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                                                                <FileIcon className="h-4 w-4" />
                                                            </div>
                                                            <div className="flex flex-col truncate">
                                                                <span className="text-sm font-medium truncate text-foreground group-hover:text-primary transition-colors">
                                                                    {getFileName(file.file)}
                                                                </span>
                                                                <span className="text-[10px] text-muted-foreground uppercase font-bold">
                                                                    {getFileName(file.file).split('.').pop()}
                                                                </span>
                                                            </div>
                                                        </div>
                                                        <Download className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                                                    </a>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="animate-in fade-in flex flex-col h-full">
                            <h1 className="text-2xl font-bold mb-6 text-foreground tracking-tight px-4 md:px-0">
                                {getFolderTitle()}
                            </h1>
                            
                            {loading ? (
                                <div className="flex items-center justify-center flex-1">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                                </div>
                            ) : emails.length === 0 ? (
                                <div className="text-center p-12 flex-1 flex flex-col items-center justify-center text-muted-foreground bg-background/50 rounded-2xl border border-dashed border-border shadow-sm">
                                    <div className="h-20 w-20 bg-muted rounded-full flex justify-center items-center mb-6">
                                        <Mail className="h-10 w-10 text-muted-foreground/50" />
                                    </div>
                                    <p className="text-lg font-medium">Нет писем в папке "{getFolderTitle()}"</p>
                                    <p className="text-sm mt-2 opacity-75">Когда сюда придут письма, они появятся в этом списке.</p>
                                </div>
                            ) : (
                                <div className="flex flex-col gap-0.5 overflow-hidden rounded-2xl border shadow-sm bg-border/50">
                                    {emails.map(item => {
                                        const previewText = stripHtml(item.body).substring(0, 100);
                                        const initials = getInitials(item.sender.first_name, item.sender.last_name, item.sender.username);
                                        const senderName = getSenderName(item);

                                        return (
                                            <div 
                                                key={item.id} 
                                                onClick={() => handleEmailClick(item)}
                                                className={`group flex items-center px-4 py-3 sm:px-6 sm:py-4 cursor-pointer transition-all bg-background hover:bg-accent/40 ${
                                                    !item.is_read ? 'font-semibold' : 'text-muted-foreground'
                                                }`}
                                            >
                                                {(currentFolder === 'inbox' || currentFolder === 'trash') && (
                                                    <div className="w-3 flex-shrink-0 mr-2 sm:mr-4">
                                                        {!item.is_read && <div className="w-2.5 h-2.5 rounded-full bg-primary mx-auto"></div>}
                                                    </div>
                                                )}

                                                <div className="hidden sm:flex h-10 w-10 flex-shrink-0 rounded-full bg-primary/10 text-primary justify-center items-center font-bold mr-4 text-sm group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                                                    {initials}
                                                </div>

                                                <div className="flex flex-col sm:flex-row flex-1 min-w-0 sm:items-center justify-between gap-1 sm:gap-4 overflow-hidden">
                                                    <div className="w-full sm:w-48 xl:w-56 flex-shrink-0 flex items-center gap-1.5 overflow-hidden">
                                                        <span className="truncate text-[15px]">{senderName}</span>
                                                        {item.external_recipients && item.external_recipients.length > 0 && (
                                                            <span title="Внешняя почта" className="flex-shrink-0 flex items-center">
                                                                <Globe className="h-3.5 w-3.5 text-orange-500" />
                                                            </span>
                                                        )}
                                                        {item.attachments && item.attachments.length > 0 && (
                                                            <Paperclip className="h-3 w-3 text-muted-foreground opacity-60 flex-shrink-0" />
                                                        )}
                                                    </div>

                                                    <div className="flex-1 truncate text-sm">
                                                        <span className="text-foreground">{item.subject || '(Без темы)'}</span>
                                                        <span className="opacity-60 hidden md:inline ml-2 font-normal">
                                                            — {previewText || 'Пустое сообщение'}
                                                        </span>
                                                    </div>

                                                    <div className="flex-shrink-0 text-xs sm:text-sm text-right w-20 sm:w-24 mt-1 sm:mt-0 opacity-80 font-normal">
                                                        {formatEmailDate(item.created_at)}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <EmailComposeModal 
                open={composeOpen} 
                onOpenChange={setComposeOpen} 
                onSuccess={() => fetchFolder(currentFolder)} 
            />
        </div>
    );
}
