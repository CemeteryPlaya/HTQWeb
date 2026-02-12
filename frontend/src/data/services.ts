// TODO: Услуги будут создаваться и редактироваться через admin panel
// когда будет реализована авторизация и доступ администратора.
// Текущие данные — статичные.

import panels8 from '@/assets/panels8.jpeg';
import panels9 from '@/assets/panels9.jpeg';
import panels10 from '@/assets/panels10.jpeg';
import panels11 from '@/assets/panels11.jpg';
import panels12 from '@/assets/panels12.jpeg';

export interface Service {
  id: number;
  iconName: string;
  titleKey: string;
  descKey: string;
  image: string;
  featuredOnMain: boolean;
}

export const services: Service[] = [
  {
    id: 1,
    iconName: 'ClipboardCheck',
    titleKey: 'services.items.owners_engineer.title',
    descKey: 'services.items.owners_engineer.desc',
    image: panels8,
    featuredOnMain: true,
  },
  {
    id: 2,
    iconName: 'Shield',
    titleKey: 'services.items.pot.title',
    descKey: 'services.items.pot.desc',
    image: panels9,
    featuredOnMain: true,
  },
  {
    id: 3,
    iconName: 'Wrench',
    titleKey: 'services.items.construction.title',
    descKey: 'services.items.construction.desc',
    image: panels10,
    featuredOnMain: true,
  },
  {
    id: 4,
    iconName: 'Plug',
    titleKey: 'services.items.commissioning.title',
    descKey: 'services.items.commissioning.desc',
    image: panels11,
    featuredOnMain: true,
  },
  {
    id: 5,
    iconName: 'Settings',
    titleKey: 'services.items.maintenance.title',
    descKey: 'services.items.maintenance.desc',
    image: panels12,
    featuredOnMain: true,
  },
];
